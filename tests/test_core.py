import sqlite3

import pytest

from app.db import get_db


def test_dashboard_requires_login(client):
    assert client.get("/dashboard").status_code == 302


def test_root_redirects_to_login_when_anonymous(client):
    r = client.get("/")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_admin_blocked_for_customer(client):
    with client.session_transaction() as s:
        s["user_id"] = 1
    assert client.get("/admin/audit").status_code == 403


def test_balance_cannot_go_negative(client):
    with client.application.app_context():
        with pytest.raises(sqlite3.IntegrityError):
            get_db().execute("UPDATE accounts SET balance_cents = -5 WHERE id = 1")
