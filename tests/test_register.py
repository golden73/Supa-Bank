def test_register_ok_and_hashed(client, app):
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
    with app.app_context():
        from app.db import get_db
        acct = get_db().execute("SELECT account_number FROM accounts WHERE user_id = 1").fetchone()
    assert acct["account_number"].startswith("SB-")  # rebranded account prefix


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
    # Check only the error message, not the footer link
    error_text = r.data.decode().split('class="error"')[1].split('</p>')[0] if 'class="error"' in r.data.decode() else ''
    assert "already" not in error_text.lower()
    assert "could not create the account" in error_text.lower()