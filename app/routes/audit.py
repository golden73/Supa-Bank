"""OWNER: Functionality 2. Audit viewing + anomaly alerts (admin only)."""
from flask import Blueprint, g, render_template

from ..security import admin_required
from ..db import get_db

bp = Blueprint("audit", __name__, url_prefix="/admin")


@bp.route("/audit")
@admin_required
def audit_view():
    rows = get_db().execute(
        "SELECT user_id, action, target, ip, created_at FROM audit_log ORDER BY id DESC LIMIT 200"
    ).fetchall()
    return render_template("audit.html", audit=rows)


@bp.route("/alerts")
@admin_required
def alerts():
    db = get_db()
    failed = db.execute(
        """SELECT u.id, u.username, u.failed_logins, u.locked_until
           FROM users u WHERE u.failed_logins >= ? ORDER BY u.failed_logins DESC""",
        (5,)
    ).fetchall()
    large = db.execute(
        """SELECT t.reference, t.amount_cents, t.created_at,
                  u.username, a.account_number
           FROM transactions t
           JOIN accounts a ON a.id = t.from_account
           JOIN users u ON u.id = a.user_id
           WHERE t.amount_cents >= 100000
           ORDER BY t.created_at DESC LIMIT 50"""
    ).fetchall()
    return render_template("alerts.html", failed=failed, large=large)