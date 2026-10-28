"""In-memory usage store for messaging tests (no database, no network)."""

from app.domain.services.messaging_quota import QuotaWindow


class InMemoryUsageStore:
    """Counts accepted sends per salon and month window and remembers claimed keys."""

    def __init__(self, preset: dict[str, int] | None = None) -> None:
        self._counts: dict[tuple[str, str], int] = {}
        self._preset = dict(preset or {})
        self._claimed: set[str] = set()
        self._first_window: dict[str, str] = {}

    @staticmethod
    def _window_key(window: QuotaWindow) -> str:
        return window.start.isoformat()

    async def used_in_window(self, salon_id: str, window: QuotaWindow) -> int:
        # Preset usage belongs to the first window the salon is seen in, like a real month.
        first = self._first_window.setdefault(salon_id, self._window_key(window))
        base = self._preset.get(salon_id, 0) if first == self._window_key(window) else 0
        return base + self._counts.get((salon_id, self._window_key(window)), 0)

    async def claim(self, key: str) -> bool:
        if key in self._claimed:
            return False
        self._claimed.add(key)
        return True

    async def record_accepted(
        self, salon_id: str, window: QuotaWindow, key: str, provider_message_id: str | None
    ) -> None:
        slot = (salon_id, self._window_key(window))
        self._counts[slot] = self._counts.get(slot, 0) + 1

    def used(self, salon_id: str) -> int:
        """Total accepted sends recorded here plus any preset, for assertions."""
        return self._preset.get(salon_id, 0) + sum(
            count for (salon, _), count in self._counts.items() if salon == salon_id
        )
