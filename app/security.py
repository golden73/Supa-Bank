"""Shared security layer (Lead owns this). Every protected route uses these."""
from functools import wraps
from flask import session, g, abort, redirect, url_for, request
from .db import get_db

def current_user():
    uid = session.get("user_id")
    if uid is None:
        return None
    return get_db().execute(
        "SELECT * FROM users WHERE id = ? AND is_active = 1", (uid,)).fetchone()

def login_required(view):
    @wraps(view)
    def wrapped(*a, **kw):
        user = current_user()
        if user is None:
            session.clear()
            return redirect(url_for("login.login"))
        g.user = user
        return view(*a, **kw)
    return wrapped

def admin_required(view):
    """Role is read from the DB each request, never from the client or cookie."""
    @wraps(view)
    @login_required
    def wrapped(*a, **kw):
        if g.user["role"] != "admin":
            audit("admin_access_denied", request.path)
            abort(403)
        return view(*a, **kw)
    return wrapped

def owns_account(account_id):
    """Ownership check: the account must belong to the logged-in user."""
    row = get_db().execute(
        "SELECT 1 FROM accounts WHERE id = ? AND user_id = ?",
        (account_id, g.user["id"])).fetchone()
    if row is None:
        abort(404)  # 404 not 403, so we don't confirm other accounts exist

def audit(action, target=None, user_id=None):
    """Audit trail. NEVER pass passwords, tokens or other secrets here."""
    if user_id is None:
        user_id = session.get("user_id")
    db = get_db()
    db.execute("INSERT INTO audit_log (user_id, action, target, ip) VALUES (?,?,?,?)",
               (user_id, action, target, request.remote_addr))
    db.commit()
