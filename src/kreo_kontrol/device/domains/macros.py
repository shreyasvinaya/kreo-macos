from __future__ import annotations

from typing import Literal, TypedDict

from pydantic import BaseModel, Field

MacroExecutionType = Literal["FIXED_COUNT", "UNTIL_RELEASED", "UNTIL_ANY_PRESSED"]
MacroEventType = Literal["press", "release"]


class MacroAction(BaseModel):
    key: str
    event_type: MacroEventType
    delay_ms: int = Field(ge=0, le=0x0FFFFF)


class MacroSlot(BaseModel):
    slot_id: int
    name: str
    execution_type: MacroExecutionType
    cycle_times: int = Field(ge=1, le=250)
    bound_ui_keys: list[str] = Field(default_factory=list)
    actions: list[MacroAction] = Field(default_factory=list)


class MacroUpsertRequest(BaseModel):
    name: str
    bound_ui_key: str | None = None
    execution_type: MacroExecutionType = "FIXED_COUNT"
    cycle_times: int = Field(default=1, ge=1, le=250)
    actions: list[MacroAction] = Field(default_factory=list)


class MacrosPayload(TypedDict):
    supported: bool
    reason: str | None
    verification_status: str
    next_slot_id: int
    max_slots: int
    slots: list[dict[str, object]]
