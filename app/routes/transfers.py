"""OWNER: Lead (backend). Transfers must be atomic, validated, idempotent."""
import secrets
from flask import Blueprint, g, request, redirect, url_for, render_template

from ..security import login_required, audit, owns_account
from ..db import get_db

bp = Blueprint("transfers", __name__)


@bp.route("/transfer", methods=["GET", "POST"])
@login_required
def transfer():
    db = get_db()
    acct = db.execute(
        "SELECT id, account_number, balance_cents FROM accounts WHERE user_id = ?",
        (g.user["id"],)
    ).fetchone()

    if request.method == "GET":
        recipients = db.execute(
            "SELECT account_number FROM accounts WHERE user_id != ?", (g.user["id"],)
        ).fetchall()
        return render_template("transfer.html", account=acct, recipients=recipients)

    idempotency_key = request.form.get("idempotency_key", "").strip()
    to_account_number = request.form.get("to_account", "").strip()
    try:
        amount_cents = int(request.form.get("amount_cents", "0"))
    except ValueError:
        amount_cents = 0

    if not idempotency_key or not to_account_number or amount_cents <= 0:
        return render_template("transfer.html", account=acct, error="Invalid transfer details."), 400

    existing = db.execute(
        "SELECT id FROM transactions WHERE idempotency_key = ?", (idempotency_key,)
    ).fetchone()
    if existing:
        return redirect(url_for("dashboard.dashboard"))

    to_acct = db.execute(
        "SELECT id, user_id FROM accounts WHERE account_number = ?", (to_account_number,)
    ).fetchone()
    if not to_acct or to_acct["user_id"] == g.user["id"]:
        return render_template("transfer.html", account=acct, error="Recipient not found."), 400
    if acct["balance_cents"] < amount_cents:
        return render_template("transfer.html", account=acct, error="Insufficient funds."), 400

    reference = secrets.token_hex(8)
    try:
        db.execute("BEGIN")
        db.execute(
            "UPDATE accounts SET balance_cents = balance_cents - ? WHERE id = ? AND balance_cents >= ?",
            (amount_cents, acct["id"], amount_cents)
        )
        if db.total_changes == 0:
            db.rollback()
            return render_template("transfer.html", account=acct, error="Insufficient funds."), 400
        db.execute(
            "UPDATE accounts SET balance_cents = balance_cents + ? WHERE id = ?",
            (amount_cents, to_acct["id"])
        )
        db.execute(
            "INSERT INTO transactions (reference, idempotency_key, from_account, to_account, amount_cents) "
            "VALUES (?, ?, ?, ?, ?)",
            (reference, idempotency_key, acct["id"], to_acct["id"], amount_cents),
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    audit("transfer", reference)
    return redirect(url_for("dashboard.dashboard"))