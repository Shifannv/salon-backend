"""Database erasure and the per-area scrub helpers."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.account_deletion.privacy import (
    authored_quote_pattern,
    personal_text_pattern,
    quoted_text_pattern,
)
from app.infrastructure.db.repositories.account_deletion.constants import (
    _OWNED_SALONS,
    ANONYMISED_NOTIFICATION_TITLE,
    REMOVED_TEXT,
    SALON_CLOSED_REASON,
)


class _ErasureMixin:
    session: AsyncSession

    # ---------------------------------------------------------------- erasure
    async def erase_database(
        self, user_id: str, role: str, staff_profile_ids: list[str] | None = None
    ) -> None:
        s = self.session
        try:
            await s.execute(text("select set_config('app.account_erasure', 'on', true)"))
            params = {"uid": user_id}
            await s.execute(text("select id from profiles where id=:uid for update"), params)
            if role == "owner":
                # Creation takes FOR SHARE on the same salon row before validating it.
                await s.execute(text("select id from salons where owner_id=:uid order by id for update"), params)
            await self._scrub_booking_audits(params)
            await self._scrub_post_baseline_footprint(params)
            await self._scrub_user_footprint(params)
            deletable_staff: list[str] = []
            if role == "owner":
                deletable_staff = await self._scrub_owner_business(params, staff_profile_ids or [])
            await s.execute(text("select erase_profile_references(:uid)"), params)
            await s.execute(text("delete from profiles where id = :uid"), params)
            for staff_id in deletable_staff:
                await s.execute(text("select erase_profile_references(:uid)"), {"uid": staff_id})
                await s.execute(text("delete from profiles where id = :uid"), {"uid": staff_id})
            await s.commit()
        except BaseException:
            await s.rollback()
            raise

    async def _scrub_booking_audits(self, params: dict[str, str]) -> None:
        """Fail closed during rollout if new audit tables lack their privacy migration."""
        state = (await self.session.execute(text("""
            select to_regclass('public.booking_customer_changes') is not null
                     or to_regclass('public.booking_finance_commands') is not null as has_audits,
                   to_regprocedure('public.erase_booking_audit_personal_data(uuid)') is not null as can_scrub
        """))).mappings().one()
        if state["has_audits"]:
            if not state["can_scrub"]:
                raise RuntimeError("booking_audit_privacy_migration_required")
            await self.session.execute(text("select public.erase_booking_audit_personal_data(:uid)"), params)

    async def _scrub_post_baseline_footprint(self, params: dict[str, str]) -> None:
        """Clear later support copies/diagnostics while retaining financial rows."""
        present = set((await self.session.execute(text("""
            select tablename from pg_catalog.pg_tables where schemaname='public'
              and tablename in ('payment_anomalies','payment_provider_account_audit','subscription_billing_records','support_tickets')
        """))).scalars().all())
        if not present:
            return
        if "support_tickets" in present or "subscription_billing_records" in present:
            ready = (await self.session.execute(text("""
                select to_regclass('public.support_erasure_events') is not null
                  and to_regprocedure('public.erase_subscription_benefit_text(uuid)') is not null
            """))).scalar_one()
            if not ready:
                raise RuntimeError("support_billing_privacy_migration_required")
        profile_row = (await self.session.execute(text("""
            select id,role::text as role,full_name,email,phone,avatar_url from profiles where id=:uid
        """), params)).mappings().one_or_none()
        if profile_row is None:
            return
        profile = dict(profile_row)
        diagnostics = {**params, "pattern": personal_text_pattern(profile), "redacted": "█"}
        if "support_tickets" in present:
            await self._scrub_support_footprint(params, profile)
        bookings = """select b.id from public.bookings b join public.salons s on s.id=b.salon_id
                      where b.customer_id=:uid or s.owner_id=:uid"""
        if "payment_anomalies" in present:
            await self.session.execute(text(f"""
                update payment_anomalies set detail=regexp_replace(detail,:pattern,:redacted,'gi')
                  where detail ~* :pattern and (
                  resolved_by=:uid or salon_id in ({_OWNED_SALONS}) or booking_id in ({bookings})
                  or payment_id in (select id from booking_payments where booking_id in ({bookings})))
            """), diagnostics)
        if "payment_provider_account_audit" in present:
            await self.session.execute(text(f"""
                update payment_provider_account_audit set detail=regexp_replace(detail,:pattern,:redacted,'gi')
                  where detail ~* :pattern
                  and (actor_id=:uid or salon_id in ({_OWNED_SALONS}))
            """), diagnostics)
        if "subscription_billing_records" in present:
            if profile["role"] == "owner":
                await self.session.execute(text("select public.erase_subscription_benefit_text(:uid)"), params)
            await self.session.execute(text(f"""
                update subscription_billing_records set failure_code=regexp_replace(failure_code,:pattern,:redacted,'gi')
                  where failure_code ~* :pattern
                  and (created_by=:uid or updated_by=:uid or salon_id in ({_OWNED_SALONS}))
            """), diagnostics)

    async def _scrub_support_footprint(self, params: dict[str, str], profile: dict) -> None:
        """Selectively anonymize known personal text and retain versioned case evidence."""
        # Reply use cases lock this same ticket before inserting messages/cached replies.
        tickets = (await self.session.execute(text("""
            select t.id from support_tickets t where t.customer_id=:uid
              or t.salon_id in (select id from salons where owner_id=:uid)
              or exists(select 1 from support_messages m where m.ticket_id=t.id and m.author_id=:uid)
            order by t.id for update of t
        """), params)).scalars().all()
        if not tickets:
            return
        values = {**params, "tickets": tickets, "pattern": personal_text_pattern(profile),
                  "owner": profile["role"] == "owner", "role": profile["role"], "removed": REMOVED_TEXT,
                  "redacted": "█"}
        await self.session.execute(text("""
            delete from payment_idempotency_keys where scope in (
              select 'support:reply:' || id::text from support_tickets where id=any(cast(:tickets as uuid[])))
              or (scope='support:create' and response_body->>'id' in (
                select id::text from support_tickets where id=any(cast(:tickets as uuid[]))))
        """), values)
        # Retained support history is restricted: cancel its local outbound and
        # delivery copies, including ambiguous quotes, without deleting case evidence.
        await self.session.execute(text("""
            delete from email_events where event_key in (
              select 'support_reply:'||id::text from support_messages where ticket_id=any(cast(:tickets as uuid[]))
              union all select 'support_confirmation:'||id::text from support_tickets where id=any(cast(:tickets as uuid[]))
              union all select 'support_admin:'||id::text from support_tickets where id=any(cast(:tickets as uuid[])))
        """), values)
        await self._redact_support_copies(values)
        # Capture authored text before overwriting it. Read bounded keyset pages
        # so a long support history never becomes one unbounded regex or payload.
        batch: list[str] = []
        size = 0
        after = None
        while True:
            originals = (await self.session.execute(text("""
                select id,body from support_messages where author_id=:uid
                  and ticket_id=any(cast(:tickets as uuid[])) and body<>:removed
                  and (cast(:after as uuid) is null or id>cast(:after as uuid))
                order by id limit 20
            """), {**values, "after": after})).mappings().all()
            if not originals:
                break
            for original in originals:
                body = original["body"]
                # Acknowledgements, punctuation and bare amounts are not reliable
                # evidence of a personal-data quote. Preserve ambiguous matches.
                if len(body.strip()) < 16 or not any(character.isalpha() for character in body):
                    continue
                literal = quoted_text_pattern(body)
                if batch and size + len(literal) > 16000:
                    await self._redact_support_copies({**values, "pattern": authored_quote_pattern(batch), "redacted": r"\1█"})
                    batch, size = [], 0
                batch.append(literal)
                size += len(literal) + 1
            after = originals[-1]["id"]
        if batch:
            await self._redact_support_copies({**values, "pattern": authored_quote_pattern(batch), "redacted": r"\1█"})
        await self.session.execute(text("""
            update support_messages set body=:removed where author_id=:uid
              and ticket_id=any(cast(:tickets as uuid[])) and body<>:removed
        """), values)
        await self.session.execute(text("""
            update support_tickets set retained_restricted=true,erasure_policy_version='support-erasure-v1',
                erasure_retention_reason='operational_review_pending'
              where id=any(cast(:tickets as uuid[])) and :owner
        """), values)
        await self.session.execute(text("""
            insert into support_erasure_events(ticket_id,actor_pseudonym,actor_role,policy_version,retention_reason)
              select id,public.booking_audit_identifier_hash('support-erasure',id::text||':'||cast(:uid as text)),
                :role,'support-erasure-v1','operational_review_pending'
              from support_tickets where id=any(cast(:tickets as uuid[])) and retained_restricted
              on conflict(ticket_id,actor_pseudonym,policy_version) do nothing
        """), values)
        await self.session.execute(text("""
            update support_tickets set customer_id=null
              where customer_id=:uid and retained_restricted and id=any(cast(:tickets as uuid[]))
        """), values)

    async def _redact_support_copies(self, values: dict) -> None:
        """Redact identified fragments while preserving surrounding case evidence."""
        await self.session.execute(text("""
            update support_messages set body=regexp_replace(body,:pattern,:redacted,'gi')
              where ticket_id=any(cast(:tickets as uuid[])) and author_id is distinct from :uid and body ~* :pattern
        """), values)
        await self.session.execute(text("""
            update support_tickets set subject=regexp_replace(subject,:pattern,:redacted,'gi')
              where id=any(cast(:tickets as uuid[])) and subject ~* :pattern
        """), values)

    async def _scrub_notifications(self, predicate: str, params: dict[str, Any]) -> None:
        """Anonymise other people's notifications that name a deleted person.

        Delivery/outbox error text can echo provider payloads, so it goes too. The
        predicate must not depend on the columns being rewritten.
        """

        s = self.session
        ids = f"select id from notifications where {predicate}"
        await s.execute(
            text(f"update notification_deliveries set error = null where notification_id in ({ids})"),
            params,
        )
        await s.execute(
            text(f"update notification_outbox set last_error = null where notification_id in ({ids})"),
            params,
        )
        await s.execute(
            text(f"""
                update notifications
                set title = :title, body = null, data = null
                where {predicate}
                  and (title is distinct from :title or body is not null or data is not null)
            """),
            {**params, "title": ANONYMISED_NOTIFICATION_TITLE},
        )

    async def _scrub_legacy_descriptions(self, params: dict[str, str]) -> None:
        """Erase owner metadata during rollout, without requiring removed columns."""
        s = self.session
        legacy = await s.execute(text("""
            select table_name from information_schema.columns
            where table_schema = 'public' and column_name = 'description'
              and table_name in ('salons', 'services')
        """))
        for table in legacy.scalars().all():
            if table == "salons":
                await s.execute(text("update salons set description = null where owner_id = :uid"), params)
            elif table == "services":
                await s.execute(text(f"update services set description = null where salon_id in ({_OWNED_SALONS})"), params)

    async def _scrub_user_footprint(self, params: dict[str, str]) -> None:
        """Everything that points at the person being erased, whatever their role."""

        s = self.session
        await s.execute(text("delete from notifications where user_id = :uid"), params)
        await s.execute(text("delete from device_tokens where user_id = :uid"), params)
        # Other people's inbox items that name this customer (owner/staff "X booked ...").
        await self._scrub_notifications(
            "user_id <> :uid and booking_id in (select id from bookings where customer_id = :uid)",
            params,
        )
        await s.execute(text("delete from salon_reports where reporter_id = :uid"), params)
        await s.execute(
            text("""
                update booking_action_requests
                set reason = case when requested_by = :uid then null else reason end,
                    decision_reason = case when decision = 'decline' then :removed end
                where requested_by = :uid
                   or booking_id in (select id from bookings where customer_id = :uid)
            """),
            {**params, "removed": REMOVED_TEXT},
        )
        await s.execute(
            text("""
                update bookings
                set customer_name = 'Deleted customer', customer_phone = null, notes = null,
                    cancellation_reason_code = null, cancellation_reason_text = null,
                    rejection_reason = case when status = 'rejected' then :removed end,
                    cancellation_reason = case when cancellation_reason = :closed
                                               then cancellation_reason end
                where customer_id = :uid
            """),
            {**params, "removed": REMOVED_TEXT, "closed": SALON_CLOSED_REASON},
        )
        # Financial rows are RETAINED (amounts, ids, provider references); only the
        # people on them are detached.
        await s.execute(text("update booking_payments set payer_id = null where payer_id = :uid"), params)
        await s.execute(
            text("update booking_payments set recorded_by = null where recorded_by = :uid"), params
        )
        await s.execute(text("delete from payment_idempotency_keys where actor_id = :uid"), params)
