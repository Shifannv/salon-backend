"""The configured outbound SMS gateway: nothing sends until a real provider has an adapter."""

from app.application.ports.messaging_gateway import MessagingGateway
from app.core.config import Settings
from app.core.config import settings as app_settings
from app.infrastructure.messaging.fake_gateway import FakeMessagingGateway
from app.infrastructure.messaging.none_gateway import NoneMessagingGateway

_fake = FakeMessagingGateway()


def provider_connected(cfg: Settings = app_settings) -> bool:
    return cfg.messaging_provider != "none"


def get_messaging_gateway(cfg: Settings = app_settings) -> MessagingGateway:
    return _fake if cfg.messaging_provider == "fake" else NoneMessagingGateway()
