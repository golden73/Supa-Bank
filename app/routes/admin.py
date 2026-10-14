"""OWNER: Functionality 1. Staff user management. Every route uses @admin_required."""
from flask import Blueprint
from ..security import admin_required
bp = Blueprint("admin", __name__, url_prefix="/admin")

# TODO F1: list users/accounts, lock/unlock a user (set is_active), audit every action,
#   admin_users.html template, tests/test_admin.py (customer gets 403 on every route).
