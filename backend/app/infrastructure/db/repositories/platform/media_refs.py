"""Media reference locks and checks."""


from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class MediaRefsMixin:
    """Media reference locks and checks."""

    session: AsyncSession

    async def lock_media_url(self, url: str) -> None:
        """Serialize reference writes and cleanup across API/worker processes."""
        if "/webp-v2/" in url:
            # All members share a lock before their individual URL locks. No new
            # schema is needed; direct client media assignment remains guarded by 0020.
            family = url.rsplit("/", 1)[0] + "/"
            await self.session.execute(
                text("select pg_advisory_xact_lock(hashtextextended(:url, 0))"), {"url": family},
            )
        await self.session.execute(
            text("select pg_advisory_xact_lock(hashtextextended(:url, 0))"), {"url": url},
        )

    async def media_reference_guards_installed(self) -> bool:
        """Cleanup requires enabled DB guards, including direct Data API writes."""
        result = await self.session.execute(text("""
            select count(*) = 7
            from pg_trigger t
            join pg_class c on c.oid = t.tgrelid
            join pg_namespace n on n.oid = c.relnamespace
            where n.nspname = current_schema() and t.tgname = 'media_reference_guard'
              and t.tgenabled in ('O', 'A') and not t.tgisinternal
              and c.relname in ('profiles', 'staff', 'salon_images', 'services',
                                'service_categories', 'service_subcategories', 'salons')
        """))
        return bool(result.scalar_one())

    async def media_url_is_referenced(self, url: str) -> bool:
        """Include inactive records: soft deletion must not destroy shared media."""
        # This does not bypass RLS. A role whose policies would hide references
        # gets an error instead of a dangerously incomplete cleanup decision.
        await self.session.execute(text("set local row_security = off"))
        result = await self.session.execute(text("""
            select exists (
                select 1 from profiles where avatar_url = :url
                union all select 1 from staff where photo_url = :url
                union all select 1 from salon_images where url = :url and is_active = true
                union all select 1 from services where photo_url = :url
                union all select 1 from service_categories where image_url = :url
                union all select 1 from service_subcategories where image_url = :url
                union all select 1 from salons where qr_image_url = :url
            )
        """), {"url": url})
        return bool(result.scalar_one())
