"""OWNER: Login 2. Login, logout, sessions, lockout (login.html + tests/test_login.py)."""
from flask import Blueprint
bp = Blueprint("login", __name__)

# TODO Login 2: POST /logout and real login logic
#   - verify Argon2 hash, generic "invalid credentials" message
#   - session.clear() BEFORE setting session["user_id"]; session.permanent = True
#   - lockout via users.failed_logins / locked_until (Config.MAX_FAILED_LOGINS, LOCKOUT_MINUTES)
#   - audit("login_ok" / "login_failed" / "logout")

@bp.route("/login", methods=["GET", "POST"])
def login():
    return "TODO login page", 501
