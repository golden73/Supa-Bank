import pytest
from app import create_app
from app.db import get_db


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "t.db"),
        "WTF_CSRF_ENABLED": False,
    })
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO users (username,email,full_name,password_hash,role) "
            "VALUES ('c','c@x','C','x','customer')"
        )
        db.execute(
            "INSERT INTO accounts (user_id,account_number,balance_cents) VALUES (1,'SB-1',1000)"
        )
        db.commit()
    return app


@pytest.fixture
def client(app):
    return app.test_client()