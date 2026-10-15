"""Tests for login/logout, lockout, and session handling."""
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
        "MAX_FAILED_LOGINS": 3,
        "LOCKOUT_MINUTES": 15,
    })
    ph = PasswordHasher()
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO users (username,email,full_name,password_hash,role) "
            "VALUES ('alice','a@t','Alice',?,'customer')",
            (ph.hash("Alice#Demo2026"),),
        )
        db.execute("INSERT INTO accounts (user_id,account_number,balance_cents) "
                   "VALUES (1,'SB-1',100000)")
        db.commit()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_login_page_get(client):
    assert client.get("/login").status_code == 200


def test_login_ok_sets_session(client):
    r = client.post("/login", data={"username": "alice", "password": "Alice#Demo2026"})
    assert r.status_code == 302
    with client.session_transaction() as s:
        assert s.get("user_id") == 1
        assert s.get("_permanent") is True


def test_login_bad_password_generic_message(client):
    r = client.post("/login", data={"username": "alice", "password": "wrong"})
    assert r.status_code == 401
    # Generic message must not reveal whether the user exists.
    assert b"Invalid credentials" in r.data
    assert b"alice" not in r.data


def test_unknown_user_same_generic_message(client):
    r = client.post("/login", data={"username": "nobody", "password": "x"})
    assert r.status_code == 401
    assert b"Invalid credentials" in r.data


def test_lockout_after_max_failed_logins(client):
    # MAX_FAILED_LOGINS = 3 in this fixture.
    for _ in range(3):
        client.post("/login", data={"username": "alice", "password": "wrong"})
    with client.application.app_context():
        row = get_db().execute(
            "SELECT failed_logins, locked_until FROM users WHERE id = 1"
        ).fetchone()
    assert row["failed_logins"] == 3
    assert row["locked_until"] is not None


def test_locked_account_rejected_with_403(client):
    with client.application.app_context():
        get_db().execute(
            "UPDATE users SET failed_logins=5, locked_until='2099-01-01T00:00:00' WHERE id=1"
        )
        get_db().commit()
    r = client.post("/login", data={"username": "alice", "password": "Alice#Demo2026"})
    assert r.status_code == 403
    assert b"locked" in r.data.lower()


def test_logout_clears_session(client):
    client.post("/login", data={"username": "alice", "password": "Alice#Demo2026"})
    with client.session_transaction() as s:
        assert s.get("user_id") == 1
    r = client.get("/logout")
    assert r.status_code == 302
    with client.session_transaction() as s:
        assert s.get("user_id") is None


def test_dashboard_requires_session_after_logout(client):
    client.post("/login", data={"username": "alice", "password": "Alice#Demo2026"})
    client.get("/logout")
    assert client.get("/dashboard").status_code == 302  # redirected to login