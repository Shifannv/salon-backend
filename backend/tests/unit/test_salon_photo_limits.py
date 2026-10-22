"""Photo policy protects slot independence, retry and replacement behavior."""

import pytest

from app.application.salon_photos import validate_salon_photo_write, visible_salon_photos
from app.core.exceptions import ValidationError


def photo(key, *, cover=False, order=0, url=None):
    return {"id": key, "url": url or f"https://media.test/{key}.jpg", "is_main": cover, "sort_order": order}


def test_reads_keep_cover_and_two_distinct_slides_in_owner_order():
    images = [photo("late", order=3), photo("cover", cover=True),
              photo("duplicate", url="https://media.test/cover.jpg"),
              photo("two", order=2), photo("one", order=1)]
    assert [p["id"] for p in visible_salon_photos(images)] == ["cover", "one", "two"]


def test_same_photo_cannot_fill_cover_and_slide():
    cover = photo("cover", cover=True)
    with pytest.raises(ValidationError, match="different photo"):
        validate_salon_photo_write([cover], {"url": cover["url"]})


def test_two_slides_are_allowed_but_a_third_is_rejected():
    images = [photo("cover", cover=True), photo("one"), photo("two")]
    with pytest.raises(ValidationError, match="two gallery"):
        validate_salon_photo_write(images, photo("three"))
    validate_salon_photo_write(images, {"url": "https://media.test/replaced.jpg"}, "two")


def test_cover_replacement_keeps_slide_capacity():
    images = [photo("cover", cover=True), photo("one"), photo("two")]
    validate_salon_photo_write(images, {"url": "https://media.test/new-cover.jpg"}, "cover")
    with pytest.raises(ValidationError):
        validate_salon_photo_write(images, photo("other-cover", cover=True))


def test_legacy_third_slide_does_not_block_replacing_a_visible_slide():
    images = [photo("cover", cover=True), photo("one"), photo("two"), photo("three")]
    validate_salon_photo_write(images, {"url": "https://media.test/replacement.jpg"}, "one")
    with pytest.raises(ValidationError, match="two gallery"):
        validate_salon_photo_write(images, photo("four"))
    with pytest.raises(ValidationError, match="different photo"):
        validate_salon_photo_write(images, {"url": images[2]["url"]}, "one")


def test_legacy_duplicate_allows_metadata_updates_and_unique_replacement():
    cover = photo("cover", cover=True)
    duplicate = photo("one", url=cover["url"])
    images = [cover, duplicate, photo("two")]
    validate_salon_photo_write(images, {"caption": "New caption"}, "one")
    validate_salon_photo_write(images, {"url": "https://media.test/unique.jpg"}, "one")
    with pytest.raises(ValidationError, match="different photo"):
        validate_salon_photo_write(images, {"url": images[2]["url"]}, "one")


def test_legacy_excess_does_not_allow_a_role_change_that_adds_capacity():
    images = [photo("one"), photo("two"), photo("extra-cover", cover=True)]
    with pytest.raises(ValidationError, match="two gallery"):
        validate_salon_photo_write(images, {"is_main": False}, "extra-cover")


def test_legacy_three_slides_cannot_add_a_fourth_photo_as_cover():
    images = [photo("one"), photo("two"), photo("three")]
    with pytest.raises(ValidationError, match="two gallery"):
        validate_salon_photo_write(images, photo("cover", cover=True))
    validate_salon_photo_write(images, {"is_main": True}, "three")
