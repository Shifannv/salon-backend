"""Owner finance cash book: daily ledger, expenses, cash adjustments and day close.

Owner only (staff and customers are refused), plan-gated on ``daily_ledger`` (a salon on its free
trial counts as Growth). The server computes every figure; a request can never supply a total.
Every write takes the salon lock, so two taps or two devices cannot race, and every write needs an
``Idempotency-Key``: the same key with the same body replays the stored record, a different body is
refused.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from app.application.use_cases.idempotency import fingerprint_of, require_idempotency_key
from app.core.exceptions import (
    AppError,
    DayInFutureError,
    DifferenceReasonRequiredError,
    EntitlementRequiredError,
    ExpenseAlreadyReversedError,
    ForbiddenError,
    NotFoundError,
    OpeningCashRequiredError,
    RuleOccurrenceError,
    SalonApprovalRequiredError,
    ValidationError,
)
from app.domain.entities.profile import Profile, Role
from app.domain.services.feature_access import (
    DAILY_LEDGER,
    EXPENSES,
    FINANCE_PAGE,
    STAFF_EARNINGS,
    is_enabled,
)
from app.domain.services.finance_ledger import (
    MAX_RANGE_DAYS,
    expected_closing_cash,
    finance_allowed,
    local_day_bounds,
    month_bounds,
    reason_is_written,
    rule_applies_on,
    today_in,
)

LEDGER_FEATURE = DAILY_LEDGER
FINANCE_TABS = frozenset({DAILY_LEDGER, EXPENSES, STAFF_EARNINGS})
MAX_KEY = 200
FUTURE_TOLERANCE = timedelta(minutes=5)


def _paise(figures: dict[str, Any], key: str) -> int:
    return int(figures[key])


class FinanceUseCases:
    def __init__(self, repository: Any, clock: Callable[[], datetime] | None = None) -> None:
        self.repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))

    # ------------------------------------------------------------------ access
    async def _salon(
        self, actor: Profile, *, write: bool = False, feature: str = LEDGER_FEATURE
    ) -> dict[str, Any]:
        """The owner's approved salon. Reading is always allowed to the owner, so past records stay
        visible after a trial or plan ends; any write needs the plan (or trial) to still be active.

        ``feature`` is the super-admin switch this call sits behind. A feature the salon's plan (or a
        salon override) locks is refused for reads and writes alike; a salon with no live plan or trial
        belongs to no audience, so it keeps the read-only rule above."""

        if actor.role is not Role.owner:
            raise ForbiddenError("Salon owner access required")
        salon = await self.repository.owner_salon(actor.id)
        if not salon or not salon["is_active"]:
            raise ForbiddenError("Active salon workspace required")
        if not salon["profile_completed"] or salon["approval_status"] != "approved":
            raise SalonApprovalRequiredError("Super admin approval is required for daily business")
        now = self._clock()
        access = await self.repository.plan_access(str(salon["id"]), now)
        resolved = access.pop("feature_access", None)
        if resolved is None:
            can_write = finance_allowed(now=now, **access)
        else:
            self._require_unlocked(resolved, feature)
            if feature in FINANCE_TABS:
                self._require_unlocked(resolved, FINANCE_PAGE)
            can_write = is_enabled(resolved, feature)
        if write and not can_write:
            raise EntitlementRequiredError(
                "Your trial or plan has ended: your finance records stay here, read-only"
            )
        return {**salon, "can_write": can_write}

    @staticmethod
    def _require_unlocked(resolved: dict[str, Any], feature: str) -> None:
        state = resolved.get(feature, {})
        if state.get("enabled") is not True and state.get("source") != "none":
            raise EntitlementRequiredError("This feature is not included in your plan")

    def _not_future(self, moment: datetime) -> None:
        if moment.tzinfo is None:
            raise ValidationError("Date and time must include a time zone")
        if moment > self._clock() + FUTURE_TOLERANCE:
            raise ValidationError("A record cannot be dated in the future")

    # ------------------------------------------------------------------ ledger
    async def _figures(self, salon_id: str, timezone: str, local_date: date) -> dict[str, Any]:
        start, end = local_day_bounds(local_date, timezone)
        return await self.repository.day_figures(salon_id, start, end)

    @staticmethod
    def _cash_expected(opening: int, figures: dict[str, Any]) -> int:
        return expected_closing_cash(
            opening_cash=opening,
            cash_collected=_paise(figures, "cash_collected"),
            cash_refunds=_paise(figures, "cash_refunds"),
            cash_expenses=_paise(figures, "cash_expenses"),
            adjustments_in=_paise(figures, "adjustments_in"),
            adjustments_out=_paise(figures, "adjustments_out"),
        )

    @staticmethod
    def _close_view(close: dict[str, Any] | None, expected_now: int) -> dict[str, Any] | None:
        if close is None:
            return None
        return {
            "changed_since_close": int(close["expected_cash_paise"]) != expected_now,
            "revision": close["revision"],
            "opening_cash_paise": close["opening_cash_paise"],
            "expected_cash_paise": close["expected_cash_paise"],
            "actual_cash_paise": close["actual_cash_paise"],
            "difference_paise": close["difference_paise"],
            "difference_reason": close["difference_reason"],
            "closed_at": close["created_at"],
        }

    async def daily_ledger(self, actor: Profile, local_date: date) -> dict[str, Any]:
        salon = await self._salon(actor)
        salon_id, timezone = str(salon["id"]), salon["timezone"]
        figures = await self._figures(salon_id, timezone, local_date)
        opening, source = await self.repository.opening_cash(salon_id, local_date, timezone)
        close = await self.repository.latest_close(salon_id, local_date)
        if close is not None and source != "previous_close":
            opening, source = int(close["opening_cash_paise"]), "entered_at_close"
        return {
            "date": local_date,
            "timezone": timezone,
            "status": "closed" if close else "open",
            "gross_completed_sales_paise": _paise(figures, "sales"),
            "cash_collected_paise": _paise(figures, "cash_collected"),
            "non_cash_received_paise": _paise(figures, "non_cash_received"),
            "outstanding_due_paise": await self.repository.outstanding_due(salon_id),
            "refunds": {
                "cash_paise": _paise(figures, "cash_refunds"),
                "non_cash_paise": _paise(figures, "non_cash_refunds"),
            },
            "expenses": {
                "cash_paise": _paise(figures, "cash_expenses"),
                "non_cash_paise": _paise(figures, "non_cash_expenses"),
            },
            # Summed here so no client ever has to add two money figures together.
            "expenses_total_paise": _paise(figures, "cash_expenses") + _paise(figures, "non_cash_expenses"),
            "cash_adjustments": {
                "in_paise": _paise(figures, "adjustments_in"),
                "out_paise": _paise(figures, "adjustments_out"),
            },
            "opening_cash_paise": opening,
            "opening_cash_source": source,
            "expected_closing_cash_paise": self._cash_expected(opening, figures),
            "close": self._close_view(close, self._cash_expected(opening, figures)),
            "needs_review": bool(figures["paid_without_receipt"] or figures["refund_pending"]),
            # False once the trial or plan has ended: the records stay readable, nothing can be added.
            "can_write": salon["can_write"],
        }

    async def ledger_range(self, actor: Profile, first: date, last: date) -> dict[str, Any]:
        if last < first:
            raise ValidationError("'to' must not be before 'from'")
        if (last - first).days + 1 > MAX_RANGE_DAYS:
            raise ValidationError(f"A range can cover at most {MAX_RANGE_DAYS} days")
        salon = await self._salon(actor)
        salon_id, timezone = str(salon["id"]), salon["timezone"]
        closes = await self.repository.closes_between(salon_id, first, last)
        days: list[dict[str, Any]] = []
        totals = {"gross_completed_sales_paise": 0, "cash_collected_paise": 0,
                  "non_cash_received_paise": 0, "expenses_paise": 0}
        review = False
        cursor = first
        while cursor <= last:
            figures = await self._figures(salon_id, timezone, cursor)
            day = {
                "date": cursor,
                "gross_completed_sales_paise": _paise(figures, "sales"),
                "cash_collected_paise": _paise(figures, "cash_collected"),
                "non_cash_received_paise": _paise(figures, "non_cash_received"),
                "expenses_paise": _paise(figures, "cash_expenses") + _paise(figures, "non_cash_expenses"),
                "status": "closed" if cursor in closes else "open",
            }
            for name in totals:
                totals[name] += day[name]
            review = review or bool(figures["paid_without_receipt"] or figures["refund_pending"])
            days.append(day)
            cursor += timedelta(days=1)
        return {"days": days, "totals": totals, "needs_review": review}

    # ------------------------------------------------------------------ day close
    async def close_day(
        self, actor: Profile, local_date: date, *, actual_cash_paise: int,
        difference_reason: str | None, opening_cash_paise: int | None, idempotency_key: str | None,
    ) -> dict[str, Any]:
        key = require_idempotency_key(idempotency_key, max_len=MAX_KEY)
        salon = await self._salon(actor, write=True)
        salon_id, timezone = str(salon["id"]), salon["timezone"]
        if local_date > today_in(timezone, self._clock()):
            raise DayInFutureError("A day cannot be closed before it has started")
        reason = (difference_reason or "").strip() or None
        digest = fingerprint_of({"op": "close", "date": local_date.isoformat(), "actual": actual_cash_paise,
                                 "reason": reason, "opening": opening_cash_paise})
        await self.repository.lock_salon(salon_id)
        # A retry must return the stored close even though the cash book has moved on since: look
        # for it before recomputing or validating anything against today's figures.
        if await self.repository.stored_close(salon_id, key, digest) is not None:
            return await self.daily_ledger(actor, local_date)
        opening, source = await self.repository.opening_cash(salon_id, local_date, timezone)
        previous = await self.repository.latest_close(salon_id, local_date)
        if source == "previous_close":
            if opening_cash_paise is not None:
                raise ValidationError("Opening cash is carried forward from the previous close")
        else:
            # First ledger day, or the day before was never closed: the owner states the drawer
            # cash at the start of the day. It is never assumed to be zero or carried silently.
            if opening_cash_paise is not None:
                opening = opening_cash_paise
            elif previous is not None:
                opening = int(previous["opening_cash_paise"])  # a re-count keeps the confirmed opening
            else:
                raise OpeningCashRequiredError("Confirm the cash in the drawer when this day began")
        figures = await self._figures(salon_id, timezone, local_date)
        expected = self._cash_expected(opening, figures)
        if actual_cash_paise != expected and not reason_is_written(reason):
            raise DifferenceReasonRequiredError("Counted cash differs from expected: write the reason")
        await self.repository.add_close({
            "salon_id": salon_id, "local_date": local_date,
            "revision": (previous["revision"] + 1) if previous else 1,
            "opening_cash_paise": opening, "expected_cash_paise": expected,
            "actual_cash_paise": actual_cash_paise, "difference_reason": reason,
            "created_by": actor.id, "key": key, "hash": digest,
        })
        await self.repository.commit()
        return await self.daily_ledger(actor, local_date)

    # ------------------------------------------------------------------ adjustments
    async def add_adjustment(
        self, actor: Profile, *, direction: str, amount_paise: int, reason: str,
        occurred_at: datetime, idempotency_key: str | None,
    ) -> dict[str, Any]:
        key = require_idempotency_key(idempotency_key, max_len=MAX_KEY)
        salon = await self._salon(actor, write=True)
        self._not_future(occurred_at)
        reason = reason.strip()
        digest = fingerprint_of({"op": "adjust", "direction": direction, "amount": amount_paise,
                                 "reason": reason, "at": occurred_at.isoformat()})
        await self.repository.lock_salon(str(salon["id"]))
        row, replayed = await self.repository.add_adjustment({
            "salon_id": str(salon["id"]), "direction": direction, "amount_paise": amount_paise,
            "reason": reason, "occurred_at": occurred_at, "reverses_id": None,
            "created_by": actor.id, "key": key, "hash": digest,
        })
        await self.repository.commit()
        return {**row, "replayed": replayed}

    # ------------------------------------------------------------------ expenses
    def _expense_values(
        self, actor: Profile, salon_id: str, *, key: str, title: str, category: str, amount_paise: int,
        payment_method: str, occurred_at: datetime, note: str | None,
    ) -> dict[str, Any]:
        self._not_future(occurred_at)
        title = title.strip()
        note = (note or "").strip() or None
        digest = fingerprint_of({"op": "expense", "title": title, "category": category, "amount": amount_paise,
                                 "method": payment_method, "at": occurred_at.astimezone(UTC).isoformat(),
                                 "note": note})
        return {
            "salon_id": salon_id, "entry_type": "expense", "reverses_id": None, "title": title,
            "category": category, "amount_paise": amount_paise, "payment_method": payment_method,
            "occurred_at": occurred_at, "note": note, "created_by": actor.id, "key": key, "hash": digest,
        }

    async def add_expense(
        self, actor: Profile, *, title: str, category: str, amount_paise: int, payment_method: str,
        occurred_at: datetime, note: str | None, idempotency_key: str | None,
    ) -> dict[str, Any]:
        key = require_idempotency_key(idempotency_key, max_len=MAX_KEY)
        if key.startswith("rule:"):
            raise RuleOccurrenceError("Repeating-expense days are recorded by the app, not one by one")
        salon = await self._salon(actor, write=True, feature=EXPENSES)
        values = self._expense_values(
            actor, str(salon["id"]), key=key, title=title, category=category, amount_paise=amount_paise,
            payment_method=payment_method, occurred_at=occurred_at, note=note,
        )
        await self.repository.lock_salon(str(salon["id"]))
        row, replayed = await self.repository.add_expense(values)
        await self.repository.commit()
        reversed_since = replayed and await self.repository.reversal_of(str(row["id"])) is not None
        return {**row, "reversed": reversed_since, "replayed": replayed}

    async def _check_rule_occurrence(self, salon: dict[str, Any], client_id: str, item: dict[str, Any]) -> None:
        """An id ``rule:<rule>:<date>`` may only record a day that rule really covers, with the rule's own
        details. A phone with an out-of-date copy cannot add days after the owner stopped it, or days
        the rule does not repeat on, so the same logical day can never be recorded under two ids."""

        try:
            _, rule_part, day_part = client_id.split(":")
            rule_id, day = str(UUID(rule_part)), date.fromisoformat(day_part)
        except ValueError as error:
            raise RuleOccurrenceError("Not a valid repeating-expense day") from error
        zone = ZoneInfo(salon["timezone"])
        rule = await self.repository.get_rule(str(salon["id"]), rule_id)
        if rule is None:
            raise RuleOccurrenceError("That repeating expense does not exist")
        stopped_on = rule["stopped_at"].astimezone(zone).date() if rule["stopped_at"] else None
        same = (
            item["occurred_at"].astimezone(zone).date() == day
            and item["title"].strip() == rule["title"] and item["category"] == rule["category"]
            and item["amount_paise"] == rule["amount_paise"] and item["payment_method"] == rule["payment_method"]
            and ((item.get("note") or "").strip() or None) == rule["note"]
        )
        if not same or not rule_applies_on(rule["frequency"], rule["start_date"], day) or (
            stopped_on is not None and day > stopped_on
        ):
            raise RuleOccurrenceError("That day is not part of this repeating expense")

    async def add_expenses_batch(self, actor: Profile, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Record up to 50 expenses in one call. Each item stands alone: a refused item never blocks
        the others, and sending the same ``client_id`` again replays the stored record."""

        salon = await self._salon(actor, write=True, feature=EXPENSES)
        salon_id = str(salon["id"])
        await self.repository.lock_salon(salon_id)
        results: list[dict[str, Any]] = []
        for item in items:
            client_id = item["client_id"]
            try:
                if client_id.startswith("rule:"):
                    await self._check_rule_occurrence(salon, client_id, item)
                values = self._expense_values(
                    actor, salon_id, key=client_id, title=item["title"], category=item["category"],
                    amount_paise=item["amount_paise"], payment_method=item["payment_method"],
                    occurred_at=item["occurred_at"], note=item.get("note"),
                )
                row, replayed = await self.repository.add_expense_isolated(values)
            except AppError as error:
                results.append({"client_id": client_id, "status": "rejected", "code": error.code, "expense": None})
                continue
            reversed_since = replayed and await self.repository.reversal_of(str(row["id"])) is not None
            results.append({
                "client_id": client_id, "status": "replayed" if replayed else "created", "code": None,
                "expense": {**row, "reversed": reversed_since, "replayed": replayed},
            })
        await self.repository.commit()
        return results

    async def expense_changes(self, actor: Profile, *, after: int, limit: int) -> dict[str, Any]:
        salon = await self._salon(actor, feature=EXPENSES)
        rows, has_more = await self.repository.expense_changes(str(salon["id"]), after, limit)
        return {
            "expenses": rows,
            "next_cursor": int(rows[-1]["seq"]) if rows else after,
            "has_more": has_more,
        }

    async def expense_summary(self, actor: Profile, month: str) -> dict[str, Any]:
        salon = await self._salon(actor, feature=EXPENSES)
        timezone = salon["timezone"]
        try:
            start, end = month_bounds(month, timezone)
        except ValueError as error:
            raise ValidationError("month must look like 2026-10") from error
        rows = await self.repository.expense_days(str(salon["id"]), start, end, timezone)
        days = [
            {"date": row["day"], "cash_paise": int(row["cash"]), "non_cash_paise": int(row["non_cash"]),
             "total_paise": int(row["cash"]) + int(row["non_cash"]), "count": int(row["live"])}
            for row in rows
        ]
        totals = {key: sum(day[key] for day in days) for key in ("cash_paise", "non_cash_paise", "total_paise", "count")}
        return {"month": month, "timezone": timezone, "days": days, "totals": totals}

    async def reverse_expense(
        self, actor: Profile, expense_id: str, *, idempotency_key: str | None
    ) -> dict[str, Any]:
        key = require_idempotency_key(idempotency_key, max_len=MAX_KEY)
        salon = await self._salon(actor, write=True, feature=EXPENSES)
        salon_id = str(salon["id"])
        await self.repository.lock_salon(salon_id)
        # Read the original only once the lock is held, so an erasure running at the same time
        # cannot change it between the read and the mirror entry.
        original = await self.repository.get_expense(salon_id, expense_id)
        if original is None:
            raise NotFoundError("Expense not found")
        if original["entry_type"] != "expense":
            raise ValidationError("Only an expense can be reversed")
        digest = fingerprint_of({"op": "reverse", "id": str(original["id"])})
        existing = await self.repository.reversal_of(str(original["id"]))
        if existing is not None:
            if existing["idempotency_key"] == key and existing["request_hash"] == digest:
                return {**existing, "reversed": False, "replayed": True}
            raise ExpenseAlreadyReversedError("This expense has already been reversed")
        row, replayed = await self.repository.add_expense({
            "salon_id": salon_id, "entry_type": "reversal", "reverses_id": str(original["id"]),
            "title": original["title"], "category": original["category"],
            "amount_paise": original["amount_paise"], "payment_method": original["payment_method"],
            # The cancellation lands on the day of the expense it cancels, never on today.
            "occurred_at": original["occurred_at"],
            "note": None, "created_by": actor.id, "key": key, "hash": digest,
        })
        await self.repository.commit()
        return {**row, "reversed": False, "replayed": replayed}

    async def list_expenses(
        self, actor: Profile, *, first: date | None, last: date | None, limit: int, offset: int
    ) -> dict[str, Any]:
        salon = await self._salon(actor, feature=EXPENSES)
        salon_id, timezone = str(salon["id"]), salon["timezone"]
        start = local_day_bounds(first, timezone)[0] if first else None
        end = local_day_bounds(last, timezone)[1] if last else None
        rows = await self.repository.list_expenses(salon_id, start, end, limit, offset)
        return {"expenses": rows, "limit": limit, "offset": offset}
