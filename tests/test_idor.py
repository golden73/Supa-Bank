"""OWNER: Home 2. IDOR / ownership tests: history and profile must be per-user."""
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
        for uid, name in ((1, "Alice"), (2, "Bob"), (3, "Carol")):
            db.execute(
                "INSERT INTO users (username,email,full_name,password_hash,role) VALUES (?,?,?,?,'customer')",
                (name.lower(), f"{name.lower()}@t", name, ph.hash("pw")),
            )
        for uid, acct in ((1, "SB-1"), (2, "SB-2"), (3, "SB-3")):
            db.execute(
                "INSERT INTO accounts (user_id,account_number,balance_cents) VALUES (?,?,1000)",
                (uid, acct),
            )
        # Alice -> Bob (visible to both). Bob -> Carol (visible to Bob, NOT Alice).
        db.execute("INSERT INTO transactions (reference,idempotency_key,from_account,to_account,amount_cents) "
                   "VALUES ('ref-ab','k-ab',1,2,500)")
        db.execute("INSERT INTO transactions (reference,idempotency_key,from_account,to_account,amount_cents) "
                   "VALUES ('ref-bc','k-bc',2,3,700)")
        db.commit()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def login_as(client, uid):
    with client.session_transaction() as s:
        s["user_id"] = uid
        s["permanent"] = True


def test_history_renders_with_transactions(client):
    login_as(client, 1)
    r = client.get("/history")
    assert r.status_code == 200          # would 500 if money() were undefined
    assert b"ref-ab" in r.data


def test_history_hides_other_users_transactions(client):
    login_as(client, 1)
    body = client.get("/history").data
    assert b"ref-bc" not in body          # Bob -> Carol must not leak to Alice


def test_history_requires_login(app):
    assert app.test_client().get("/history").status_code == 302


def test_profile_update_only_touches_own_row(client):
    login_as(client, 1)
    r = client.post("/profile", data={"full_name": "Alice Two", "email": "alice2@example.com"})
    assert r.status_code == 302
    with client.application.app_context():
        db = get_db()
        assert db.execute("SELECT full_name, email FROM users WHERE id=1").fetchone()["full_name"] == "Alice Two"
        # Bob is untouched.
        assert db.execute("SELECT full_name FROM users WHERE id=2").fetchone()["full_name"] == "Bob"


def test_profile_rejects_bad_email(client):
    login_as(client, 1)
    r = client.post("/profile", data={"full_name": "Alice", "email": "not-an-email"})
    assert r.status_code == 200
    assert b"valid email" in r.data
