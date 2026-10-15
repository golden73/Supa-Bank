"""OWNER: Home 1. Show account + balance for g.user ONLY (never an ID from the URL)."""
from flask import Blueprint, g, render_template

from ..security import login_required
from ..db import get_db

bp = Blueprint("dashboard", __name__)


@bp.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    acct = db.execute(
        "SELECT id, account_number, balance_cents FROM accounts WHERE user_id = ?",
        (g.user["id"],),
    ).fetchone()
    recent = db.execute(
        """SELECT t.reference, t.amount_cents, t.note, t.created_at,
                  t.from_account = a.id AS outgoing
           FROM transactions t JOIN accounts a ON a.user_id = ?
           WHERE t.from_account = a.id OR t.to_account = a.id
           ORDER BY t.id DESC LIMIT 5""",
        (g.user["id"],),
    ).fetchall()
    return render_template("dashboard.html", user=g.user, account=acct, transactions=recent)
