"""Auto-repeat expense rules (0051). Configuration only: a rule never records money by itself."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.infrastructure.db.repositories.finance_repository import FinanceRepository, _row


class ExpenseRuleRepository(FinanceRepository):
    async def list_rules(self, salon_id: str) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text("select * from salon_expense_rules where salon_id = :s order by active desc, created_at desc limit 100"),
            {"s": salon_id},
        )
        return [_row(r) for r in result.mappings().all()]

    async def count_active(self, salon_id: str) -> int:
        return int(await self.session.scalar(
            text("select count(*) from salon_expense_rules where salon_id = :s and active"), {"s": salon_id}
        ) or 0)

    async def replay_rule(self, salon_id: str, key: str, request_hash: str) -> dict[str, Any] | None:
        return await self._replay("salon_expense_rules", salon_id, key, request_hash)

    async def add_rule(self, values: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        existing = await self._replay("salon_expense_rules", values["salon_id"], values["key"], values["hash"])
        if existing:
            return existing, True
        result = await self.session.execute(
            text(
                """insert into salon_expense_rules(salon_id, title, category, amount_paise, payment_method, note,
                     frequency, start_date, created_by, idempotency_key, request_hash)
                   values(:salon_id, :title, :category, :amount_paise, :payment_method, :note,
                          :frequency, :start_date, :created_by, :key, :hash) returning *"""
            ),
            values,
        )
        return _row(result.mappings().one()), False

    async def stop_rule(self, salon_id: str, rule_id: str) -> dict[str, Any] | None:
        """Stops the rule once; stopping a stopped rule leaves it as it was."""

        result = await self.session.execute(
            text(
                """update salon_expense_rules set active = false, stopped_at = now()
                   where salon_id = :s and id = :i and active returning *"""
            ),
            {"s": salon_id, "i": rule_id},
        )
        row = result.mappings().first()
        return _row(row) if row else await self.get_rule(salon_id, rule_id)
