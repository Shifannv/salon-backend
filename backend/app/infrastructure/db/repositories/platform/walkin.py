"""Walk-in QR codes and salon lookup."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    QrCodeNotFoundError,
)


class WalkinMixin:
    """Walk-in QR codes and salon lookup."""

    session: AsyncSession

    async def get_qr_image_url(self, salon_id: str) -> str | None:
        """Return the cached QR image URL from the salons table, or None if not yet set."""
        result = await self.session.execute(
            text("select qr_image_url from salons where id = :salon_id"),
            {"salon_id": salon_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None
        return row["qr_image_url"]  # may be None if column is NULL

    async def set_qr_image_url(self, salon_id: str, url: str) -> None:
        """Persist the QR image URL so future requests return immediately."""
        await self.session.execute(
            text(
                "update salons set qr_image_url = :url where id = :salon_id"
            ),
            {"salon_id": salon_id, "url": url},
        )
        await self.session.commit()

    async def validate_qr_token(self, qr_token: str) -> str:
        """Validate a QR token and return the salon_id (UUID as str).

        Lightweight alternative to get_salon_by_qr — used in the booking path
        where we only need to confirm the token is valid and get the salon_id.
        No services or staff are fetched.
        """

        result = await self.session.execute(
            text(
                """
                select id
                from get_salon_by_qr(:qr_token)
                """
            ),
            {"qr_token": qr_token},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise QrCodeNotFoundError("Salon not found or not accepting walk-ins")
        return str(row["id"])

    async def get_salon_by_qr(self, qr_token: str) -> dict[str, Any]:
        """Return salon info via the get_salon_by_qr database function.

        The DB function validates approval, activity, and profile completion.
        We then fetch the full salon row to include address and image_url,
        which are needed by the walk-in slot-first UI mini-header.
        """

        # Step 1: validate QR via the security-definer DB function
        result = await self.session.execute(
            text(
                """
                select id, name, city, timezone, approval_mode
                from get_salon_by_qr(:qr_token)
                """
            ),
            {"qr_token": qr_token},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise QrCodeNotFoundError("Salon not found or not accepting walk-ins")
        salon = dict(row)
        salon["qr_token"] = qr_token

        # Step 2: fetch extra display fields from the salons table/image table
        extra = await self.session.execute(
            text(
                """
                select s.address, s.working_hours, s.accepting_bookings, img.url as image_url
                from salons s
                left join lateral (
                  select url
                  from salon_images
                  where salon_id = s.id
                    and is_active = true
                  order by is_main desc, sort_order asc, created_at asc
                  limit 1
                ) img on true
                where s.id = :salon_id
                """
            ),
            {"salon_id": str(salon["id"])},
        )
        extra_row = extra.mappings().one_or_none()
        if extra_row:
            salon["address"] = extra_row["address"]
            salon["image_url"] = extra_row["image_url"]
            salon["working_hours"] = extra_row["working_hours"]
            salon["accepting_bookings"] = extra_row["accepting_bookings"]

        salon["id"] = str(salon["id"])
        salon["images"] = await self.list_salon_images(salon["id"])
        salon["services"] = await self.list_public_services(salon["id"])
        salon["staff"] = await self._list_walkin_staff(str(salon["id"]))
        return salon

    async def _list_walkin_staff(self, salon_id: str) -> list[dict[str, Any]]:
        """Return active staff for walk-in display."""

        result = await self.session.execute(
            text(
                """
                select st.id, st.name, st.photo_url, st.specialization, st.working_hours,
                       array(select cast(ss.service_id as text)
                             from staff_services ss join services sv on sv.id = ss.service_id
                             where ss.staff_id = st.id and ss.is_active and sv.is_active
                               and sv.salon_id = st.salon_id
                             order by ss.service_id) as service_ids
                from staff st
                where st.salon_id = :salon_id and st.is_active
                order by st.name
                """
            ),
            {"salon_id": salon_id},
        )
        return [{**dict(row), "id": str(row["id"])} for row in result.mappings().all()]

    # ------------------------------------------------------------------
    # Fix: register_device now accepts the actor_id explicitly
    # ------------------------------------------------------------------
