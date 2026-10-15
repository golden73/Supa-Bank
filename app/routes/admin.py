"""OWNER: Functionality 1. Staff user management. Every route uses @admin_required."""
from flask import Blueprint, request, redirect, url_for, render_template

from ..security import admin_required, audit
from ..db import get_db
from ..money import money

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/users")
@admin_required
def admin_users():
    rows = get_db().execute(
        "SELECT u.id, u.username, u.email, u.full_name, u.role, u.is_active, "
        "u.failed_logins, u.locked_until, a.account_number, a.balance_cents "
        "FROM users u LEFT JOIN accounts a ON a.user_id = u.id "
        "ORDER BY u.id"
    ).fetchall()
    return render_template("admin_users.html", users=rows, money=money)


@bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@admin_required
def toggle_user(user_id):
    db = get_db()
    user = db.execute("SELECT is_active FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        return redirect(url_for("admin.admin_users"))
    new_state = 0 if user["is_active"] else 1
    db.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_state, user_id))
    db.commit()
    # audit() defaults the actor to the session user (the admin). The target is
    # the affected account; never pass the target id as the actor.
    audit("toggle_user", str(user_id))
    return redirect(url_for("admin.admin_users"))


@bp.route("/users/<int:user_id>/unlock", methods=["POST"])
@admin_required
def unlock_user(user_id):
    db = get_db()
    db.execute("UPDATE users SET failed_logins = 0, locked_until = NULL WHERE id = ?", (user_id,))
    db.commit()
    audit("unlock_user", str(user_id))
    return redirect(url_for("admin.admin_users"))