"""OWNER: Functionality 2. Audit viewing + anomaly alert tests (admin only)."""
import pytest
from argon2 import PasswordHasher

from app import create_app
from app.db import get_db

ph = PasswordHasher()


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "t.db"),
        "WTF_CSRF_ENABLED": False,
        "AUDIT_FAILED_LOGIN_THRESHOLD": 3,
        "AUDIT_LARGE_TRANSFER_CENTS": 100000,
    })
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO users (username,email,full_name,password_hash,role) VALUES ('admin','a@t','Admin',?,'admin')", (ph.hash("pw"),))
        db.execute("INSERT INTO users (username,email,full_name,password_hash,role) VALUES ('cust','c@t','Cust',?,'customer')", (ph.hash("pw"),))
        db.execute("INSERT INTO users (username,email,full_name,password_hash,role) VALUES ('victim','v@t','Vic',?,'customer')", (ph.hash("pw"),))
        db.execute("INSERT INTO accounts (user_id,account_number,balance_cents) VALUES (1,'SB-1',0)")
        db.execute("INSERT INTO accounts (user_id,account_number,balance_cents) VALUES (2,'SB-2',100000)")
        db.execute("INSERT INTO accounts (user_id,account_number,balance_cents) VALUES (3,'SB-3',0)")
        # A secret hash that must never reach the page.
        app.config["_SECRET_HASH"] = ph.hash("SecretPass#123")
        db.execute("INSERT INTO users (username,email,full_name,password_hash,role) VALUES ('secret','s@t','Sec',?,'customer')", (app.config["_SECRET_HASH"],))
        # A large outgoing transfer.
        db.execute("INSERT INTO transactions (reference,idempotency_key,from_account,to_account,amount_cents,note) "
                   "VALUES ('big-ref','key-large',2,3,150000,'over limit')")
        db.commit()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def login_as(client, uid):
    with client.session_transaction() as s:
        s["user_id"] = uid


def test_anonymous_audit_redirects_to_login(app):
    r = app.test_client().get("/admin/audit")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_customer_cannot_read_audit(client):
    login_as(client, 2)
    assert client.get("/admin/audit").status_code == 403
    assert client.get("/admin/alerts").status_code == 403


def test_admin_sees_audit_and_alerts(client):
    login_as(client, 1)
    assert client.get("/admin/audit").status_code == 200
    alerts = client.get("/admin/alerts")
    assert alerts.status_code == 200           # would 500 if money() were undefined
    assert b"big-ref" in alerts.data           # large transfer listed


def test_alerts_never_leak_secrets(client):
    login_as(client, 1)
    secret = client.application.config["_SECRET_HASH"]
    body = client.get("/admin/alerts").get_data(as_text=True)
    assert secret not in body
    assert "SecretPass#123" not in body
    assert "$argon2" not in body


def test_alert_for_repeated_failures_by_ip(client):
    login_as(client, 1)
    with client.application.app_context():
        db = get_db()
        for _ in range(4):
            db.execute("INSERT INTO audit_log (user_id,action,target,ip) VALUES (2,'login_failed','auth','1.2.3.4')")
        db.commit()
    body = client.get("/admin/alerts").get_data(as_text=True)
    assert "1.2.3.4" in body
