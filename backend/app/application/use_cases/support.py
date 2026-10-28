"""Authorized support requests and replies, saved atomically with business email."""

from typing import Any

from app.application.use_cases.idempotency import check_idempotency_key_length, fingerprint_of
from app.core.exceptions import ForbiddenError, NotFoundError
from app.domain.entities.profile import Profile, Role


class SupportUseCases:
    def __init__(self, repository: Any, settings: Any) -> None:
        self.repository = repository
        self.settings = settings

    async def begin(
        self, actor: Profile, scope: str, key: str | None, values: dict[str, Any]
    ) -> dict[str, Any] | None:
        check_idempotency_key_length(key, max_len=200, reject_blank=False)
        digest = fingerprint_of(values)
        return await self.repository.begin_idempotent(actor.id, scope, key, digest, 86400)

    async def create(
        self, actor: Profile, values: dict[str, Any], key: str | None
    ) -> dict[str, Any]:
        if actor.role not in {Role.customer, Role.owner}:
            raise ForbiddenError("Customer or owner access required")
        await self.repository.lock_active_author(actor.id)
        replay = await self.begin(actor, "support:create", key, values)
        if replay is not None:
            return replay
        await self.repository.throttle("support:" + actor.id, 5, 3600)
        ticket = await self.repository.create_ticket(actor, values["subject"], values["body"], values.get("salon_id"))
        tid = str(ticket["id"])
        if actor.email:
            await self.repository.enqueue_email(actor.id, "support_confirmation:" + tid, "support_confirmation",
                actor.email, "Support request received", "We received your support request. We will reply as soon as possible.")
        if self.settings.support_email:
            await self.repository.enqueue_email(actor.id, "support_admin:" + tid, "support_admin",
                self.settings.support_email, "New support request", "A new support request is available in the backend. Ticket: " + tid)
        result = {**ticket, "messages": []}
        await self.repository.finish_idempotent(actor.id, "support:create", key, 201, result)
        await self.repository.commit()
        return result

    async def read(self, actor: Profile, ticket_id: str) -> dict[str, Any]:
        ticket = await self.repository.get_ticket(ticket_id)
        if ticket and (ticket.get("retained_restricted") or ticket.get("privacy_restricted")) and actor.role != Role.super_admin:
            raise NotFoundError("Support ticket not found")
        if not ticket or not (str(ticket["customer_id"]) == actor.id or actor.role == Role.super_admin
            or (actor.role == Role.owner and str(ticket.get("owner_id")) == actor.id)):
            raise NotFoundError("Support ticket not found")
        return {**ticket, "messages": await self.repository.messages(ticket_id)}

    async def reply(
        self, actor: Profile, ticket_id: str, body: str, key: str | None
    ) -> dict[str, Any]:
        if actor.role not in {Role.owner, Role.super_admin}:
            raise ForbiddenError("Owner or admin access required")
        await self.repository.lock_active_author(actor.id)
        scope = "support:reply:" + ticket_id
        ticket = await self.read(actor, ticket_id)
        replay = await self.begin(actor, scope, key, {"body": body})
        if replay is not None:
            return replay
        if actor.role == Role.owner and str(ticket.get("owner_id")) != actor.id:
            raise NotFoundError("Support ticket not found")
        await self.repository.throttle("support:reply:" + actor.id, 30, 3600)
        message_id = await self.repository.add_message(ticket_id, actor.id, body)
        await self.repository.mark_replied(ticket_id)
        if ticket.get("customer_email") and not (ticket.get("retained_restricted") or ticket.get("privacy_restricted")):
            await self.repository.enqueue_email(str(ticket["customer_id"]), "support_reply:" + message_id,
                "support_reply", ticket["customer_email"], "Reply to your support request", body)
        result = await self.read(actor, ticket_id)
        # Keep persisted replay bodies within the public contract, excluding internal contacts.
        result = {k: v for k, v in result.items() if k not in {"customer_email", "owner_id"}}
        await self.repository.finish_idempotent(actor.id, scope, key, 200, result)
        await self.repository.commit()
        return result
