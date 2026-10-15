```python
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from models import db, User, Account, AuditLog


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view_function):
    """Allow access only to authenticated administrators."""

    @login_required
    def wrapped_view(*args, **kwargs):
        if not current_user.is_admin:
            from flask import abort
            abort(403)

        return view_function(*args, **kwargs)

    wrapped_view.__name__ = view_function.__name__
    return wrapped_view


def record_admin_action(action, target_user_id, details):
    """Record an administrative action in the audit log."""

    log = AuditLog(
        admin_user_id=current_user.id,
        target_user_id=target_user_id,
        action=action,
        details=details,
    )

    db.session.add(log)


@admin_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    """Display users and their associated accounts."""

    users = User.query.order_by(User.id.asc()).all()

    accounts = Account.query.order_by(Account.id.asc()).all()

    return render_template(
        "admin_users.html",
        users=users,
        accounts=accounts,
    )


@admin_bp.route("/users/<int:user_id>/lock", methods=["POST"])
@admin_required
def lock_user(user_id):
    """Lock an active user account."""

    user = db.session.get(User, user_id)

    if user is None:
        flash("User not found.", "error")
        return redirect(url_for("admin.list_users"))

    if user.is_admin:
        flash("Administrator accounts cannot be locked here.", "error")
        return redirect(url_for("admin.list_users"))

    if user.is_active:
        user.is_active = False

        record_admin_action(
            action="USER_LOCKED",
            target_user_id=user.id,
            details="Administrator locked the user account.",
        )

        try:
            db.session.commit()
            flash("User locked successfully.", "success")
        except SQLAlchemyError:
            db.session.rollback()
            flash("Unable to lock the user. Please try again.", "error")
    else:
        flash("This user is already locked.", "info")

    return redirect(url_for("admin.list_users"))


@admin_bp.route("/users/<int:user_id>/unlock", methods=["POST"])
@admin_required
def unlock_user(user_id):
    """Unlock an inactive user account."""

    user = db.session.get(User, user_id)

    if user is None:
        flash("User not found.", "error")
        return redirect(url_for("admin.list_users"))

    if user.is_active:
        flash("This user is already active.", "info")
        return redirect(url_for("admin.list_users"))

    user.is_active = True

    record_admin_action(
        action="USER_UNLOCKED",
        target_user_id=user.id,
        details="Administrator unlocked the user account.",
    )

    try:
        db.session.commit()
        flash("User unlocked successfully.", "success")
    except SQLAlchemyError:
        db.session.rollback()
        flash("Unable to unlock the user. Please try again.", "error")

    return redirect(url_for("admin.list_users"))
```
