"""OWNER: Lead (backend). Transfers must be atomic, validated, idempotent."""
from flask import Blueprint
bp = Blueprint("transfers", __name__)

# TODO Lead: POST /transfer
#   - validate: amount_cents int > 0, recipient exists, not self, sufficient funds
#   - ONE transaction: debit, credit, INSERT transactions (reference = secrets.token_hex(8))
#   - rollback on error; unique idempotency_key so replays do nothing
#   - audit("transfer", reference)
# Home 1 builds transfer.html (the form); Lead owns the logic here.
