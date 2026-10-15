"""OWNER: Home 2. Profile edit + customer-only history. Always filter by g.user['id']."""
import re
import sqlite3

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from ..security import login_required, audit
from ..db import get_db

bp = Blueprint("profile", __name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    db = get_db()
    error = None

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        if not 1 <= len(full_name) <= 80:
            error = "Name must be 1-80 characters."
        elif not _EMAIL_RE.match(email) or len(email) > 120:
            error = "Please enter a valid email."
        else:
            try:
                # Only ever update g.user's own row; no id comes from the request.
                db.execute(
                    "UPDATE users SET full_name = ?, email = ? WHERE id = ?",
                    (full_name, email, g.user["id"]),
                )
                db.commit()
            except sqlite3.IntegrityError:
                db.rollback()
                error = "That email is already in use."
            else:
                audit("profile_update")
                flash("Profile updated.")
                return redirect(url_for("profile.profile"))

    acct = db.execute(
        "SELECT account_number FROM accounts WHERE user_id = ?", (g.user["id"],)
    ).fetchone()
    return render_template("profile.html", user=g.user, account=acct, error=error)


@bp.route("/history")
@login_required
def history():
    rows = get_db().execute(
        """SELECT t.reference, t.amount_cents, t.note, t.created_at,
                  t.from_account = a.id AS outgoing
           FROM transactions t JOIN accounts a ON a.user_id = ?
           WHERE t.from_account = a.id OR t.to_account = a.id
           ORDER BY t.id DESC""",
        (g.user["id"],),
    ).fetchall()
    return render_template("history.html", transactions=rows)
