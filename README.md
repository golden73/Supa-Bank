# Vault24 Backend (Flask + SQLite)

## Setup
```
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # set SECRET_KEY (export it, or use your shell/IDE)
python seed.py              # fictional users: alice, bob, admin
flask --app app run --debug
pytest
```

## Layout / who owns what (edit ONLY your own files)
| Person | Files |
|---|---|
| Lead (backend) | app/security.py, config.py, db.py, schema.sql, __init__.py, seed.py, app/routes/transfers.py, README (threat model) |
| Login 1 | app/routes/register.py, templates/register.html, tests/test_register.py |
| Login 2 | app/routes/login.py, templates/login.html, tests/test_login.py |
| Home 1 | app/routes/dashboard.py, templates/base.html, templates/dashboard.html, templates/transfer.html, static/style.css |
| Home 2 | app/routes/profile.py, templates/profile.html, templates/history.html, tests/test_idor.py |
| Functionality 1 | app/routes/admin.py, templates/admin_users.html, tests/test_admin.py |
| Functionality 2 | app/routes/audit.py, templates/admin_audit.html, tests/test_audit.py, README sections |

Shared files (security.py, schema.sql, config.py, __init__.py, requirements.txt): ask the Lead.

## Rules
Parameterized queries only (`?`). Money is integer cents. Use `@login_required` / `@admin_required`.
Filter by `g.user["id"]`, never a user-supplied ID. Never log secrets. Feature branches + PR review.

## AI-use disclosure (fill in)
Tool / purpose / what was reviewed or changed: ...
