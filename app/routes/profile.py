"""OWNER: Home 2. Profile edit + customer-only history. Always filter by g.user['id']."""
from flask import Blueprint, g
from ..security import login_required
from ..db import get_db
bp = Blueprint("profile", __name__)

# TODO Home 2: GET/POST /profile (update only g.user's row; validate; audit("profile_update")).
@bp.route("/history")
@login_required
def history():
    rows = get_db().execute(
        """SELECT t.reference, t.amount_cents, t.note, t.created_at,
                  t.from_account = a.id AS outgoing
           FROM transactions t JOIN accounts a ON a.user_id = ?
           WHERE t.from_account = a.id OR t.to_account = a.id
           ORDER BY t.created_at DESC""", (g.user["id"],)).fetchall()
    return {"transactions": [dict(r) for r in rows]}
