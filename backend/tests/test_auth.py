from app.application.use_cases.auth.me import GetMe
from app.domain.entities.profile import Profile, Role


async def test_get_me_returns_active_actor() -> None:
    actor = Profile(
        id="00000000-0000-0000-0000-000000000001",
        role=Role.customer,
        full_name="Test User",
        email="test@example.com",
        phone=None,
        phone_verified=False,
        avatar_url=None,
        is_active=True,
    )

    response = await GetMe().execute(actor)

    assert response.profile == actor
