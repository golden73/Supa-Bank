"""OWNER: Home 2. Profile edit + customer-only history. Always filter by g.user['id']."""
from flask import Blueprint, g, request, redirect, url_for, render_template, flash

from ..security import login_required, audit
from ..db import get_db

bp = Blueprint("profile", __name__)


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    db = get_db()
    error = None
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        if 1 <= len(full_name) <= 80:
            db.execute("UPDATE users SET full_name = ? WHERE id = ?", (full_name, g.user["id"]))
            db.commit()
            g.user["full_name"] = full_name
            audit("profile_update")
            return redirect(url_for("profile.profile"))
        error = "Name must be 1-80 characters."
    return render_template("profile.html", user=g.user, error=error)


@bp.route("/history")
@login_required
def history():
    rows = get_db().execute(
        """SELECT t.reference, t.amount_cents, t.note, t.created_at,
                  t.from_account = a.id AS outgoing
           FROM transactions t JOIN accounts a ON a.user_id = ?
           WHERE t.from_account = a.id OR t.to_account = a.id
           ORDER BY t.created_at DESC""", (g.user["id"],)).fetchall()
    return render_template("history.html", transactions=rows)