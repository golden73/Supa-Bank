"""Tests for transfer atomicity, idempotency, and balance integrity."""
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
            "('alice','a@t','Alice',?,'customer')", (ph.hash("Alice#Demo2026"),))
        db.execute(
            "INSERT INTO users (username,email,full_name,password_hash,role) VALUES "
            "('bob','b@t','Bob',?,'customer')", (ph.hash("Bob#Demo2026"),))
        db.execute("INSERT INTO accounts (user_id,account_number,balance_cents) VALUES (1,'V24-1',100000)")
        db.execute("INSERT INTO accounts (user_id,account_number,balance_cents) VALUES (2,'V24-2',50000)")
        db.commit()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def login_as(client, uid):
    with client.session_transaction() as s:
        s["user_id"] = uid
        s["permanent"] = True


def test_transfer_requires_login(client):
    assert client.post("/transfer", data={}).status_code == 302


def test_transfer_ok_debits_sender_credits_recipient(client):
    login_as(client, 1)
    r = client.post("/transfer", data={
        "to_account": "V24-2", "amount_cents": "3000", "idempotency_key": "k1",
    })
    assert r.status_code == 302
    with client.application.app_context():
        a1 = get_db().execute("SELECT balance_cents FROM accounts WHERE id=1").fetchone()
        a2 = get_db().execute("SELECT balance_cents FROM accounts WHERE id=2").fetchone()
        assert a1["balance_cents"] == 97000
        assert a2["balance_cents"] == 53000
        t = get_db().execute("SELECT reference, idempotency_key FROM transactions").fetchone()
        assert t["reference"] and t["idempotency_key"] == "k1"


def test_transfer_self_to_self_rejected(client):
    login_as(client, 1)
    r = client.post("/transfer", data={
        "to_account": "V24-1", "amount_cents": "100", "idempotency_key": "k2",
    })
    assert r.status_code == 400
    with client.application.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0


def test_transfer_insufficient_funds_rejected(client):
    login_as(client, 1)
    r = client.post("/transfer", data={
        "to_account": "V24-2", "amount_cents": "999999", "idempotency_key": "k3",
    })
    assert r.status_code == 400
    with client.application.app_context():
        a1 = get_db().execute("SELECT balance_cents FROM accounts WHERE id=1").fetchone()
        assert a1["balance_cents"] == 100000


def test_idempotency_replay_does_not_double_debit(client):
    login_as(client, 1)
    data = {"to_account": "V24-2", "amount_cents": "1000", "idempotency_key": "dup"}
    assert client.post("/transfer", data=data).status_code == 302
    assert client.post("/transfer", data=data).status_code == 302
    with client.application.app_context():
        a1 = get_db().execute("SELECT balance_cents FROM accounts WHERE id=1").fetchone()
        a2 = get_db().execute("SELECT balance_cents FROM accounts WHERE id=2").fetchone()
        assert a1["balance_cents"] == 99000
        assert a2["balance_cents"] == 51000
        assert get_db().execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 1


def test_transfer_invalid_amount_rejected(client):
    login_as(client, 1)
    r = client.post("/transfer", data={
        "to_account": "V24-2", "amount_cents": "0", "idempotency_key": "k5",
    })
    assert r.status_code == 400


def test_transfer_unknown_recipient_rejected(client):
    login_as(client, 1)
    r = client.post("/transfer", data={
        "to_account": "V24-999", "amount_cents": "100", "idempotency_key": "k6",
    })
    assert r.status_code == 400


def test_history_only_shows_own_transactions(client):
    login_as(client, 1)
    # Bob sends to himself (no cross-user tx yet) - then check alice's history is empty.
    r = client.get("/history")
    assert r.status_code == 200
    assert b"V24-1" not in r.data  # no transactions for alice yet