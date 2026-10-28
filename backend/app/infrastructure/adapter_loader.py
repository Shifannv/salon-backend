"""Load a provider adapter module by configured name (shared by the resolvers)."""

import importlib
import re
from types import ModuleType

from app.core.exceptions import PaymentProviderNotConfiguredError

_MODULE_NAME = re.compile(r"[a-z][a-z0-9_]*")


def load_adapter(package: str, provider: str, *, misconfigured: str, not_installed: str) -> ModuleType:
    """Import ``<package>.<provider>``; the name is validated first so config cannot reach
    arbitrary modules. Failures raise ``PaymentProviderNotConfiguredError`` with the given
    messages."""

    if not _MODULE_NAME.fullmatch(provider):
        raise PaymentProviderNotConfiguredError(misconfigured)
    try:
        return importlib.import_module(f"{package}.{provider}")
    except ModuleNotFoundError as exc:
        raise PaymentProviderNotConfiguredError(not_installed) from exc
