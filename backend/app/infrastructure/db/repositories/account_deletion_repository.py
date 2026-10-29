"""SQL adapter for account-deletion challenges, ledger and erasure.

The statements live in mixins under account_deletion/; this module keeps the public
class and re-exports every name other modules import from here.
"""


from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.account_deletion_repository import AccountDeletionRepository
from app.infrastructure.db.repositories.account_deletion.bookings import _BookingMixin
from app.infrastructure.db.repositories.account_deletion.challenges import _ChallengeMixin
from app.infrastructure.db.repositories.account_deletion.constants import (  # noqa: F401  (re-exported for callers and tests)
    _CHALLENGE_COLUMNS,
    _OWNED_SALONS,
    ANONYMISED_NOTIFICATION_TITLE,
    CLOSURE_NOTICE_BASE,
    CLOSURE_NOTICE_MANUAL,
    CLOSURE_NOTICE_ONLINE,
    CLOSURE_REFUND_KEY,
    REMOVED_TEXT,
    SALON_CASCADE_TABLES,
    SALON_CLOSED_REASON,
    SALON_PROVIDER_REFERENCE_TABLES,
    SHELL_SALON_NAME,
)
from app.infrastructure.db.repositories.account_deletion.erasure import _ErasureMixin
from app.infrastructure.db.repositories.account_deletion.requests import _RequestMixin
from app.infrastructure.db.repositories.subscription_billing_repository import (
    SubscriptionBillingRepository,
)


