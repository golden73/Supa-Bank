import pytest

from app import create_app
from models import db, User, Account, AuditLog


@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret",
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "WTF_CSRF_ENABLED": False,
    })

    with app.app_context():
        db.create_all()

        admin = User(
            username="admin",
            role="admin",
            is_active=True,
            password_hash="test-admin-hash"
        )

        customer = User(
            username="customer",
            role="customer",
            is_active=True,
            password_hash="test-customer-hash"
        )

        db.session.add_all([admin, customer])
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login_as(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def test_customer_gets_403_on_every_admin_route(client, app):
    with app.app_context():
        customer = User.query.filter_by(
            username="customer"
        ).first()

        customer_id = customer.id

    login_as(client, customer_id)

    routes = [
        ("/admin/users", "GET"),
        (f"/admin/users/{customer_id}/lock", "POST"),
        (f"/admin/users/{customer_id}/unlock", "POST"),
    ]

    for path, method in routes:
        response = client.open(path, method=method)
        assert response.status_code == 403


def test_admin_can_lock_user_and_action_is_audited(client, app):
    with app.app_context():
        admin = User.query.filter_by(
            username="admin"
        ).first()

        customer = User.query.filter_by(
            username="customer"
        ).first()

        admin_id = admin.id
        customer_id = customer.id

    login_as(client, admin_id)

    response = client.post(
        f"/admin/users/{customer_id}/lock"
    )

    assert response.status_code == 302

    with app.app_context():
        customer = db.session.get(User, customer_id)

        assert customer.is_active is False

        log = AuditLog.query.filter_by(
            admin_id=admin_id,
            target_user_id=customer_id,
            action="USER_LOCKED"
        ).first()

        assert log is not None


def test_admin_page_never_displays_password_hashes(client, app):
    with app.app_context():
        admin = User.query.filter_by(
            username="admin"
        ).first()

        admin_id = admin.id

    login_as(client, admin_id)

    response = client.get("/admin/users")

    assert response.status_code == 200
    assert b"test-admin-hash" not in response.data
    assert b"test-customer-hash" not in response.data