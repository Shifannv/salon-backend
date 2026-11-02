"""Canonical subscription plan prices for test fixtures.

Owner-approved authoritative production prices confirmed 2026-11-01.
See: backend/docs/verification/SUBSCRIPTION_PRICE_APPROVAL_2026-11-01.md

All test fixtures that reference current subscription plan prices must import from here
instead of duplicating numeric literals. A regression test in test_migration_policy.py
verifies this module matches the reconciliation harness constants.

NOTE: Integration tests that REPLAY the 0049 SQL migration (test_plan_prices_sql.py,
test_subscription_billing_sql.py) correctly assert 1675/2932 because those are the values
the immutable SQL produces from the 0031 seed. Those tests should NOT import from here.
"""
from decimal import Decimal

# Growth plan — owner-confirmed production prices
GROWTH_1M = Decimal("449.00")
GROWTH_1M_PAISE = 44900  # ₹449.00 in Indian paisa
GROWTH_6M = Decimal("2419.00")
GROWTH_12M = Decimal("4299.00")

# Premium plan — current owner-approved catalog
PREMIUM_6M = Decimal("3499.00")
PREMIUM_12M = Decimal("6199.00")
