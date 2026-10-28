"""Owner salon profile and images."""

from collections.abc import Mapping
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.salon_photos import validate_salon_photo_write, visible_salon_photos
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.infrastructure.db.rows import one_dict_or_none

# Columns every owner-salon read/insert/update returns (the admin-create list differs).
_OWNER_SALON_COLUMNS = (
    "id, owner_id, name, address, city, lat, lng, timezone, working_hours, approval_mode, "
    "slot_interval_minutes, accepting_bookings, qr_token, profile_completed, approval_status, "
    "approved_at, approved_by, rejection_reason, is_active, created_at, updated_at"
)


class OwnerSalonMixin:
    """Owner salon profile and images."""

    session: AsyncSession

    async def list_salon_images(self, salon_id: str) -> list[dict[str, Any]]:
        """One cover and at most two distinct slides, including legacy read protection."""
        return visible_salon_photos(await self._list_salon_images_raw(salon_id))

    async def _list_salon_images_raw(self, salon_id: str) -> list[dict[str, Any]]:
        """List active images for a salon.

        Soft-deleted images (is_active = false) are excluded.
        """

        result = await self.session.execute(
            text(
                """
                select id, salon_id, url, caption, is_main, sort_order, created_at, updated_at
                from salon_images
                where salon_id = :salon_id
                  and is_active = true
                order by is_main desc, sort_order asc, created_at asc
                """
            ),
            {"salon_id": salon_id},
        )
        rows = result.mappings().all()
        return [
            {
                **dict(row),
                "id": str(row["id"]),
                "salon_id": str(row["salon_id"]),
            }
            for row in rows
        ]

    async def delete_salon_image(self, actor_id: str, image_id: str) -> str | None:
        """Soft-delete a salon image (set is_active = false).

        Returns the ``url`` of the deleted row so the caller can clean up the
        corresponding R2 object, or ``None`` if the image was not found.
        """

        salon = await self.get_owner_salon(actor_id)
        result = await self.session.execute(
            text(
                """
                update salon_images
                   set is_active = false
                 where id = :image_id
                   and salon_id = :salon_id
                   and is_active = true
                returning url
                """
            ),
            {"image_id": image_id, "salon_id": salon["id"]},
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None
        await self.session.commit()
        return str(row["url"])

    async def get_workspace_salon(self, actor_id: str) -> dict[str, Any] | None:
        """Read workspace state without auto-provisioning a salon."""
        result = await self.session.execute(
            text("""
                select s.id, s.name, s.qr_token, s.is_active, s.profile_completed, s.approval_status
                from salons s
                where s.owner_id = :actor_id
                   or exists (select 1 from staff st where st.salon_id = s.id
                              and st.profile_id = :actor_id and st.is_active)
                order by s.is_active desc, s.created_at asc
                limit 1
            """),
            {"actor_id": actor_id},
        )
        return one_dict_or_none(result)

    async def get_owner_salon(self, actor_id: str) -> dict[str, Any]:
        """Return the salon owned by an actor, auto-provisioning a blank one on first login.

        Owners are created via the Supabase ``handle_new_user`` trigger which only inserts
        into ``profiles``. A salon row does not exist until either an admin creates it or —
        for Google OAuth owners — this method creates it on the first owner-salon request.
        """

        row = await self._get_owner_salon_row(actor_id)
        if row is None:
            return await self.provision_owner_salon(actor_id)
        return await self._owner_salon_with_images(row)

    async def _lock_owner_salon(self, actor_id: str) -> None:
        """Serialize owner-salon creation for one actor within this API."""

        await self.session.execute(
            text("select pg_advisory_xact_lock(hashtext(:actor_id))"),
            {"actor_id": actor_id},
        )

    async def _owner_salon_with_images(self, row: Any) -> dict[str, Any]:
        """Return an owner salon row in the shape expected by the owner app."""

        salon = dict(row)
        salon["id"] = str(salon["id"])
        salon["owner_id"] = str(salon["owner_id"])
        if salon.get("approved_by") is not None:
            salon["approved_by"] = str(salon["approved_by"])
        salon["images"] = await self.list_salon_images(salon["id"])
        return salon

    async def _get_owner_salon_row(self, actor_id: str) -> Mapping[str, Any] | None:
        """Raw DB read — returns the mapping row or None, never raises."""

        result = await self.session.execute(
            text(
                f"""
                select {_OWNER_SALON_COLUMNS}
                from salons
                where owner_id = :actor_id and is_active
                order by created_at asc
                limit 1
                """
            ),
            {"actor_id": actor_id},
        )
        return result.mappings().one_or_none()

    async def provision_owner_salon(self, actor_id: str) -> dict[str, Any]:
        """Create a blank salon for a new owner and return it.

        Idempotent for API traffic: an owner-scoped advisory lock makes concurrent
        first-login requests check for an existing active salon before inserting.
        """

        await self._lock_owner_salon(actor_id)
        existing = await self._get_owner_salon_row(actor_id)
        if existing is not None:
            return await self._owner_salon_with_images(existing)

        result = await self.session.execute(
            text(
                f"""
                insert into salons (owner_id, name, is_active, profile_completed)
                values (:actor_id, '', true, false)
                returning {_OWNER_SALON_COLUMNS}
                """
            ),
            {"actor_id": actor_id},
        )
        await self.session.commit()
        return await self._owner_salon_with_images(result.mappings().one())

    async def _owner_salon_id(self, actor_id: str) -> str:
        """Return the id of the owner's active salon, provisioning a blank one if needed."""

        row = await self._get_owner_salon_row(actor_id)
        if row is None:
            return str((await self.provision_owner_salon(actor_id))["id"])
        return str(row["id"])

    async def _find_owner_salon_id(self, actor_id: str) -> str | None:
        """Read-only salon resolver: the owner's active salon id, or None.

        Unlike ``_owner_salon_id`` this never provisions (and never commits), so a
        ``GET`` cannot create a salon row as a side effect.
        """

        row = await self._get_owner_salon_row(actor_id)
        return None if row is None else str(row["id"])

    async def update_owner_salon(self, actor_id: str, values: dict[str, Any]) -> dict[str, Any]:
        """Update owner-editable salon fields."""

        if {"description", "category"} & values.keys():
            raise ValidationError("Unsupported salon field")
        salon = await self.get_owner_salon(actor_id)
        # _prepare_jsonb_values serialises working_hours so Postgres receives a JSON string
        # that can be cast to jsonb, not a raw Python dict which would raise ProgrammingError.
        allowed = self._prepare_jsonb_values(
            {key: value for key, value in values.items() if value is not None}
        )
        if not allowed:
            return salon

        # _sql_assignment emits `key = :key` for plain columns and
        # `key = cast(:key as jsonb)` for working_hours.
        return await self._update_owner_salon_row(actor_id, salon["id"], allowed)

    async def _update_owner_salon_row(
        self, actor_id: str, salon_id: Any, assignments_values: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply column updates to the owner's active salon and return it with images."""

        assignments = ", ".join(self._sql_assignment(key) for key in assignments_values)
        result = await self.session.execute(
            text(
                f"""
                update salons
                set {assignments}
                where id = :salon_id and owner_id = :actor_id and is_active
                returning {_OWNER_SALON_COLUMNS}
                """
            ),
            {**assignments_values, "salon_id": salon_id, "actor_id": actor_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Salon not found")
        await self.session.commit()
        return await self._owner_salon_with_images(row)

    async def complete_owner_salon(
        self, actor_id: str, values: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Submit onboarding for review; a rejected salon may be resubmitted."""

        if {"description", "category"} & (values or {}).keys():
            raise ValidationError("Unsupported salon field")
        allowed = self._prepare_jsonb_values(dict(values or {}))
        payload = {**allowed, "profile_completed": True}

        await self._lock_owner_salon(actor_id)
        salon = await self._get_owner_salon_row(actor_id)
        if salon is not None:
            locked = await self.session.execute(
                text("select approval_status from salons where id = :id for update"),
                {"id": salon["id"]},
            )
            salon = {**salon, "approval_status": locked.scalar_one()}
        if salon is None:
            if not payload.get("name"):
                raise ValidationError("Salon name is required to complete setup")
            fields = ["owner_id", *payload.keys()]
            params = {"owner_id": actor_id, **payload}
            columns = ", ".join(fields)
            placeholders = ", ".join(self._sql_value_placeholder(field) for field in fields)
            result = await self.session.execute(
                text(
                    f"""
                    insert into salons ({columns})
                    values ({placeholders})
                    returning {_OWNER_SALON_COLUMNS}
                    """
                ),
                params,
            )
            await self.session.commit()
            return await self._owner_salon_with_images(result.mappings().one())

        if salon["approval_status"] == "rejected":
            payload.update(approval_status="pending", approved_at=None, approved_by=None,
                           rejection_reason=None)

        return await self._update_owner_salon_row(actor_id, salon["id"], payload)

    async def create_salon_image(self, actor_id: str, values: dict[str, Any]) -> dict[str, Any]:
        """Create an image for the owner's salon."""

        salon = await self.get_owner_salon(actor_id)
        await self.session.execute(text("select id from salons where id = :id for update"), {"id": salon["id"]})
        # The publication use case holds the URL advisory lock. A lost attach
        # response can safely retry without inserting a duplicate gallery row.
        existing = await self.session.execute(text("""
            select id, salon_id, url, caption, is_main, sort_order, created_at, updated_at
            from salon_images where salon_id = :salon_id and url = :url and is_active = true
            limit 1
        """), {"salon_id": salon["id"], "url": values["url"]})
        row = existing.mappings().one_or_none()
        if row is not None:
            if bool(row.get("is_main")) != bool(values.get("is_main", False)):
                raise ValidationError("Choose a different photo for each salon image")
            await self.session.commit()
            return dict(row)
        validate_salon_photo_write(await self._list_salon_images_raw(salon["id"]), values)
        result = await self._execute_salon_photo_write(
            text(
                """
                insert into salon_images (salon_id, url, caption, is_main, sort_order)
                values (:salon_id, :url, :caption, :is_main, :sort_order)
                returning id, salon_id, url, caption, is_main, sort_order, created_at, updated_at
                """
            ),
            {
                "salon_id": salon["id"],
                "url": values["url"],
                "caption": values.get("caption"),
                "is_main": values.get("is_main", False),
                "sort_order": values.get("sort_order", 0),
            },
        )
        await self.session.commit()
        return dict(result.mappings().one())

    async def update_salon_image(
        self, actor_id: str, image_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update an owner salon image."""

        salon = await self.get_owner_salon(actor_id)
        await self.session.execute(text("select id from salons where id = :id for update"), {"id": salon["id"]})
        images = await self._list_salon_images_raw(salon["id"])
        if not any(str(image["id"]) == image_id for image in images):
            raise NotFoundError("Image not found")
        allowed = {key: value for key, value in values.items() if value is not None}
        if not allowed:
            return next(image for image in images if str(image["id"]) == image_id)
        validate_salon_photo_write(images, allowed, image_id)
        assignments = ", ".join(f"{key} = :{key}" for key in allowed)
        result = await self._execute_salon_photo_write(
            text(
                f"""
                update salon_images
                set {assignments}
                where id = :image_id and salon_id = :salon_id
                returning id, salon_id, url, caption, is_main, sort_order, created_at, updated_at
                """
            ),
            {**allowed, "image_id": image_id, "salon_id": salon["id"]},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Image not found")
        await self.session.commit()
        return dict(row)

    async def _execute_salon_photo_write(self, statement: Any, values: dict[str, Any]) -> Any:
        """Map only known photo constraints; never expose raw database errors."""
        try:
            return await self.session.execute(statement, values)
        except DBAPIError as error:
            await self.session.rollback()
            state = getattr(error.orig, "sqlstate", None)
            diagnostic = str(error.orig)
            if state == "23505" and "uq_salon_active_image_url" in diagnostic:
                raise ValidationError("Choose a different photo for each salon image") from None
            if state == "23514" and any(code in diagnostic for code in ("salon_photo_limit", "salon_photo_move_forbidden")):
                raise ValidationError("A salon supports one cover and at most two gallery photos; refresh and try again") from None
            if state == "40001":
                raise ConflictError("Salon photos changed; refresh and try again") from None
            raise
