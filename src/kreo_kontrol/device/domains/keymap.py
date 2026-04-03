from __future__ import annotations

from typing import TypedDict

from pydantic import BaseModel


class KeyAction(BaseModel):
    action_id: str
    label: str
    category: str
    raw_value: int


class KeyActionOption(BaseModel):
    action_id: str
    label: str
    category: str
    raw_value: int


class KeyAssignment(BaseModel):
    ui_key: str
    logical_id: str
    svg_id: str
    label: str
    protocol_pos: int
    base_action: KeyAction
    fn_action: KeyAction


class KeymapState(BaseModel):
    verification_status: str
    assignments: list[KeyAssignment]
    available_actions: list[KeyActionOption]


class KeymapPayload(TypedDict):
    verification_status: str
    assignments: list[dict[str, object]]
    available_actions: list[dict[str, object]]
