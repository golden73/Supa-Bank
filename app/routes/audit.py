"""OWNER: Functionality 2. Audit viewing + anomaly alerts (admin only).

Thresholds are read from app config (see Config.AUDIT_*) so they can be tuned
per deployment or per test without editing source. No passwords or secrets are
ever written to or read from the audit trail.
"""
from flask import Blueprint, current_app, render_template

from ..security import admin_required
from ..db import get_db

bp = Blueprint("audit", __name__, url_prefix="/admin")


def _cfg(key, default):
    return current_app.config.get(key, default)


@bp.route("/audit")
@admin_required
def audit_view():
    rows = get_db().execute(
        "SELECT user_id, action, target, ip, created_at "
        "FROM audit_log ORDER BY id DESC LIMIT 200"
    ).fetchall()
    return render_template("audit.html", audit=rows)


@bp.route("/alerts")
@admin_required
def alerts():
    db = get_db()
    threshold = _cfg("AUDIT_FAILED_LOGIN_THRESHOLD", 5)
    large_cents = _cfg("AUDIT_LARGE_TRANSFER_CENTS", 100000)
    minutes = _cfg("AUDIT_RECENT_MINUTES", 60)

    # Accounts currently at/over the failed-login threshold.
    failed = db.execute(
        "SELECT id, username, failed_logins, locked_until FROM users "
        "WHERE failed_logins >= ? ORDER BY failed_logins DESC",
        (threshold,),
    ).fetchall()

    # Brute-force signal: many failed logins from one IP in the recent window.
    ips = db.execute(
        "SELECT ip, COUNT(*) AS count FROM audit_log "
        "WHERE action = 'login_failed' AND ip IS NOT NULL "
        "AND created_at >= datetime('now', ?) "
        "GROUP BY ip HAVING COUNT(*) >= ? ORDER BY count DESC",
        (f"-{minutes} minutes", threshold),
    ).fetchall()

    # Exfiltration signal: unusually large outgoing transfers.
    large = db.execute(
        """SELECT t.reference, t.amount_cents, t.created_at,
                  u.username, a.account_number
           FROM transactions t
           JOIN accounts a ON a.id = t.from_account
           JOIN users u ON u.id = a.user_id
           WHERE t.amount_cents >= ?
           ORDER BY t.created_at DESC LIMIT 50""",
        (large_cents,),
    ).fetchall()

    return render_template(
        "alerts.html",
        failed=failed,
        ips=ips,
        large=large,
        threshold=threshold,
        large_cents=large_cents,
        minutes=minutes,
    )
