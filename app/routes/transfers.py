"""OWNER: Lead (backend). Transfers must be atomic, validated, idempotent."""
import re
import secrets
import sqlite3
from decimal import Decimal, InvalidOperation

from flask import (
    Blueprint, current_app, flash, g, redirect, render_template, request,
    session, url_for,
)

from ..security import login_required, audit
from ..db import get_db
from ..money import money

bp = Blueprint("transfers", __name__)

_IDEM_RE = re.compile(r"^[0-9a-f]{32}$")


def parse_amount(text):
    """Parse a dollar amount ("12.50") into integer cents, or None if invalid.

    Bounded to two decimals, positive, and <= MAX_TRANSFER_CENTS.
    """
    try:
        d = Decimal((text or "").strip())
    except (InvalidOperation, AttributeError):
        return None
    if not d.is_finite() or d <= 0 or d.as_tuple().exponent < -2:
        return None
    cents = int(d * 100)
    if cents <= 0 or cents > current_app.config["MAX_TRANSFER_CENTS"]:
        return None
    return cents


def _idempotency_key():
    """Per-session token, hidden in the form, so a double submit can't double-spend."""
    if "idempotency_key" not in session:
        session["idempotency_key"] = secrets.token_hex(16)
    return session["idempotency_key"]


@bp.route("/transfer", methods=["GET", "POST"])
@login_required
def transfer():
    db = get_db()
    acct = db.execute(
        "SELECT id, account_number, balance_cents FROM accounts WHERE user_id = ?",
        (g.user["id"],),
    ).fetchone()

    def recipients():
        return db.execute(
            "SELECT account_number FROM accounts WHERE user_id != ? ORDER BY account_number",
            (g.user["id"],),
        ).fetchall()

    def fail(message, code=400, key=None):
        return render_template(
            "transfer.html",
            account=acct,
            recipients=recipients(),
            idempotency_key=key or _idempotency_key(),
            error=message,
            money=money,
        ), code

    if acct is None:
        return fail("No account is linked to your profile.", 400)

    if request.method == "GET":
        return render_template(
            "transfer.html",
            account=acct,
            recipients=recipients(),
            idempotency_key=_idempotency_key(),
            money=money,
        )

    key = request.form.get("idempotency_key", "").strip()
    to_account_number = request.form.get("to_account", "").strip()
    note = request.form.get("note", "").strip()[:100]
    cents = parse_amount(request.form.get("amount", ""))

    if not _IDEM_RE.match(key):
        return fail("Your session expired. Reload the page and try again.")
    if cents is None:
        return fail("Enter a valid amount (positive, up to $1,000,000, max 2 decimals).")
    if not to_account_number:
        return fail("Choose a recipient account.")

    to_acct = db.execute(
        "SELECT id, user_id FROM accounts WHERE account_number = ?",
        (to_account_number,),
    ).fetchone()
    if not to_acct or to_acct["user_id"] == g.user["id"]:
        return fail("Recipient account not found.")

    reference = secrets.token_hex(8)
    try:
        db.execute("BEGIN IMMEDIATE")  # take the write lock before reading balances
        dup = db.execute(
            "SELECT reference FROM transactions WHERE idempotency_key = ?", (key,)
        ).fetchone()
        if dup:  # replay: nothing changes, report the original reference
            db.execute("ROLLBACK")
            session["idempotency_key"] = secrets.token_hex(16)
            flash(f"Transfer already processed (reference {dup['reference']}).")
            return redirect(url_for("dashboard.dashboard"))

        cur = db.execute(
            "UPDATE accounts SET balance_cents = balance_cents - ? "
            "WHERE id = ? AND balance_cents >= ?",
            (cents, acct["id"], cents),
        )
        if cur.rowcount == 0:  # the guarded UPDATE matched nothing -> not enough funds
            db.execute("ROLLBACK")
            return fail("Insufficient funds.", key=key)

        db.execute(
            "UPDATE accounts SET balance_cents = balance_cents + ? WHERE id = ?",
            (cents, to_acct["id"]),
        )
        db.execute(
            "INSERT INTO transactions "
            "(reference, idempotency_key, from_account, to_account, amount_cents, note) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (reference, key, acct["id"], to_acct["id"], cents, note or None),
        )
        db.execute("COMMIT")
    except sqlite3.IntegrityError:  # unique idempotency_key -> a concurrent replay
        db.execute("ROLLBACK")
        session["idempotency_key"] = secrets.token_hex(16)
        flash("Transfer already processed.")
        return redirect(url_for("dashboard.dashboard"))
    except Exception:
        db.execute("ROLLBACK")
        raise

    session["idempotency_key"] = secrets.token_hex(16)
    audit("transfer", reference)
    flash(f"Sent {money(cents)} — reference {reference}.")
    return redirect(url_for("dashboard.dashboard"))
