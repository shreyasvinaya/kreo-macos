from __future__ import annotations

from pydantic import BaseModel


class LightingState(BaseModel):
    mode: str
    brightness: int
    per_key_rgb_supported: bool

