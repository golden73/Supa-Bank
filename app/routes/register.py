"""OWNER: Login 1. Registration only (route + register.html + tests/test_register.py)."""
from flask import Blueprint
bp = Blueprint("register", __name__)

# TODO Login 1: GET/POST /register
#   - validate username, email, password strength on the server
#   - generic message on duplicates (don't reveal which email exists)
#   - hash with argon2.PasswordHasher, INSERT users row + accounts row
#     (account_number like V24-xxxx, starting balance in cents)
#   - audit("register")
