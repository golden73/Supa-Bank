"""Tests for admin user management: server-side role enforcement + audit trail."""
import pytest
from argon2 import PasswordHasher
from app import create_app
from app.db import get_db


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "t.db"),
        "WTF_CSRF_ENABLED": False,
    })
    ph = PasswordHasher()
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO users (username,email,full_name,password_hash,role) VALUES "
            "('admin','a@t','Admin',?,'admin')", (ph.hash("Admin#Demo2026"),))
        db.execute(
            "INSERT INTO users (username,email,full_name,password_hash,role) VALUES "
            "('bob','b@t','Bob',?,'customer')", (ph.hash("Bob#Demo2026"),))
        db.execute("INSERT INTO accounts (user_id,account_number,balance_cents) VALUES (1,'SB-1',0)")
        db.execute("INSERT INTO accounts (user_id,account_number,balance_cents) VALUES (2,'SB-2',50000)")
        db.commit()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def login_as(client, uid):
    with client.session_transaction() as s:
        s["user_id"] = uid
        s["permanent"] = True


def test_customer_cannot_access_admin_users(client):
    login_as(client, 2)
    assert client.get("/admin/users").status_code == 403


def test_customer_cannot_toggle_or_unlock(client):
    login_as(client, 2)
    assert client.post("/admin/users/2/toggle").status_code == 403
    assert client.post("/admin/users/2/unlock").status_code == 403


def test_admin_can_lock_user_and_audit_recorded(client):
    login_as(client, 1)
    r = client.post("/admin/users/2/toggle")
    assert r.status_code == 302
    with client.application.app_context():
        row = get_db().execute("SELECT is_active FROM users WHERE id=2").fetchone()
        assert row["is_active"] == 0
        log = get_db().execute(
            "SELECT action, target FROM audit_log WHERE action='toggle_user' AND user_id=1"
        ).fetchone()
        assert log is not None
        assert log["target"] == "2"


def test_admin_can_unlock_and_clear_lockout(client):
    with client.application.app_context():
        get_db().execute("UPDATE users SET is_active=0, failed_logins=5, locked_until='2099-01-01' WHERE id=2")
        get_db().commit()
    login_as(client, 1)
    assert client.post("/admin/users/2/unlock").status_code == 302
    with client.application.app_context():
        row = get_db().execute("SELECT is_active, failed_logins, locked_until FROM users WHERE id=2").fetchone()
        assert row["is_active"] == 0          # unlock only clears lockout, not active state
        assert row["failed_logins"] == 0
        assert row["locked_until"] is None


def test_admin_page_never_exposes_password_hashes(client):
    login_as(client, 1)
    html = client.get("/admin/users").data.decode()
    assert "Admin#Demo2026" not in html
    assert "$argon2" not in html


def test_toggle_unknown_user_redirects(client):
    login_as(client, 1)
    r = client.post("/admin/users/9999/toggle")
    assert r.status_code == 302


# --- CSRF is enabled here (production-like): the admin forms must carry a token ---

@pytest.fixture
def csrf_app(tmp_path):
    app = create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "csrf.db"),
        "WTF_CSRF_ENABLED": True,
    })
    ph = PasswordHasher()
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO users (username,email,full_name,password_hash,role) VALUES ('admin','a@t','Admin',?,'admin')", (ph.hash("pw"),))
        db.execute("INSERT INTO users (username,email,full_name,password_hash,role) VALUES ('bob','b@t','Bob',?,'customer')", (ph.hash("pw"),))
        db.execute("INSERT INTO accounts (user_id,account_number,balance_cents) VALUES (1,'SB-1',0)")
        db.execute("INSERT INTO accounts (user_id,account_number,balance_cents) VALUES (2,'SB-2',0)")
        db.commit()
    return app


def _csrf_token(html: bytes) -> str:
    import re
    m = re.search(rb'name="csrf_token" value="([^"]+)"', html)
    assert m, "csrf_token missing from admin form"
    return m.group(1).decode()


def test_admin_form_includes_csrf_token(csrf_app):
    client = csrf_app.test_client()
    login_as(client, 1)
    html = client.get("/admin/users").data
    assert b'name="csrf_token"' in html


def test_admin_toggle_works_with_csrf_token(csrf_app):
    client = csrf_app.test_client()
    login_as(client, 1)
    token = _csrf_token(client.get("/admin/users").data)
    r = client.post("/admin/users/2/toggle", data={"csrf_token": token})
    assert r.status_code == 302


def test_admin_toggle_blocked_without_csrf_token(csrf_app):
    client = csrf_app.test_client()
    login_as(client, 1)
    r = client.post("/admin/users/2/toggle")
    assert r.status_code == 400