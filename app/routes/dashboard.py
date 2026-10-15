"""OWNER: Home 1. Show account + balance for g.user ONLY (never an ID from the URL)."""
from flask import Blueprint, g, render_template

from ..security import login_required
from ..db import get_db
from ..money import money

bp = Blueprint("dashboard", __name__)


@bp.route("/dashboard")
@login_required
def dashboard():
    acct = get_db().execute(
        "SELECT account_number, balance_cents FROM accounts WHERE user_id = ?",
        (g.user["id"],)
    ).fetchone()
    return render_template("dashboard.html", account=acct, money=money)