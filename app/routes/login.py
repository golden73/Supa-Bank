"""OWNER: Login 2. Login, logout, sessions, lockout (login.html + tests/test_login.py)."""
from datetime import datetime, timezone, timedelta

from argon2 import PasswordHasher
from flask import Blueprint, render_template, request, redirect, url_for, session, current_app

from ..security import audit
from ..db import get_db

bp = Blueprint("login", __name__)
ph = PasswordHasher()


def _parse_lockout(value):
    """Parse a stored lockout timestamp to an aware UTC datetime.

    Stored values may be tz-aware (from .isoformat() of an aware datetime) or
    tz-naive (e.g. seeded by a test). Naive values are treated as UTC so the
    comparison below never raises "offset-naive vs offset-aware".
    """
    if not value:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()

    # Read lockout thresholds from the running app config, not the class default,
    # so tests and deployments can tune them without editing source.
    max_failed = current_app.config["MAX_FAILED_LOGINS"]
    lockout_minutes = current_app.config["LOCKOUT_MINUTES"]

    ok = False
    if user and user["is_active"]:
        locked_until = _parse_lockout(user["locked_until"])
        if locked_until and datetime.now(timezone.utc) < locked_until:
            audit("login_failed", "locked", user["id"])
            return render_template("login.html", error="Account is locked. Try again later."), 403
        try:
            ok = ph.verify(user["password_hash"], password)
        except Exception:
            ok = False

    if not ok:
        if user and user["is_active"]:
            failed = (user["failed_logins"] or 0) + 1
            locked = None
            if failed >= max_failed:
                locked = (datetime.now(timezone.utc) + timedelta(minutes=lockout_minutes)).isoformat()
            db.execute(
                "UPDATE users SET failed_logins = ?, locked_until = ? WHERE id = ?",
                (failed, locked, user["id"]),
            )
            db.commit()
            audit("login_failed", "bad_password", user["id"])
        else:
            audit("login_failed", "unknown_user")
        return render_template("login.html", error="Invalid credentials."), 401

    db.execute("UPDATE users SET failed_logins = 0, locked_until = NULL WHERE id = ?", (user["id"],))
    db.commit()

    session.clear()
    session["user_id"] = user["id"]
    session.permanent = True
    audit("login_ok")
    return redirect(url_for("dashboard.dashboard"))


@bp.route("/logout")
def logout():
    session.clear()
    audit("logout")
    return redirect(url_for("login.login"))