from __future__ import annotations

from typing import Any, Protocol


class StructuredProvider(Protocol):
    """Future provider boundary for structured extraction or classification adapters."""

    name: str

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...
