from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect
from .config import Config
from . import db

csrf = CSRFProtect()

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    csrf.init_app(app)
    app.teardown_appcontext(db.close_db)

    from .routes import register, login, dashboard, profile, transfers, admin, audit
    for bp in (register.bp, login.bp, dashboard.bp, profile.bp, transfers.bp, admin.bp, audit.bp):
        app.register_blueprint(bp)

    @app.after_request
    def headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Content-Security-Policy"] = "default-src 'self'"
        resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(500)
    def safe_error(e):  # generic message, no stack traces or internals
        code = getattr(e, "code", 500)
        return f"Error {code}", code

    with app.app_context():
        db.init_db()
    return app
