"""Payment gateway adapters.

Adapters are discovered by module name: ``PAYMENT_PROVIDER=<name>`` loads
``app.infrastructure.payments.<name>`` and calls its ``create_gateway(settings)``.
Deleting an adapter file therefore removes that provider without touching the core.
"""
