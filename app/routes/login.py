"""OWNER: Login 2. Login, logout, sessions, lockout (login.html + tests/test_login.py)."""
from datetime import datetime, timezone, timedelta

from argon2 import PasswordHasher
from flask import Blueprint, render_template, request, redirect, url_for, session

from ..security import audit
from ..db import get_db
from ..config import Config

bp = Blueprint("login", __name__)
ph = PasswordHasher()


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

    ok = False
    if user and user["is_active"]:
        locked_until = user["locked_until"]
        if locked_until and datetime.now(timezone.utc) < datetime.fromisoformat(locked_until):
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
            if failed >= Config.MAX_FAILED_LOGINS:
                locked = (datetime.now(timezone.utc) + timedelta(minutes=Config.LOCKOUT_MINUTES)).isoformat()
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