"""Typed response models for the local API."""

from __future__ import annotations

from pydantic import BaseModel


class HealthStatus(BaseModel):
    """Health state returned by the loopback API."""

    status: str


class DeviceSummary(BaseModel):
    """Current keyboard connectivity state for the UI shell."""

    connected: bool
    supported_devices: list[str]


class ProfilesResponse(BaseModel):
    active_profile: int
    available_profiles: list[int]


class KeymapResponse(BaseModel):
    assignments: list[dict[str, str | None]]


class LightingResponse(BaseModel):
    mode: str
    brightness: int
    per_key_rgb_supported: bool


class MacrosResponse(BaseModel):
    slots: list[dict[str, str | int | None]]
