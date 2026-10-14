import pytest
from app import create_app
from app.db import get_db

@pytest.fixture
def client(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "t.db"), "WTF_CSRF_ENABLED": False})
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO users (username,email,full_name,password_hash,role) VALUES ('c','c@x','C','x','customer')")
        db.execute("INSERT INTO accounts (user_id,account_number,balance_cents) VALUES (1,'V24-1',1000)")
        db.commit()
    return app.test_client()

def test_dashboard_requires_login(client):
    assert client.get("/dashboard").status_code == 302

def test_admin_blocked_for_customer(client):
    with client.session_transaction() as s:
        s["user_id"] = 1
    assert client.get("/admin/audit").status_code == 403

def test_balance_cannot_go_negative(client):
    with client.application.app_context():
        with pytest.raises(Exception):
            get_db().execute("UPDATE accounts SET balance_cents = -5 WHERE id = 1")
