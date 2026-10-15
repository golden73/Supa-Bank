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
        db.execute("INSERT INTO accounts (user_id,account_number,balance_cents) VALUES (1,'SB-1',100000)")
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


def idem_key(client):
    """Load the transfer form once, then read the server-issued token."""
    client.get("/transfer")
    with client.session_transaction() as s:
        return s["idempotency_key"]


def test_transfer_requires_login(client):
    assert client.post("/transfer", data={}).status_code == 302


def test_transfer_ok_debits_sender_credits_recipient(client):
    login_as(client, 1)
    r = client.post("/transfer", data={
        "to_account": "SB-2", "amount": "30.00", "idempotency_key": idem_key(client),
    })
    assert r.status_code == 302
    with client.application.app_context():
        a1 = get_db().execute("SELECT balance_cents FROM accounts WHERE id=1").fetchone()
        a2 = get_db().execute("SELECT balance_cents FROM accounts WHERE id=2").fetchone()
        assert a1["balance_cents"] == 97000
        assert a2["balance_cents"] == 53000
        t = get_db().execute("SELECT reference FROM transactions").fetchone()
        assert t["reference"]


def test_transfer_self_to_self_rejected(client):
    login_as(client, 1)
    r = client.post("/transfer", data={
        "to_account": "SB-1", "amount": "1.00", "idempotency_key": idem_key(client),
    })
    assert r.status_code == 400
    with client.application.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0


def test_transfer_insufficient_funds_rejected(client):
    login_as(client, 1)
    r = client.post("/transfer", data={
        "to_account": "SB-2", "amount": "9999.00", "idempotency_key": idem_key(client),
    })
    assert r.status_code == 400
    with client.application.app_context():
        assert get_db().execute("SELECT balance_cents FROM accounts WHERE id=1").fetchone()[0] == 100000


def test_idempotency_replay_does_not_double_debit(client):
    login_as(client, 1)
    key = idem_key(client)
    data = {"to_account": "SB-2", "amount": "10.00", "idempotency_key": key}
    assert client.post("/transfer", data=data).status_code == 302
    assert client.post("/transfer", data=data).status_code == 302
    with client.application.app_context():
        assert get_db().execute("SELECT balance_cents FROM accounts WHERE id=1").fetchone()[0] == 99000
        assert get_db().execute("SELECT balance_cents FROM accounts WHERE id=2").fetchone()[0] == 51000
        assert get_db().execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 1


def test_transfer_rejects_bad_amounts(client):
    login_as(client, 1)
    for bad in ("0", "-5", "abc", "1.999"):
        key = idem_key(client)
        r = client.post("/transfer", data={"to_account": "SB-2", "amount": bad, "idempotency_key": key})
        assert r.status_code == 400, bad


def test_transfer_rejects_forged_idempotency_key(client):
    login_as(client, 1)
    r = client.post("/transfer", data={
        "to_account": "SB-2", "amount": "1.00", "idempotency_key": "not-a-valid-token",
    })
    assert r.status_code == 400


def test_transfer_unknown_recipient_rejected(client):
    login_as(client, 1)
    r = client.post("/transfer", data={
        "to_account": "SB-999", "amount": "1.00", "idempotency_key": idem_key(client),
    })
    assert r.status_code == 400
