"""Backend-only support persistence, sharing existing payment idempotency."""

import hashlib
from uuid import uuid4

from sqlalchemy import text

from app.core.exceptions import NotFoundError, TooManyRequestsError
from app.infrastructure.db.repositories.payment_repository import PaymentRepository


class SupportRepository(PaymentRepository):
    async def throttle(self, principal: str, limit: int, seconds: int):
        bucket = hashlib.sha256(principal.encode()).hexdigest()
        row = (await self.session.execute(text("""
            insert into api_rate_limits(bucket_hash) values(:bucket)
            on conflict(bucket_hash) do update set
              attempts = case when api_rate_limits.window_start <= now() - make_interval(secs => :seconds)
                then 1 else api_rate_limits.attempts + 1 end,
              window_start = case when api_rate_limits.window_start <= now() - make_interval(secs => :seconds)
                then now() else api_rate_limits.window_start end
            returning attempts
        """), {"bucket": bucket, "seconds": seconds})).scalar_one()
        if row > limit:
            raise TooManyRequestsError("Too many requests. Please try again later.")

    async def enqueue_email(self, user_id, event_key, event_type, recipient, subject, body):
        await self.session.execute(text("""
            insert into email_events(user_id,event_key,event_type,recipient,subject,body)
            values (:user,:key,:type,:recipient,:subject,:body) on conflict(event_key) do nothing
        """), {"user": user_id,"key": event_key,"type": event_type,"recipient": recipient,"subject": subject,"body": body})

    async def create_ticket(self, actor, subject, body, salon_id):
        if salon_id is not None:
            found = (await self.session.execute(text("select id from salons where id=:id and is_active"), {"id": salon_id})).scalar_one_or_none()
            if found is None:
                raise NotFoundError("Salon not found")
        ticket_id = str(uuid4())
        row = (await self.session.execute(text("""
            insert into support_tickets(id,customer_id,salon_id,subject)
            values(:id,:user,:salon,:subject) returning id,customer_id,salon_id,subject,status,created_at,updated_at
        """), {"id":ticket_id,"user":actor.id,"salon":salon_id,"subject":subject})).mappings().one()
        await self.add_message(ticket_id, actor.id, body)
        return dict(row)

    async def add_message(self, ticket_id, actor_id, body):
        result = await self.session.execute(text("""
            insert into support_messages(ticket_id,author_id,body) values(:id,:actor,:body)
            returning id
        """), {"id":ticket_id,"actor":actor_id,"body":body})
        return str(result.scalar_one())

    async def get_ticket(self, ticket_id):
        row = (await self.session.execute(text("""
            select t.*, s.owner_id, p.email as customer_email from support_tickets t
            left join salons s on s.id=t.salon_id join profiles p on p.id=t.customer_id
            where t.id=:id for update of t
        """), {"id":ticket_id})).mappings().one_or_none()
        return dict(row) if row else None

    async def mark_replied(self, ticket_id):
        await self.session.execute(text("update support_tickets set status='replied',updated_at=now() where id=:id"), {"id":ticket_id})

    async def messages(self, ticket_id):
        result = await self.session.execute(text("select id,author_id,body,created_at from support_messages where ticket_id=:id order by created_at,id limit 200"), {"id":ticket_id})
        return [dict(r) for r in result.mappings()]

    async def email_status(self, event_id, actor_id):
        row = (await self.session.execute(text("select id,event_type,status,created_at,sent_at from email_events where id=:id and user_id=:actor"), {"id":event_id,"actor":actor_id})).mappings().one_or_none()
        return dict(row) if row else None
