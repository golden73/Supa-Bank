import os
import sqlite3
from flask import g, current_app


def get_db():
    """One connection per request. ALWAYS use ? placeholders, never string formatting.

    isolation_level=None puts the connection in autocommit mode; write-heavy
    routes (transfers) open an explicit BEGIN IMMEDIATE ... COMMIT transaction
    so their read-check-write sequence is atomic. timeout gives concurrent
    writers a chance to wait out a lock instead of failing immediately.
    """
    if "db" not in g:
        path = current_app.config["DATABASE"]
        if path != ":memory:":
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        g.db = sqlite3.connect(path, timeout=10, isolation_level=None)
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
