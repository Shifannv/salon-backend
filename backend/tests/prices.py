"""Canonical subscription plan prices for test fixtures.

Owner-approved authoritative production prices confirmed 2026-10-31 (Path A).
See: backend/docs/verification/0049_SUBSCRIPTION_PRICE_RECONCILIATION_2026-10-31.md

All test fixtures that reference current subscription plan prices must import from here
instead of duplicating numeric literals. A regression test in test_migration_policy.py
verifies this module matches the reconciliation harness constants.

NOTE: Integration tests that REPLAY the 0049 SQL migration (test_plan_prices_sql.py,
test_subscription_billing_sql.py) correctly assert 1675/2932 because those are the values
the immutable SQL produces from the 0031 seed. Those tests should NOT import from here.
"""
from decimal import Decimal

# Growth plan — owner-confirmed production prices
GROWTH_1M = Decimal("499.00")
GROWTH_1M_PAISE = 49900  # ₹499.00 in Indian paisa
GROWTH_6M = Decimal("2000.00")
GROWTH_12M = Decimal("2999.00")

# Premium plan — unchanged from 0049 SQL targets
PREMIUM_6M = Decimal("2875.00")
PREMIUM_12M = Decimal("5032.00")
