"""Utilities for dispatching processor queue messages in the GUI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from logging_utils import logger


class TranscriptLike(Protocol):
    """Minimal protocol for the Tk text widget used to display transcripts."""

    def insert(self, index: str, text: str, tag: str | None = None) -> None:
        ...

    def see(self, index: str) -> None:
        ...

    def update_idletasks(self) -> None:
        ...


BannerCallback = Callable[[str, object], None]
StateCallback = Callable[[dict[str, object]], None]


@dataclass
class DispatchResult:
    """Outcome of a dispatch operation."""

    wrote_to_transcript: bool


# Fix: Q-103
class QueueDispatcher:
    """Centralise queue message handling away from the Tkinter view."""

    def __init__(
        self,
        *,
        transcript: TranscriptLike,
        banner_callback: BannerCallback,
        state_callback: StateCallback,
    ) -> None:
        self._transcript = transcript
        self._banner_callback = banner_callback
        self._state_callback = state_callback

    def dispatch(self, level: str, payload: object) -> DispatchResult:
        """Route a queue message to the appropriate handler."""

        if level == "state":
            if isinstance(payload, dict):
                self._state_callback(payload)
            else:
                logger.debug("Ignoring malformed state payload: %s", payload)
            return DispatchResult(wrote_to_transcript=False)

        if level not in {"info", "error", "warning"}:
            logger.debug("Received unknown message type: %s", level)
            level = "info"

        text = self._coerce_payload(payload)
        if text is None:
            logger.debug("Skipping message with empty payload: %s", payload)
            return DispatchResult(wrote_to_transcript=False)

        tag = "info"
        log_text = text
        if level == "error":
            tag = "error"
            logger.error(log_text)
            text = f"ERROR: {log_text}"
        elif level == "warning":
            logger.warning(log_text)
            text = f"WARNING: {log_text}"

        self._transcript.insert("end", text + "\n", tag)
        self._banner_callback(level, payload)
        return DispatchResult(wrote_to_transcript=True)

    @staticmethod
    def _coerce_payload(payload: object) -> str | None:
        if payload is None:
            return None
        if isinstance(payload, (str, bytes)):
            return payload.decode() if isinstance(payload, bytes) else payload
        if isinstance(payload, dict):
            return str(payload)
        return str(payload).strip() or None


__all__ = ["QueueDispatcher", "DispatchResult"]
