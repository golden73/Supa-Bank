"""Shared money formatting helper. All balances are integer cents."""
def money(cents):
    """Format an integer-cent amount as a dollar string, e.g. 12345 -> '$123.45'."""
    return f"${cents / 100:,.2f}"