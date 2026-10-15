# Vault24 — 24-Hour Digital Banking Security Prototype

Stack: **Python Flask 3 + SQLite + Argon2id + vanilla HTML/CSS/Jinja templates**.
All data is fictional. No real money, banking platforms or personal financial information.

## Setup
```
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export SECRET_KEY="$(python -c 'import secrets;print(secrets.token_hex(32))')"  # or rely on the persisted instance/secret_key
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
| 03 | Dashboard — account + balance + recent transactions for `g.user` only | Done |
| 04 | Transfers — atomic `BEGIN IMMEDIATE/COMMIT/ROLLBACK`, guarded debit, `secrets.token_hex` reference, server-issued idempotency token | Done |
| 05 | History — customer's own transactions only, joined via the user's account | Done |
| 06 | Profile editing — updates only `g.user`'s row (name + email), validated | Done |
| 07 | Staff/admin — every admin route uses `@admin_required` (role read from DB); lock/unlock with CSRF-protected forms | Done |
| 08 | Audit trail + anomaly alerts — logins, transfers, profile changes, admin actions; brute-force-by-IP and large-transfer alerts | Done |

## Security design notes
- **Idempotency:** the transfer form carries a hidden 32-hex token issued by the server
  (`session["idempotency_key"]`). It is validated and, together with the `UNIQUE`
  constraint on `transactions.idempotency_key`, makes a double submit a no-op. The token
  rotates after every attempt.
- **Atomicity:** the transfer opens `BEGIN IMMEDIATE`, re-checks for a replay, performs a
  guarded debit (`WHERE balance_cents >= ?`) and checks `cursor.rowcount`, then credits and
  inserts the transaction. Any failure rolls back the whole thing.
- **Secret key:** read from `SECRET_KEY`, else persisted to `instance/secret_key` (0600) so
  sessions survive restarts and multiple workers.
- **`money` is a Jinja global** so a view that forgets to pass it can't 500 a page.

## Threat model (3 risks + mitigations)
1. **Account takeover via credential stuffing.** Argon2id hashing, a generic "Invalid
   credentials" message (no user enumeration), server-side lockout after `MAX_FAILED_LOGINS`
   failed attempts for `LOCKOUT_MINUTES`, and a per-IP brute-force alert.
2. **IDOR / broken object-level authorization.** Every route filters by `g.user["id"]`
   (never an ID from the URL); `@admin_required` re-reads the role from the DB each request;
   ownership checks return 404 (not 403) so other accounts' existence isn't confirmed.
3. **Double-spend / inconsistent balance.** Transfers run in one transaction with a guarded
   debit and a `UNIQUE` idempotency key, so replays and insufficient-funds cases change
   nothing.

## Known limitations
- Single SQLite file (fine for a prototype; not for production concurrency).
- No password reset flow; no 2FA (out of scope for the 24-hour build).
- Lockout timestamps are stored as ISO strings; naive values are treated as UTC.
- Rate limiting is limited to login lockout (no global per-route limiter).
- `logout` is a GET link (state change via GET); should be POST in a hardened build.

## Tests & fixes record
- `pytest` → **41 passing**.
- Added `tests/test_idor.py` (history isolation + profile ownership) and `tests/test_audit.py`
  (audit/alerts access, no-secret-leak, IP brute-force), plus CSRF-enabled admin tests.
- Fixed: `/history` and `/admin/alerts` returned 500 (`money` was undefined — now a Jinja
  global); `POST /profile` raised `TypeError` on `sqlite3.Row` item assignment; admin
  lock/unlock forms were missing `{{ csrf_token() }}` (400 under CSRF); transfers used the
  user-typed `amount_cents`/idempotency key (now dollars + server token); `test_core`
  negative-balance test now asserts `sqlite3.IntegrityError`.
- Reconciled the `audit-functionality` branch's work into `app/routes/audit.py`
  (config-driven thresholds, IP-grouped brute-force detection).

## Team & contributions
| Git username | Contribution |
|---|---|
| `GoldenChisenga` / `golden73` | Repo setup, skeleton, shared security layer, transfers, integration, README/threat model |
| `Ivwananji223` | Registration, login, dashboard, profile, admin, audit, templates, tests (feature branch) |
| `Kilo` (AI tool) | Scaffolding/review assistance — see AI-use disclosure |

> Team members: confirm/link your name to your module from the ownership table above before
> the deadline so each contribution is recorded as required.

## AI-use disclosure
Tool / purpose / what was reviewed or changed: **Kilo (kilo-auto/free)** was used to scaffold
and review the codebase. Purpose: read the existing skeleton, integrate the login/register and
admin work, and review diffs for security compliance. Reviewed/changed: reverted the
SupaBank→Vault24 rebrand; fixed a tz-naive/aware datetime crash in the lockout check; made
lockout thresholds read from `current_app.config`; corrected `audit()` so the actor defaults
to the session user; consolidated the duplicated `money()` helper into `app/money.py`; renamed
`Register.html` → `register.html`. A later pass (this repo) repaired the history/profile/alerts
runtime defects, added a server-issued idempotency token and `BEGIN IMMEDIATE` transfers,
hardened the secret key, reconciled the audit alerts work, and expanded the test suite. All
logic verified by running `pytest` (41 passing) and an end-to-end browser-style smoke test.
