"""SQL fragments shared by the payment repository mixins."""

_SETTLED = "('captured', 'partially_refunded', 'refunded')"
_OPEN = "('created', 'authorized')"
