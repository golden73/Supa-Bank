# Vault24 — 24-Hour Digital Banking Security Prototype

Stack: **Python Flask 3 + SQLite + Argon2id + vanilla HTML/CSS/Jinja templates**.
All data is fictional. No real money, banking platforms or personal financial information.

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
| Lead (backend) | app/security.py, config.py, db.py, schema.sql, __init__.py, money.py, seed.py, app/routes/transfers.py, README (threat model) |
| Login 1 | app/routes/register.py, templates/register.html, tests/test_register.py |
| Login 2 | app/routes/login.py, templates/login.html, tests/test_login.py |
| Home 1 | app/routes/dashboard.py, templates/base.html, templates/dashboard.html, templates/transfer.html, static/style.css |
| Home 2 | app/routes/profile.py, templates/profile.html, templates/history.html, tests/test_idor.py |
| Functionality 1 | app/routes/admin.py, templates/admin_users.html, tests/test_admin.py |
| Functionality 2 | app/routes/audit.py, templates/audit.html, templates/alerts.html, tests/test_audit.py, README sections |

Shared files (security.py, schema.sql, config.py, __init__.py, requirements.txt): ask the Lead.

## Rules
Parameterized queries only (`?`). Money is integer cents. Use `@login_required` / `@admin_required`.
Filter by `g.user["id"]`, never a user-supplied ID. Never log secrets. Feature branches + PR review.

## Implemented features
| # | Module | Status |
|---|---|---|
| 01 | Registration — server-side validation, Argon2id hash, generic duplicate message | Done |
| 02 | Login/logout/sessions — secure cookies, `session.clear()` before re-set, lockout after `MAX_FAILED_LOGINS` | Done |
| 03 | Dashboard — account + balance for `g.user` only, filtered by `g.user["id"]` | Done |
| 04 | Transfers — atomic `BEGIN/COMMIT/ROLLBACK`, balance guard, `secrets.token_hex(8)` reference, idempotency key | Done |
| 05 | History — customer's own transactions only, joined via the user's account | Done |
| 06 | Profile editing — updates only `g.user`'s row, ownership enforced by the route | Done |
| 07 | Staff/admin — every admin route uses `@admin_required` (role read from DB) | Done |
| 08 | Audit trail — logins, transfers, profile changes, admin actions; never passwords/secrets | Done |

## Threat model (3 risks + mitigations)
1. **Account takeover via credential stuffing.** Mitigation: Argon2id hashing, generic "Invalid credentials" message (no user/enumeration leak), server-side lockout after 5 failed attempts for 15 minutes, and `failed_logins`/`locked_until` reset on success.
2. **IDOR / broken object-level authorization.** Mitigation: every route filters by `g.user["id"]` (never an ID from the URL); `@admin_required` re-reads the role from the DB each request; admin endpoints return 404 (not 403) for resources that don't exist to avoid confirming their presence.
3. **Inconsistent balance / double-spend.** Mitigation: transfers run in one transaction with `BEGIN/COMMIT/ROLLBACK`; the debit uses `WHERE balance_cents >= ?` and checks `total_changes`; the idempotency key is UNIQUE so a replay inserts nothing and is treated as success.

## Known limitations
- Single SQLite file (no production concurrency; fine for a prototype).
- No password reset flow (out of scope for the 24-hour build).
- Lockout timestamps are stored as ISO strings; naive values are interpreted as UTC.
- No rate limiting beyond login lockout.

## AI-use disclosure
Tool / purpose / what was reviewed or changed: **Kilo (kilo-auto/free)** was used to scaffold and review the codebase. Purpose: read the existing skeleton, merge PR #1 (login/register) and PR #2 (admin), and review the diffs for security compliance. Reviewed/changed: reverted the SupaBank→Vault24 rebrand; fixed a tz-naive/aware datetime crash in the lockout check; made lockout thresholds read from `current_app.config` instead of the class default; corrected `audit()` so the actor defaults to the session user rather than the target; consolidated the duplicated `money()` helper into `app/money.py`; renamed `Register.html` → `register.html`; added `tests/test_login.py`, `tests/test_admin.py`, `tests/test_transfers.py`. All logic was verified by running `pytest` (28 passing).
