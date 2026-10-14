"""OWNER: Home 1. Show account + balance for g.user ONLY (never an ID from the URL)."""
from flask import Blueprint, g
from ..security import login_required
from ..db import get_db
bp = Blueprint("dashboard", __name__)

@bp.route("/dashboard")
@login_required
def dashboard():
    acct = get_db().execute(
        "SELECT account_number, balance_cents FROM accounts WHERE user_id = ?",
        (g.user["id"],)).fetchone()
    # TODO Home 1: render a template with acct; amounts are cents -> format as money.
    return {"name": g.user["full_name"], "account": acct["account_number"],
            "balance": acct["balance_cents"] / 100}
