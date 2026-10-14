"""Creates fictional demo data: 2 customers + 1 admin. Run: python seed.py"""
from argon2 import PasswordHasher
from app import create_app
from app.db import get_db

ph = PasswordHasher()
USERS = [  # (username, email, full name, password, role, balance in cents)
    ("alice", "alice@vault24.test", "Alice Demo", "Alice#Demo2026", "customer", 100000),
    ("bob", "bob@vault24.test", "Bob Demo", "Bob#Demo2026", "customer", 50000),
    ("admin", "admin@vault24.test", "Admin Demo", "Admin#Demo2026", "admin", 0),
]
app = create_app()
with app.app_context():
    db = get_db()
    for i, (u, e, n, pw, role, bal) in enumerate(USERS, start=1):
        if db.execute("SELECT 1 FROM users WHERE username = ?", (u,)).fetchone():
            continue
        cur = db.execute("INSERT INTO users (username,email,full_name,password_hash,role) VALUES (?,?,?,?,?)",
                         (u, e, n, ph.hash(pw), role))
        db.execute("INSERT INTO accounts (user_id,account_number,balance_cents) VALUES (?,?,?)",
                   (cur.lastrowid, f"V24-{1000 + i}", bal))
    db.commit()
    print("Seeded: alice / bob (customers), admin (admin). Passwords are in seed.py (fictional).")
