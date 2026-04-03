"""Persistent app-side profile snapshots for Kreo Kontrol."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field

from kreo_kontrol.api.models import (
    ProfilesResponse,
    SavedKeymapAssignmentResponse,
    SavedKeymapSnapshotResponse,
    SavedLightingSnapshotResponse,
    SavedProfileSnapshotResponse,
)
from kreo_kontrol.device.domains.lighting import LightingApplyRequest


class SavedKeymapAssignment(BaseModel):
    base_raw_value: int
    fn_raw_value: int


class SavedKeymapSnapshot(BaseModel):
    assignments: dict[str, SavedKeymapAssignment]


class SavedLightingSnapshot(BaseModel):
    mode: str
    brightness: int
    color: str | None = None
    keys: dict[str, str]


class SavedProfileSnapshot(BaseModel):
    snapshot_id: str
    name: str
    updated_at: str
    lighting: SavedLightingSnapshot
    keymap: SavedKeymapSnapshot


class SavedProfilesDocument(BaseModel):
    active_snapshot_id: str | None = None
    snapshots: list[SavedProfileSnapshot] = Field(default_factory=list)


def default_saved_profiles_path() -> Path:
    """Return the default on-disk location for saved snapshots."""

    return Path.cwd() / ".kreo-kontrol-state" / "profiles.json"


class SavedProfilesStore:
    """Persist and apply app-side profile snapshots."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or default_saved_profiles_path()

    def load(self) -> SavedProfilesDocument:
        """Load the current saved-profile document."""

        if not self._path.exists():
            return SavedProfilesDocument()
        return SavedProfilesDocument.model_validate_json(self._path.read_text(encoding="utf-8"))

    def to_response(self) -> ProfilesResponse:
        """Build the typed API response for the current saved profiles."""

        return self._to_response(self.load())

    def capture_current(self, controller, name: str) -> ProfilesResponse:
        """Capture the current keyboard state into a saved snapshot."""

        document = self.load()
        lighting_state = controller.read_state()
        per_key_state = controller.read_per_key_state()
        keymap_state = controller.read_keymap()

        snapshot = SavedProfileSnapshot(
            snapshot_id=str(uuid4()),
            name=name,
            updated_at=datetime.now(UTC).isoformat(),
            lighting=SavedLightingSnapshot(
                mode=lighting_state.mode,
                brightness=lighting_state.brightness,
                color=lighting_state.color,
                keys={
                    str(entry["ui_key"]): str(entry["color"])
                    for entry in per_key_state["keys"]
                },
            ),
            keymap=SavedKeymapSnapshot(
                assignments={
                    str(entry["ui_key"]): SavedKeymapAssignment(
                        base_raw_value=int(entry["base_action"]["raw_value"]),
                        fn_raw_value=int(entry["fn_action"]["raw_value"]),
                    )
                    for entry in keymap_state["assignments"]
                }
            ),
        )
        document.snapshots.append(snapshot)
        document.active_snapshot_id = snapshot.snapshot_id
        self._save(document)
        return self._to_response(document)

    def apply_snapshot(self, controller, snapshot_id: str) -> ProfilesResponse:
        """Apply a saved snapshot back to the controller."""

        document = self.load()
        snapshot = next(
            (entry for entry in document.snapshots if entry.snapshot_id == snapshot_id),
            None,
        )
        if snapshot is None:
            raise ValueError(f"saved profile {snapshot_id!r} does not exist")

        controller.apply_keymap(
            {
                ui_key: {
                    "base_raw_value": assignment.base_raw_value,
                    "fn_raw_value": assignment.fn_raw_value,
                }
                for ui_key, assignment in snapshot.keymap.assignments.items()
            }
        )
        if snapshot.lighting.mode == "custom":
            controller.apply_per_key_colors_by_ui_key(snapshot.lighting.keys)
        elif snapshot.lighting.mode == "static":
            controller.apply_global_lighting(
                LightingApplyRequest(
                    mode="static",
                    brightness=snapshot.lighting.brightness,
                    color=snapshot.lighting.color,
                )
            )

        document.active_snapshot_id = snapshot.snapshot_id
        self._save(document)
        return self._to_response(document)

    def _save(self, document: SavedProfilesDocument) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(document.model_dump_json(indent=2), encoding="utf-8")

    def _to_response(self, document: SavedProfilesDocument) -> ProfilesResponse:
        active_index = None
        if document.active_snapshot_id is not None:
            for index, snapshot in enumerate(document.snapshots, start=1):
                if snapshot.snapshot_id == document.active_snapshot_id:
                    active_index = index
                    break

        return ProfilesResponse(
            supported=True,
            active_profile=active_index,
            available_profiles=list(range(1, len(document.snapshots) + 1)),
            reason=None,
            storage_kind="saved_snapshots",
            active_snapshot_id=document.active_snapshot_id,
            snapshots=[
                SavedProfileSnapshotResponse(
                    snapshot_id=snapshot.snapshot_id,
                    name=snapshot.name,
                    updated_at=snapshot.updated_at,
                    lighting=SavedLightingSnapshotResponse(
                        mode=snapshot.lighting.mode,
                        brightness=snapshot.lighting.brightness,
                        color=snapshot.lighting.color,
                        keys=snapshot.lighting.keys,
                    ),
                    keymap=SavedKeymapSnapshotResponse(
                        assignments={
                            ui_key: SavedKeymapAssignmentResponse(
                                base_raw_value=assignment.base_raw_value,
                                fn_raw_value=assignment.fn_raw_value,
                            )
                            for ui_key, assignment in snapshot.keymap.assignments.items()
                        }
                    ),
                )
                for snapshot in document.snapshots
            ],
        )
