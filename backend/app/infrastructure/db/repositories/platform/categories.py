"""Service categories and subcategories."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    NotFoundError,
)


class CategoriesMixin:
    """Service categories and subcategories."""

    session: AsyncSession

    async def list_categories(self, include_inactive: bool = False) -> list[dict[str, Any]]:
        """List service categories."""

        where = "" if include_inactive else "where is_active"
        result = await self.session.execute(
            text(
                f"""
                select id, name, slug, image_url, description, sort_order, is_active,
                       created_at, updated_at
                from service_categories
                {where}
                order by sort_order, name
                """
            )
        )
        return [dict(row) for row in result.mappings().all()]

    async def get_category(self, category_id: str) -> dict[str, Any]:
        """Read one service category."""

        result = await self.session.execute(
            text(
                """
                select id, name, slug, image_url, description, sort_order, is_active,
                       created_at, updated_at
                from service_categories
                where id = :category_id
                """
            ),
            {"category_id": category_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Category not found")
        return dict(row)

    async def create_category(self, values: dict[str, Any]) -> dict[str, Any]:
        """Create a service category."""

        result = await self.session.execute(
            text(
                """
                insert into service_categories (name, slug, image_url, description, sort_order)
                values (:name, :slug, :image_url, :description, :sort_order)
                returning id, name, slug, image_url, description, sort_order, is_active,
                          created_at, updated_at
                """
            ),
            {
                "name": values["name"],
                "slug": values["slug"],
                "image_url": values.get("image_url"),
                "description": values.get("description"),
                "sort_order": values.get("sort_order", 0),
            },
        )
        await self.session.commit()
        return dict(result.mappings().one())

    async def update_category(
        self, category_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a service category."""

        allowed = {k: v for k, v in values.items() if v is not None}
        if not allowed:
            return await self.get_category(category_id)
        assignments = ", ".join(f"{k} = :{k}" for k in allowed)
        result = await self.session.execute(
            text(
                f"""
                update service_categories set {assignments}
                where id = :category_id
                returning id, name, slug, image_url, description, sort_order, is_active,
                          created_at, updated_at
                """
            ),
            {**allowed, "category_id": category_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Category not found")
        await self.session.commit()
        return dict(row)

    async def deactivate_category(self, category_id: str) -> dict[str, Any]:
        """Soft-delete a service category."""

        return await self.update_category(category_id, {"is_active": False})

    async def list_subcategories(
        self, category_id: str, include_inactive: bool = False
    ) -> list[dict[str, Any]]:
        """List subcategories for a category."""

        where_active = "" if include_inactive else "and sc.is_active"
        result = await self.session.execute(
            text(
                f"""
                select sc.id, sc.category_id, sc.name, sc.slug, sc.image_url,
                       sc.description, sc.sort_order, sc.is_active,
                       sc.created_at, sc.updated_at
                from service_subcategories sc
                where sc.category_id = :category_id {where_active}
                order by sc.sort_order, sc.name
                """
            ),
            {"category_id": category_id},
        )
        return [dict(row) for row in result.mappings().all()]

    async def get_subcategory(self, subcategory_id: str) -> dict[str, Any]:
        """Read one subcategory."""

        result = await self.session.execute(
            text(
                """
                select id, category_id, name, slug, image_url, description,
                       sort_order, is_active, created_at, updated_at
                from service_subcategories
                where id = :subcategory_id
                """
            ),
            {"subcategory_id": subcategory_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Subcategory not found")
        return dict(row)

    async def create_subcategory(self, values: dict[str, Any]) -> dict[str, Any]:
        """Create a service subcategory."""

        result = await self.session.execute(
            text(
                """
                insert into service_subcategories
                  (category_id, name, slug, image_url, description, sort_order)
                values
                  (:category_id, :name, :slug, :image_url, :description, :sort_order)
                returning id, category_id, name, slug, image_url, description,
                          sort_order, is_active, created_at, updated_at
                """
            ),
            {
                "category_id": values["category_id"],
                "name": values["name"],
                "slug": values["slug"],
                "image_url": values.get("image_url"),
                "description": values.get("description"),
                "sort_order": values.get("sort_order", 0),
            },
        )
        await self.session.commit()
        return dict(result.mappings().one())

    async def update_subcategory(
        self, subcategory_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a service subcategory."""

        allowed = {k: v for k, v in values.items() if v is not None}
        if not allowed:
            return await self.get_subcategory(subcategory_id)
        assignments = ", ".join(f"{k} = :{k}" for k in allowed)
        result = await self.session.execute(
            text(
                f"""
                update service_subcategories set {assignments}
                where id = :subcategory_id
                returning id, category_id, name, slug, image_url, description,
                          sort_order, is_active, created_at, updated_at
                """
            ),
            {**allowed, "subcategory_id": subcategory_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Subcategory not found")
        await self.session.commit()
        return dict(row)

    async def deactivate_subcategory(self, subcategory_id: str) -> dict[str, Any]:
        """Soft-delete a service subcategory."""

        return await self.update_subcategory(subcategory_id, {"is_active": False})

    # ------------------------------------------------------------------
    # Staff languages
    # ------------------------------------------------------------------
