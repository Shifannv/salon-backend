"""Unit tests for Admin use cases."""

import pytest

from app.application.use_cases.admin import AdminUseCases, CatalogAdminUseCases
from app.core.exceptions import ForbiddenError
from app.domain.entities.profile import Role
from tests.conftest import make_mock_repo, make_profile, make_super_admin

# ---------------------------------------------------------------------------
# AdminUseCases — salon management
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_list_salons_requires_super_admin():
    repo = make_mock_repo()
    auth_gateway = object()
    uc = AdminUseCases(repo, auth_gateway)
    customer = make_profile(role=Role.customer)

    with pytest.raises(ForbiddenError):
        await uc.list_salons(customer, search=None, limit=20, offset=0)


@pytest.mark.asyncio
async def test_admin_list_salons_super_admin_ok():
    repo = make_mock_repo()
    repo.admin_list_salons.return_value = []
    auth_gateway = object()
    uc = AdminUseCases(repo, auth_gateway)
    admin = make_super_admin()

    result = await uc.list_salons(admin, search=None, limit=20, offset=0)
    assert result == []
    repo.admin_list_salons.assert_awaited_once_with(None, 20, 0)


@pytest.mark.asyncio
async def test_admin_deactivate_salon_requires_super_admin():
    repo = make_mock_repo()
    auth_gateway = object()
    uc = AdminUseCases(repo, auth_gateway)
    owner = make_profile(role=Role.owner)

    with pytest.raises(ForbiddenError):
        await uc.deactivate_salon(owner, "salon-001")


# ---------------------------------------------------------------------------
# CatalogAdminUseCases — categories
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_list_categories_requires_super_admin():
    repo = make_mock_repo()
    uc = CatalogAdminUseCases(repo)
    customer = make_profile(role=Role.customer)

    with pytest.raises(ForbiddenError):
        await uc.list_categories(customer)


@pytest.mark.asyncio
async def test_admin_list_categories_super_admin_ok():
    repo = make_mock_repo()
    repo.list_categories.return_value = [{"id": "cat-001", "name": "Hair"}]
    uc = CatalogAdminUseCases(repo)
    admin = make_super_admin()

    categories = await uc.list_categories(admin)
    assert len(categories) == 1
    repo.list_categories.assert_awaited_once_with(False)
