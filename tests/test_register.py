def test_register_ok_and_hashed(client, app):          # CHECK: fixture names in tests/conftest.py
    r = client.post("/register", data={
        "username": "newuser", "full_name": "New User",
        "email": "new@example.com", "password": "Sup3rSecret99",
    })
    assert r.status_code in (302, 303)
    with app.app_context():
        from app.db import get_db
        row = get_db().execute(
            "SELECT password_hash FROM users WHERE username = ?", ("newuser",)
        ).fetchone()
    assert row["password_hash"].startswith("$argon2")
    assert "Sup3rSecret99" not in row["password_hash"]


def test_register_rejects_bad_input(client):
    r = client.post("/register", data={
        "username": "x", "full_name": "", "email": "nope", "password": "short",
    })
    assert r.status_code == 400


def test_register_duplicate_is_generic(client):
    data = {"username": "dupuser", "full_name": "Dup",
            "email": "dup@example.com", "password": "Sup3rSecret99"}
    client.post("/register", data=data)
    r = client.post("/register", data=data)
    assert r.status_code == 400
    assert b"already" not in r.data.lower()