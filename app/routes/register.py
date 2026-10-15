"""OWNER: Registration. Creates user + account with argon2 hash."""
import re
import secrets
import sqlite3

from argon2 import PasswordHasher
from flask import Blueprint, render_template, request, redirect, url_for

from ..security import audit
from ..db import get_db

bp = Blueprint("register", __name__)
ph = PasswordHasher()

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
STARTING_BALANCE_CENTS = 100000        # $1,000.00 in cents


def password_ok(pw: str) -> bool:
    return (
        10 <= len(pw) <= 128
        and re.search(r"[A-Za-z]", pw) is not None
        and re.search(r"\d", pw) is not None
    )


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get("username", "").strip()
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not (
        USERNAME_RE.match(username)
        and EMAIL_RE.match(email)
        and 1 <= len(full_name) <= 80
        and password_ok(password)
    ):
        return render_template(
            "register.html",
            error="Please check your details and try again.",
        ), 400

    db = get_db()
    try:
        pw_hash = ph.hash(password)
        cur = db.execute(
            "INSERT INTO users (username, email, full_name, password_hash) "
            "VALUES (?, ?, ?, ?)",
            (username, email, full_name, pw_hash),
        )
        user_id = cur.lastrowid
        account_number = "SB-" + "".join(secrets.choice("0123456789") for _ in range(9))
        db.execute(
            "INSERT INTO accounts (user_id, account_number, balance_cents) VALUES (?, ?, ?)",
            (user_id, account_number, STARTING_BALANCE_CENTS),
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        return render_template(
            "register.html",
            error="Could not create the account. Try different details.",
        ), 400
    except Exception:
        db.rollback()
        raise

    audit("register")
    return redirect(url_for("login.login"))