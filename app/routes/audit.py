"""OWNER: Functionality 2. Audit viewing + anomaly alerts (admin only)."""
from flask import Blueprint
from ..security import admin_required
from ..db import get_db
bp = Blueprint("audit", __name__, url_prefix="/admin")

@bp.route("/audit")
@admin_required
def audit_view():
    rows = get_db().execute(
        "SELECT user_id, action, target, ip, created_at FROM audit_log ORDER BY id DESC LIMIT 200").fetchall()
    return {"audit": [dict(r) for r in rows]}

# TODO F2: anomaly alerts (many failed logins, unusually large transfers), audit templates.
