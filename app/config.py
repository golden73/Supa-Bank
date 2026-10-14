import os, secrets

class Config:
    # Secrets come from the environment, never from source control.
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    DATABASE = os.environ.get("DATABASE", "instance/vault24.db")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"  # set 1 behind HTTPS
    PERMANENT_SESSION_LIFETIME = 1800  # 30 min
    MAX_FAILED_LOGINS = 5
    LOCKOUT_MINUTES = 15
    WTF_CSRF_ENABLED = True
