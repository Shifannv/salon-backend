"""Shared salon photo policy: one cover and two independent service-page slides."""

from typing import Any

from app.core.exceptions import ValidationError

MAX_GALLERY_PHOTOS = 2


def visible_salon_photos(images: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Bound legacy reads without repeating a cover as a slide."""
    ordered = sorted(images, key=lambda image: (
        not image.get("is_main", False), image.get("sort_order", 0),
        str(image.get("created_at", "")), str(image.get("id", "")),
    ))
    result: list[dict[str, Any]] = []
    urls: set[str] = set()
    covers = slides = 0
    for image in ordered:
        url = image.get("url", "")
        if not url or url in urls:
            continue
        if image.get("is_main"):
            if covers:
                continue
            covers += 1
        else:
            if slides >= MAX_GALLERY_PHOTOS:
                continue
            slides += 1
        urls.add(url)
        result.append(image)
    return result


def validate_salon_photo_write(
    images: list[dict[str, Any]], values: dict[str, Any], image_id: str | None = None,
) -> None:
    """Validate a write while the repository holds the salon row lock."""
    current = next((image for image in images if str(image["id"]) == image_id), {})
    candidate = {**current, **values}
    others = [image for image in images if str(image["id"]) != image_id]
    # Legacy rows remain active until the reviewed cleanup. Permit edits that
    # retain an existing URL, while never introducing another duplicate.
    if (not current or candidate.get("url") != current.get("url")) and any(
        image["url"] == candidate.get("url") for image in others
    ):
        raise ValidationError("Choose a different photo for each salon image")
    is_cover = bool(candidate.get("is_main", False))
    count = sum(bool(image.get("is_main", False)) == is_cover for image in others)
    unchanged_role = bool(current) and bool(current.get("is_main", False)) == is_cover
    if (not current and len(images) >= 1 + MAX_GALLERY_PHOTOS) or (
        not unchanged_role and count >= (1 if is_cover else MAX_GALLERY_PHOTOS)
    ):
        raise ValidationError("A salon supports one cover and at most two gallery photos; replace an existing photo")
