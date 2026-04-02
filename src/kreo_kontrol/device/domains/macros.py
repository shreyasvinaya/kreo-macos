from __future__ import annotations

from pydantic import BaseModel


class MacroSlot(BaseModel):
    slot_id: int
    name: str
    bound_key: str | None = None

