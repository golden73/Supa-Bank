"""OWNER: Functionality 2. Audit viewing + anomaly alert tests."""
import pytest
from argon2 import PasswordHasher
from app import create_app
from app.db import get_db

ph = PasswordHasher()


@pytest.fixture
def client(tmp_path):
    app = create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "t.db"),
        "WTF_CSRF_ENABLED": False,
    })
    with app.app_context():
        db = get_db()
        # 1=admin, 2=cust (customer), 3=victim (recipient), 4=secret (hash leak test)
        db.execute("INSERT INTO users (username,email,full_name,password_hash,role) "
                   "VALUES ('admin','a@vault24.test','Admin','x','admin')")
        db.execute("INSERT INTO accounts (user_id,account_number,balance_cents) VALUES (1,'V24-1000',0)")
        db.execute("INSERT INTO users (username,email,full_name,password_hash,role) "
                   "VALUES ('cust','c@vault24.test','Cust','x','customer')")
        db.execute("INSERT INTO accounts (user_id,account_number,balance_cents) VALUES (2,'V24-1001',100000)")
        db.execute("INSERT INTO users (username,email,full_name,password_hash,role) "
                   "VALUES ('victim','v@vault24.test','Vic','x','customer')")
        db.execute("INSERT INTO accounts (user_id,account_number,balance_cents) VALUES (3,'V24-1002',100000)")
        # a real argon2 hash stored only in users.password_hash; must never reach the page
        app.config["_SECRET_HASH"] = ph.hash("SecretPass#123")
        db.execute("INSERT INTO users (username,email,full_name,password_hash,role) "
                   "VALUES ('secret','s@vault24.test','Sec', ?, 'customer')",
                   (app.config["_SECRET_HASH"],))
        db.commit()
    return app.test_client()


def _login(client, user_id):
    with client.session_transaction() as s:
        s["user_id"] = user_id


def test_anonymous_audit_redirects_to_login(client):
    resp = client.get("/admin/audit")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_customer_cannot_read_audit(client):
    _login(client, 2)
    assert client.get("/admin/audit").status_code == 403


def test_admin_sees_audit_page(client):
    _login(client, 1)
    resp = client.get("/admin/audit")
    assert resp.status_code == 200
    assert "Audit log" in resp.text
    # the admin's own view_audit action is recorded and shown
    assert "view_audit" in resp.text


def test_audit_log_never_leaks_secrets(client):
    _login(client, 1)
    with client.application.app_context():
        secret = client.application.config["_SECRET_HASH"]
    resp = client.get("/admin/audit")
    body = resp.get_data(as_text=True)
    assert secret not in body               # argon2 hash never appears
    assert "SecretPass#123" not in body     # plaintext password never appears
    assert "$argon2" not in body            # no hash marker leaks either


def test_alert_many_failed_logins(client):
    _login(client, 1)
    with client.application.app_context():
        db = get_db()
        for _ in range(6):
            db.execute("INSERT INTO audit_log (user_id, action, target, ip) "
                       "VALUES (?, 'login_failed', 'auth', '1.2.3.4')", (2,))
        db.commit()
    body = client.get("/admin/audit").get_data(as_text=True)
    assert "1.2.3.4" in body
    assert "failed login" in body.lower()


def test_alert_large_transfer(client):
    _login(client, 1)
    with client.application.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO transactions (reference, idempotency_key, from_account, to_account, amount_cents, note) "
            "VALUES ('big-ref', 'key-large', 2, 3, 50000, 'overlimit')")
        db.commit()
    body = client.get("/admin/audit").get_data(as_text=True)
    assert "big-ref" in body
    assert "large transfer" in body.lower()