class SQLAccountDeletionRepository(
    _ChallengeMixin,
    _RequestMixin,
    _BookingMixin,
    _ErasureMixin,
    AccountDeletionRepository,
):
    """Every method commits (or rolls back) its own unit of work."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _scrub_owner_business(self, params: dict[str, str], staff_ids: list[str]) -> list[str]:
        """Empty a closed salon down to an anonymous shell.

        Returns the staff profile ids that are safe to hard-delete (see below).
        """

        s = self.session
        owned = f"({_OWNED_SALONS})"
        # Re-run inside the erasure transaction: an order paid after the earlier step must not
        # leave a live renewal behind (idempotent; a late payment later hits 'blocked_closed').
        await SubscriptionBillingRepository(s).wind_down_salons(params["uid"])
        await self._scrub_owner_finance(params)
        # Staff logins that existed only for these salons are separate people whose
        # profile (name, email, phone, avatar) would otherwise be banned but kept for
        # ever. Guard: staff role, no staff row at a salon this owner does not own, never a
        # customer, never an owner. Anything failing the guard stays banned, not deleted.
        deletable_staff: list[str] = []
        if staff_ids:
            rows = await s.execute(
                text(f"""
                    select p.id from profiles p
                    where p.id = any(cast(:ids as uuid[])) and p.role = 'staff' and p.id <> :uid
                      and not exists (select 1 from staff o where o.profile_id = p.id
                                      and o.salon_id not in {owned})
                      and not exists (select 1 from bookings b where b.customer_id = p.id)
                      and not exists (select 1 from salons x where x.owner_id = p.id)
                """),
                {**params, "ids": staff_ids},
            )
            deletable_staff = [str(r[0]) for r in rows.all()]
        if staff_ids:
            await s.execute(
                text("delete from payment_idempotency_keys where actor_id = any(cast(:ids as uuid[]))"),
                {"ids": staff_ids},
            )

        # Cascade FKs to salons never fire (salons are kept): delete explicitly.
        for table in SALON_CASCADE_TABLES + SALON_PROVIDER_REFERENCE_TABLES:
            await s.execute(text(f"delete from {table} where salon_id in {owned}"), params)
        await s.execute(
            text(
                "delete from blocked_slots where staff_id in "
                f"(select id from staff where salon_id in {owned})"
            ),
            params,
        )
        await s.execute(
            text(f"""
                update subscription_events set error_message = null
                where error_message is not null and salon_subscription_id in (
                  select id from salon_subscriptions where salon_id in {owned})
            """),
            params,
        )
        await s.execute(
            text(f"update salon_reports set details = '' where salon_id in {owned} and details <> ''"),
            params,
        )

        await s.execute(
            text("""
                update salons
                set is_active = false, name = :shell, city = null,
                    address = null, lat = null, lng = null, qr_image_url = null,
                    rejection_reason = null, working_hours = '{}'::jsonb,
                    qr_token = encode(gen_random_bytes(16), 'hex')
                where owner_id = :uid
            """),
            {**params, "shell": SHELL_SALON_NAME},
        )
        await s.execute(
            text(f"update services set photo_url = null where salon_id in {owned}"),
            params,
        )
        # During the coordinated rollout the old columns may still exist. Keep
        # erasure complete until reviewed 0041 drops them; never recreate them.
        await self._scrub_legacy_descriptions(params)
        await s.execute(
            text(f"""
                update staff_services set specialization = null
                where specialization is not null
                  and staff_id in (select id from staff where salon_id in {owned})
            """),
            params,
        )
        await s.execute(
            text(f"""
                update staff
                set name = 'Former staff', photo_url = null, specialization = null,
                    experience = null, profile_id = null, is_active = false
                where salon_id in {owned}
            """),
            params,
        )

        # Bookings stay (other customers' history) but lose owner-written free text, and
        # walk-in people - who have no account and no other holder - lose their details.
        await s.execute(
            text(f"""
                update bookings
                set rejection_reason = case when status = 'rejected' then :removed end,
                    cancellation_reason_code = null, cancellation_reason_text = null,
                    cancellation_reason = case when cancellation_reason = :closed
                                               then cancellation_reason end
                where salon_id in {owned}
                  and (cancellation_reason_code is not null or cancellation_reason_text is not null
                       or rejection_reason is distinct from case when status = 'rejected' then :removed end
                       or cancellation_reason is distinct from case when cancellation_reason = :closed
                                                                    then cancellation_reason end)
            """),
            {**params, "removed": REMOVED_TEXT, "closed": SALON_CLOSED_REASON},
        )
        await s.execute(
            text(f"""
                update bookings
                set customer_name = 'Deleted customer', customer_phone = null, notes = null
                where salon_id in {owned} and customer_id is null
                  and (customer_name <> 'Deleted customer' or customer_phone is not null
                       or notes is not null)
            """),
            params,
        )
        await s.execute(
            text(f"""
                update booking_action_requests
                set decision_reason = case when decision = 'decline' then :removed end
                where decision_reason is not null
                  and decision_reason is distinct from case when decision = 'decline' then :removed end
                  and booking_id in (select id from bookings where salon_id in {owned})
            """),
            {**params, "removed": REMOVED_TEXT},
        )
        # An owner-typed refund reason is free text; the closure code is not.
        await s.execute(
            text(f"""
                update payment_refunds set reason = null
                where reason is not null and reason <> :closed
                  and booking_id in (select id from bookings where salon_id in {owned})
            """),
            {**params, "closed": SALON_CLOSED_REASON},
        )
        # Whoever recorded a cash receipt (owner or staff) is detached; amounts stay.
        await s.execute(
            text(f"""
                update booking_payments set recorded_by = null
                where salon_id in {owned} and recorded_by is not null
            """),
            params,
        )
        # Customers' and staff inbox items about this salon may name the owner, the staff
        # or the salon; the cancellation notices written by the closure step are exempt.
        await self._scrub_notifications(
            f"""user_id <> :uid
                and booking_id in (select id from bookings where salon_id in {owned})
                and coalesce(data ->> 'reason', '') <> '{SALON_CLOSED_REASON}'""",
            params,
        )
        return deletable_staff

    async def profile_exists(self, user_id: str) -> bool:
        result = await self.session.execute(
            text("select exists (select 1 from profiles where id = :uid)"), {"uid": user_id}
        )
        return bool(result.scalar_one())
