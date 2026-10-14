"""OWNER: Functionality 2. Audit viewing + anomaly alerts (admin only)."""
from flask import Blueprint, render_template, current_app
from ..security import admin_required, audit
from ..db import get_db
bp = Blueprint("audit", __name__, url_prefix="/admin")

# Thresholds. Overridable via app config so the shared config.py stays untouched.
_DEFAULT_FAILED_LOGINS = 5
_DEFAULT_LARGE_TRANSFER_CENTS = 10_000
_DEFAULT_RECENT_MINUTES = 60


def _cfg(key, default):
    return current_app.config.get(key, default)


def _recent_sql():
    minutes = _cfg("AUDIT_RECENT_MINUTES", _DEFAULT_RECENT_MINUTES)
    return f"-{minutes} minutes"


def anomaly_alerts():
    """Stateless anomaly detection over recent activity. Nothing sensitive is logged."""
    db = get_db()
    recent = _recent_sql()
    failed_threshold = _cfg("AUDIT_FAILED_LOGIN_THRESHOLD", _DEFAULT_FAILED_LOGINS)
    large_cents = _cfg("AUDIT_LARGE_TRANSFER_CENTS", _DEFAULT_LARGE_TRANSFER_CENTS)

    alerts = []

    # Brute force: many failed logins from a single IP within the window.
    for ip, count in db.execute(
        "SELECT ip, COUNT(*) AS c FROM audit_log "
        "WHERE action = 'login_failed' AND ip IS NOT NULL "
        "AND created_at >= datetime('now', ?) "
        "GROUP BY ip HAVING COUNT(*) >= ?",
        (recent, failed_threshold)).fetchall():
        alerts.append({
            "type": "brute_force",
            "severity": "high",
            "message": f"{count} failed logins from {ip} in the last "
                       f"{_cfg('AUDIT_RECENT_MINUTES', _DEFAULT_RECENT_MINUTES)} min",
        })

    # Exfiltration: unusually large outgoing transfers within the window.
    for row in db.execute(
        "SELECT reference, amount_cents, from_account FROM transactions "
        "WHERE amount_cents >= ? AND created_at >= datetime('now', ?) "
        "ORDER BY created_at DESC LIMIT 50",
        (large_cents, recent)).fetchall():
        alerts.append({
            "type": "large_transfer",
            "severity": "medium",
            "message": f"Large transfer {row['reference']}: "
                       f"{row['amount_cents'] / 100:.2f} from account {row['from_account']}",
        })

    return alerts


def audit_rows(limit=200):
    db = get_db()
    return db.execute(
        "SELECT user_id, action, target, ip, created_at "
        "FROM audit_log ORDER BY id DESC LIMIT ?",
        (limit,)).fetchall()


@bp.route("/audit")
@admin_required
def audit_view():
    audit("view_audit")
    return render_template(
        "admin_audit.html",
        entries=audit_rows(),
        alerts=anomaly_alerts(),
        failed_threshold=_cfg("AUDIT_FAILED_LOGIN_THRESHOLD", _DEFAULT_FAILED_LOGINS),
        large_threshold=_cfg("AUDIT_LARGE_TRANSFER_CENTS", _DEFAULT_LARGE_TRANSFER_CENTS),
    )
