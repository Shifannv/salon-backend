"""Owner earnings and settlement-account operations for ``BookingPaymentUseCases``."""

from decimal import Decimal
from typing import Any

from app.application.ports.payment_gateway import (
    SettlementAccountRequest,
)
from app.application.use_cases.payments.ledger import (
    SettlementRegistrationDetails,
    _fingerprint,
)
from app.application.use_cases.workspace import assert_approved_workspace
from app.core.exceptions import (
    ForbiddenError,
    NotFoundError,
    PaymentCapabilityError,
    PaymentOutcomeUnknownError,
    PaymentProviderError,
    ValidationError,
)
from app.domain.entities.payment import (
    GatewayCapability,
)
from app.domain.entities.profile import Profile
from app.domain.services.authorization import is_owner


class SettlementAccountMixin:
    """Earnings and payee registration; mixed into ``BookingPaymentUseCases``."""

    # --------------------------------------------------------------- earnings
    async def earnings(self, actor: Profile) -> dict[str, Any]:
        if not is_owner(actor):
            raise ForbiddenError("Only the salon owner can view earnings")
        salon_id = await self.repository.find_owner_salon_id(actor.id)
        currency = self.settings.payment_currency
        zero = Decimal("0.00")
        totals = (
            await self.repository.earnings(salon_id)
            if salon_id
            else {
                "online_collected": zero, "platform_fees": zero, "manual_recorded": zero,
                "online_count": 0, "manual_count": 0, "online_refunded": zero,
                "commission_reversed": zero, "overcollected": zero,
            }
        )
        commission_net = Decimal(totals["platform_fees"]) - Decimal(totals["commission_reversed"])
        net = Decimal(totals["online_collected"]) - Decimal(totals["online_refunded"]) - commission_net
        return {
            "currency": currency,
            "online_collected": totals["online_collected"],
            "online_refunded": totals["online_refunded"],
            "platform_fees": totals["platform_fees"],
            "commission_reversed": totals["commission_reversed"],
            "platform_commission_net": commission_net,
            "overcollected": totals["overcollected"],
            "online_net": net,
            "manual_recorded": totals["manual_recorded"],
            "online_payment_count": totals["online_count"],
            "manual_payment_count": totals["manual_count"],
            "note": (
                "Derived from the payment ledger using each payment's commission snapshot. "
                "Provider fees and taxes are not included. Payout timing is decided by the provider."
            ),
        }

    # ------------------------------------------------------ settlement account
    @staticmethod
    def _masked(ref: str | None) -> str | None:
        return None if not ref else "..." + ref[-4:]

    async def get_settlement_account(self, actor: Profile) -> dict[str, Any]:
        if not is_owner(actor):
            raise ForbiddenError("Only the salon owner can view the settlement account")
        enabled = self.resolver.enabled
        gateway = self.resolver.resolve() if enabled else None
        supported = bool(gateway and gateway.supports(GatewayCapability.linked_accounts))
        salon_id = await self.repository.find_owner_salon_id(actor.id)
        account = (
            await self.repository.get_provider_account(salon_id, self.resolver.provider)
            if salon_id and enabled
            else None
        )
        return {
            "provider_enabled": enabled,
            "supported": supported,
            "requires_details": bool(gateway and gateway.supports(GatewayCapability.vendor_kyc)),
            "onboarding_status": account["onboarding_status"] if account else "not_started",
            "requirements": list(account["requirements"]) if account else [],
            "account_reference_masked": self._masked(
                account["provider_account_ref"] if account else None
            ),
        }

    async def register_settlement_account(
        self,
        actor: Profile,
        key: str | None,
        details: SettlementRegistrationDetails | None = None,
    ) -> dict[str, Any]:
        gateway = self._require_gateway(GatewayCapability.linked_accounts)
        if not is_owner(actor):
            raise ForbiddenError("Only the salon owner can register a settlement account")
        await assert_approved_workspace(self.workspace, actor)
        key = self._require_key(key)
        scope = "settlement-register"
        # Deliberately NOT a hash of the submitted details: low-entropy bank data must not be
        # recoverable from the idempotency table.
        replay = await self._idempotent(actor, scope, key, _fingerprint(kind="register"))
        if replay is not None:
            return replay
        salon_id = await self.repository.find_owner_salon_id(actor.id)
        if salon_id is None:
            raise NotFoundError("Salon not found")
        needs_details = gateway.supports(GatewayCapability.vendor_kyc)
        if needs_details and details is None:
            raise ValidationError("Contact, PAN and bank or UPI details are required to register")
        holder = details.legal_name if details else await self.repository.get_payout_holder_name(salon_id)
        if not holder:
            raise ValidationError("Save your payout details before registering for online payments")

        salon_hex = salon_id.replace("-", "")
        pending = await self.repository.begin_registration(
            salon_id, gateway.provider_name, actor.id, lambda gen: f"sv{salon_hex}g{gen}"
        )
        # Vendor identity + 'pending' status are durable BEFORE the provider is called.
        await self._checkpoint(actor)
        request = SettlementAccountRequest(
            salon_id=salon_id,
            legal_name=holder,
            vendor_ref=pending["vendor_ref"],
            email=details.contact_email if details else None,
            phone=details.contact_phone if details else None,
            account_type=details.account_type if details else None,
            business_type=details.business_type if details else None,
            pan=details.pan if details else None,
            bank_account_number=details.bank_account_number if details else None,
            ifsc=details.ifsc if details else None,
            upi_id=details.upi_id if details else None,
        )
        try:
            account = await gateway.register_settlement_account(request)
        except PaymentOutcomeUnknownError:
            # Stays 'pending' under the same vendor id; a retry is idempotent at the provider.
            await self._abandon(actor, scope, key)
            raise
        except (PaymentProviderError, PaymentCapabilityError):
            await self.repository.set_account_result(
                salon_id, gateway.provider_name, "needs_action",
                ["The payment provider rejected the registration. Check the details and submit again."],
                actor.id,
            )
            await self.repository.add_account_audit(
                salon_id=salon_id, provider=gateway.provider_name, action="register_failed",
                previous_status="pending", new_status="needs_action",
                vendor_ref=pending["vendor_ref"], actor_id=actor.id,
            )
            await self._abandon(actor, scope, key)
            raise
        await self.repository.set_account_result(
            salon_id, gateway.provider_name, account.onboarding_status.value,
            list(account.requirements), actor.id, account.account_ref,
        )
        body = {
            "provider_enabled": True,
            "supported": True,
            "requires_details": needs_details,
            "onboarding_status": account.onboarding_status.value,
            "requirements": list(account.requirements),
            "account_reference_masked": self._masked(account.account_ref),
        }
        await self._store_and_commit(actor, scope, key, body, 200)
        return body
