"""Diagnostics models for HID traffic."""

from __future__ import annotations

from pydantic import BaseModel


class HidTraceEntry(BaseModel):
    """A single HID read or write represented for diagnostics."""

    direction: str
    report_id: int
    payload_hex: str
    confidence: str | None = None
    verification: str | None = None
    command_name: str | None = None
