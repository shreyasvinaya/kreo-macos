"""Typed response models for the local API."""

from __future__ import annotations

from pydantic import BaseModel


class HealthStatus(BaseModel):
    """Health state returned by the loopback API."""

    status: str


class DeviceSummary(BaseModel):
    """Current keyboard connectivity state for the UI shell."""

    connected: bool
    configurable: bool
    supported_devices: list[str]
    supports_profiles: bool
    transport_kind: str


class KeyboardAssetKey(BaseModel):
    logical_id: str
    svg_id: str
    ui_key: str
    label: str
    protocol_pos: int
    led_index: int


class KeyboardAssetResponse(BaseModel):
    asset_name: str
    base_image_url: str
    letters_image_url: str
    interactive_svg_url: str
    keys: list[KeyboardAssetKey]


class ProfilesResponse(BaseModel):
    supported: bool
    active_profile: int | None
    available_profiles: list[int]
    reason: str | None = None
    storage_kind: str = "saved_snapshots"
    active_snapshot_id: str | None = None
    snapshots: list[SavedProfileSnapshotResponse] = []


class SavedKeymapAssignmentResponse(BaseModel):
    base_raw_value: int
    fn_raw_value: int


class SavedKeymapSnapshotResponse(BaseModel):
    assignments: dict[str, SavedKeymapAssignmentResponse]


class SavedLightingSnapshotResponse(BaseModel):
    mode: str
    brightness: int
    color: str | None = None
    keys: dict[str, str]


class SavedMacroActionResponse(BaseModel):
    key: str
    event_type: str
    delay_ms: int


class SavedMacroSlotResponse(BaseModel):
    slot_id: int
    name: str
    execution_type: str
    cycle_times: int
    bound_ui_keys: list[str]
    actions: list[SavedMacroActionResponse]


class SavedMacrosSnapshotResponse(BaseModel):
    supported: bool
    reason: str | None = None
    slots: list[SavedMacroSlotResponse]


class SavedProfileSnapshotResponse(BaseModel):
    snapshot_id: str
    name: str
    updated_at: str
    lighting: SavedLightingSnapshotResponse
    keymap: SavedKeymapSnapshotResponse
    macros: SavedMacrosSnapshotResponse


class CreateProfilePayload(BaseModel):
    name: str


class KeyActionResponse(BaseModel):
    action_id: str
    label: str
    category: str
    raw_value: int


class KeyAssignmentResponse(BaseModel):
    ui_key: str
    logical_id: str
    svg_id: str
    label: str
    protocol_pos: int
    base_action: KeyActionResponse
    fn_action: KeyActionResponse


class KeymapResponse(BaseModel):
    verification_status: str
    assignments: list[KeyAssignmentResponse]
    available_actions: list[KeyActionResponse]


class KeymapEditPayload(BaseModel):
    base_raw_value: int | None = None
    fn_raw_value: int | None = None


class KeymapApplyPayload(BaseModel):
    edits: dict[str, KeymapEditPayload]


class LightingResponse(BaseModel):
    mode: str
    brightness: int
    per_key_rgb_supported: bool
    color: str | None = None
    verification_status: str = "unverified"


class LightingApplyPayload(BaseModel):
    mode: str
    brightness: int | None = None
    color: str | None = None


class LightingApplyResponse(BaseModel):
    mode: str
    brightness: int
    per_key_rgb_supported: bool
    color: str | None = None
    verification_status: str


class PerKeyLightingEntry(BaseModel):
    ui_key: str
    label: str
    light_pos: int
    color: str


class PerKeyLightingResponse(BaseModel):
    mode: str
    brightness: int
    per_key_rgb_supported: bool
    verification_status: str
    keys: list[PerKeyLightingEntry]


class PerKeyLightingApplyPayload(BaseModel):
    edits: dict[str, str]


class MacroActionResponse(BaseModel):
    key: str
    event_type: str
    delay_ms: int


class MacroSlotResponse(BaseModel):
    slot_id: int
    name: str
    execution_type: str
    cycle_times: int
    bound_ui_keys: list[str]
    actions: list[MacroActionResponse]


class MacroUpsertPayload(BaseModel):
    name: str
    bound_ui_key: str | None = None
    execution_type: str
    cycle_times: int
    actions: list[MacroActionResponse]


class MacrosResponse(BaseModel):
    supported: bool
    reason: str | None = None
    verification_status: str
    next_slot_id: int
    max_slots: int
    slots: list[MacroSlotResponse]
