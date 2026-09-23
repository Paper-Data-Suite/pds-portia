"""Explicit application clock seam for Portia teacher-menu workflows."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from portia.models.common import ExplicitOffsetTimestamp

NowSource = Callable[[], datetime]


def _system_now() -> datetime:
    return datetime.now(timezone.utc)


class MenuClock:
    """Yield explicit offset-aware timestamps without domain-layer wall clocks."""

    def __init__(self, now_source: NowSource | None = None) -> None:
        self._now_source = now_source or _system_now

    def now(self) -> ExplicitOffsetTimestamp:
        """Return the current instant as Portia's accepted explicit timestamp."""

        value = self._now_source()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("menu clock must return an offset-aware datetime")
        return ExplicitOffsetTimestamp(value.isoformat())
