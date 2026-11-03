"""Consent rules: all three confirmations are required, marketing is separate, versions decide 'needs consent'."""

import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError as SchemaError

from app.api.v1.routes import consents
from app.api.v1.schemas.consent import ConsentRequest, MarketingChoiceRequest
from app.core.config import settings
from app.core.exceptions import ValidationError
from tests.conftest import make_profile


def request(**over):
    base = {"source": "customer_app", "accept_terms": True, "accept_privacy": True, "age_13_plus": True}
    return ConsentRequest(**{**base, **over})


def test_marketing_defaults_to_off_and_unknown_fields_are_refused():
    assert request().marketing is False
    with pytest.raises(SchemaError):
        request(role="super_admin")
    with pytest.raises(SchemaError):
        request(source="somewhere_else")


@pytest.mark.parametrize("missing", ["accept_terms", "accept_privacy", "age_13_plus"])
async def test_each_required_confirmation_must_be_true(missing):
    with patch.object(consents, "ConsentRepository") as repo:
        repo.return_value.record = AsyncMock()
        with pytest.raises(ValidationError):
            await consents.record_consent(request(**{missing: False}), make_profile(), AsyncMock())
        repo.return_value.record.assert_not_awaited()


async def test_recording_stores_versions_and_the_marketing_choice_then_reports_status():
    stored = {}

    async def record(user_id, source, answers):
        stored.update({kind: (version, granted) for kind, version, granted in answers})

    async def latest(user_id):
        return {kind: {"version": version, "granted": granted} for kind, (version, granted) in stored.items()}

    with patch.object(consents, "ConsentRepository") as repo:
        repo.return_value.record = AsyncMock(side_effect=record)
        repo.return_value.latest = AsyncMock(side_effect=latest)
        done = await consents.record_consent(request(marketing=True), make_profile(), AsyncMock())
    assert stored["terms"] == (settings.terms_version, True)
    assert stored["privacy"] == (settings.privacy_version, True)
    assert done.needs_consent is False and done.marketing is True and done.age_13_plus is True


def status_for(latest):
    return consents._status(latest)


def test_nothing_accepted_needs_consent():
    assert status_for({}).needs_consent is True


def test_an_older_policy_version_needs_consent_again(monkeypatch):
    latest = {
        "terms": {"version": "2026-10-26", "granted": True},
        "privacy": {"version": "2026-10-26", "granted": True},
        "age_13_plus": {"version": "1", "granted": True},
    }
    assert status_for(latest).needs_consent is False
    monkeypatch.setattr(settings, "privacy_version", "2027-01-01")
    assert status_for(latest).needs_consent is True


def test_a_withdrawn_marketing_choice_does_not_force_consent_again():
    latest = {
        "terms": {"version": settings.terms_version, "granted": True},
        "privacy": {"version": settings.privacy_version, "granted": True},
        "age_13_plus": {"version": "1", "granted": True},
        "marketing": {"version": "1", "granted": False},
    }
    result = status_for(latest)
    assert result.needs_consent is False and result.marketing is False


async def test_marketing_can_be_withdrawn_on_its_own_without_touching_the_other_answers():
    stored = []

    async def record(user_id, source, answers):
        stored.extend(answers)

    async def latest(user_id):
        return {
            "terms": {"version": settings.terms_version, "granted": True},
            "privacy": {"version": settings.privacy_version, "granted": True},
            "age_13_plus": {"version": "1", "granted": True},
            "marketing": {"version": "1", "granted": stored[-1][2]},
        }

    with patch.object(consents, "ConsentRepository") as repo:
        repo.return_value.record = AsyncMock(side_effect=record)
        repo.return_value.latest = AsyncMock(side_effect=latest)
        done = await consents.set_marketing_choice(
            MarketingChoiceRequest(source="customer_app", marketing=False), make_profile(), AsyncMock())
    assert stored == [("marketing", "1", False)]
    assert done.marketing is False and done.needs_consent is False
