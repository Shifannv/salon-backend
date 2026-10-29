"""Auto-repeat expense rules: the owner sets "rent every month" once and every phone sees it.

A rule is configuration. The owner's phone records each due day as an ordinary expense through the
batch endpoint with the client id ``rule:<id>:<date>``, so a day can never be recorded twice and a
cancelled occurrence is never brought back. A rule is never edited: stop it and create another.
Owner only; creating and stopping need an active plan or trial, reading never does.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.application.use_cases.finance import MAX_KEY, FinanceUseCases
from app.application.use_cases.idempotency import fingerprint_of, require_idempotency_key
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities.profile import Profile
from app.domain.services.finance_ledger import today_in

MAX_ACTIVE_RULES = 30
MAX_START_AHEAD = timedelta(days=366)
MAX_START_BEHIND = timedelta(days=31)


class ExpenseRuleUseCases(FinanceUseCases):
    async def list_rules(self, actor: Profile) -> dict[str, Any]:
        salon = await self._salon(actor)
        rules = await self.repository.list_rules(str(salon["id"]))
        return {"rules": rules, "can_write": salon["can_write"]}

    async def add_rule(
        self, actor: Profile, *, title: str, category: str, amount_paise: int, payment_method: str,
        note: str | None, frequency: str, start_date: date, idempotency_key: str | None,
    ) -> dict[str, Any]:
        key = require_idempotency_key(idempotency_key, max_len=MAX_KEY)
        salon = await self._salon(actor, write=True)
        salon_id = str(salon["id"])
        today = today_in(salon["timezone"], self._clock())
        title = title.strip()
        note = (note or "").strip() or None
        digest = fingerprint_of({
            "op": "expense_rule", "title": title, "category": category, "amount": amount_paise,
            "method": payment_method, "note": note, "frequency": frequency, "start": start_date.isoformat(),
        })
        await self.repository.lock_salon(salon_id)
        values = {
            "salon_id": salon_id, "title": title, "category": category, "amount_paise": amount_paise,
            "payment_method": payment_method, "note": note, "frequency": frequency, "start_date": start_date,
            "created_by": actor.id, "key": key, "hash": digest,
        }
        # A replay is answered before the cap, so a retried request is never refused for being "too many".
        existing = await self.repository.replay_rule(salon_id, key, digest)
        if existing is None:
            # Checked only for a new rule: a retry of one already made is never refused because a day passed.
            if start_date > today + MAX_START_AHEAD:
                raise ValidationError("A repeat cannot start more than a year ahead")
            if start_date < today - MAX_START_BEHIND:
                raise ValidationError("A repeat cannot start more than 31 days in the past")
            if await self.repository.count_active(salon_id) >= MAX_ACTIVE_RULES:
                raise ValidationError(f"At most {MAX_ACTIVE_RULES} repeating expenses can be active; stop one first")
        row, replayed = await self.repository.add_rule(values)
        await self.repository.commit()
        return {**row, "replayed": replayed}

    async def stop_rule(self, actor: Profile, rule_id: str) -> dict[str, Any]:
        salon = await self._salon(actor, write=True)
        salon_id = str(salon["id"])
        await self.repository.lock_salon(salon_id)
        row = await self.repository.stop_rule(salon_id, rule_id)
        if row is None:
            raise NotFoundError("Repeating expense not found")
        await self.repository.commit()
        return {**row, "replayed": False}
