import os, sqlite3
from flask import g, current_app

def get_db():
    """One connection per request. ALWAYS use ? placeholders, never string formatting."""
    if "db" not in g:
        path = current_app.config["DATABASE"]
        if path != ":memory:":
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        g.db = sqlite3.connect(path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    with current_app.open_resource("schema.sql") as f:
        get_db().executescript(f.read().decode())
