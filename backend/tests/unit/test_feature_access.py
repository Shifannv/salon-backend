from datetime import UTC, datetime, timedelta

from app.domain.services.feature_access import (
    FeatureOverride,
    audience_for,
    is_enabled,
    resolve_features,
)

NOW = datetime(2026, 11, 1, tzinfo=UTC)
MATRIX = {
    "split_bill": {"trial": True, "growth": False, "premium": True},
    "reports": {"trial": True, "growth": True, "premium": True},
}


def resolve(audience, overrides=None):
    return resolve_features(audience=audience, matrix=MATRIX, overrides=overrides or {}, now=NOW)


def test_audience_paid_plan_beats_trial():
    assert audience_for(entitlement_active=True, tier=1, trial_active=True) == "growth"
    assert audience_for(entitlement_active=True, tier=2, trial_active=False) == "premium"


def test_audience_trial_and_ended():
    assert audience_for(entitlement_active=False, tier=None, trial_active=True) == "trial"
    assert audience_for(entitlement_active=False, tier=None, trial_active=False) is None


def test_matrix_columns_are_independent():
    assert is_enabled(resolve("growth"), "split_bill") is False
    assert is_enabled(resolve("premium"), "split_bill") is True
    assert is_enabled(resolve("trial"), "split_bill") is True


def test_no_audience_locks_everything():
    resolved = resolve(None)
    assert not any(v["enabled"] for v in resolved.values())


def test_live_override_unlocks_one_growth_salon():
    resolved = resolve("growth", {"split_bill": FeatureOverride(True, NOW + timedelta(days=3))})
    assert resolved["split_bill"] == {"enabled": True, "source": "override", "plans": ["premium"]}


def test_expired_override_reverts_to_plan_rule():
    resolved = resolve("growth", {"split_bill": FeatureOverride(True, NOW - timedelta(seconds=1))})
    assert resolved["split_bill"] == {"enabled": False, "source": "plan", "plans": ["premium"]}


def test_override_can_lock_a_feature_the_plan_gives():
    assert is_enabled(resolve("premium", {"reports": FeatureOverride(False)}), "reports") is False


def test_unknown_key_is_locked():
    assert is_enabled(resolve("premium"), "nope") is False
