import os
import secrets
from pathlib import Path


def _load_secret_key():
    """Return a stable SECRET_KEY.

    Precedence: environment variable, then a persisted file under instance/,
    then a freshly generated value saved to that file. Persisting the key keeps
    sessions valid across restarts and across multiple worker processes instead
    of silently breaking them with a new random key per process.
    """
    env = os.environ.get("SECRET_KEY")
    if env:
        return env
    root = Path(__file__).resolve().parent.parent
    instance = root / "instance"
    instance.mkdir(parents=True, exist_ok=True)
    key_file = instance / "secret_key"
    if key_file.exists():
        value = key_file.read_text().strip()
        if value:
            return value
    value = secrets.token_hex(32)
    key_file.write_text(value)
    try:
        os.chmod(key_file, 0o600)
    except OSError:
        pass
    return value


class Config:
    # Secrets come from the environment, never from source control.
    SECRET_KEY = _load_secret_key()
    DATABASE = os.environ.get("DATABASE", "instance/vault24.db")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"  # set 1 behind HTTPS
    PERMANENT_SESSION_LIFETIME = 1800  # 30 min
    MAX_FAILED_LOGINS = 5
    LOCKOUT_MINUTES = 15
    MAX_TRANSFER_CENTS = 1_000_000_00  # $1,000,000 per transfer
    WTF_CSRF_ENABLED = True
    # Anomaly thresholds (audit module). Overridable per-deployment/test.
    AUDIT_FAILED_LOGIN_THRESHOLD = 5
    AUDIT_LARGE_TRANSFER_CENTS = 100000  # $1,000.00
    AUDIT_RECENT_MINUTES = 60
