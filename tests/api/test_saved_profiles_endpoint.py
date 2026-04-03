from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from kreo_kontrol.api.app import create_app
from kreo_kontrol.device.bytech_lighting import LightingController, LightingProtocolError
from kreo_kontrol.device.domains.lighting import (
    LightingState,
    LightingVerificationStatus,
)


class SavedProfilesController:
    def __init__(self) -> None:
        self.applied_keymap_edits: dict[str, dict[str, int | None]] | None = None
        self.applied_lighting_edits: dict[str, str] | None = None
        self.mode = "custom"
        self.brightness = 25
        self.color = None
        self.per_key_colors = {
            "esc": "#ff0000",
            "w": "#00ffaa",
        }
        self.macro_slots = [
            {
                "slot_id": 0,
                "name": "Copy Burst",
                "execution_type": "FIXED_COUNT",
                "cycle_times": 2,
                "bound_ui_keys": ["right_opt"],
                "actions": [
                    {"key": "c", "event_type": "press", "delay_ms": 10},
                    {"key": "c", "event_type": "release", "delay_ms": 20},
                ],
            }
        ]

    def configurable(self) -> bool:
        return True

    def transport_kind(self) -> str:
        return "vendor_hid"

    def supports_profiles(self) -> bool:
        return False

    def is_connected(self) -> bool:
        return True

    def supported_devices(self) -> list[str]:
        return ["Kreo Swarm"]

    def read_state(self) -> LightingState:
        return LightingState(
            mode=self.mode,
            brightness=self.brightness,
            per_key_rgb_supported=True,
            color=self.color,
            verification_status=LightingVerificationStatus.UNVERIFIED,
        )

    def read_per_key_state(self):
        return {
            "mode": self.mode,
            "brightness": self.brightness,
            "per_key_rgb_supported": True,
            "verification_status": "unverified",
            "keys": [
                {
                    "ui_key": "esc",
                    "label": "Esc",
                    "light_pos": 8,
                    "color": self.per_key_colors["esc"],
                },
                {
                    "ui_key": "w",
                    "label": "W",
                    "light_pos": 40,
                    "color": self.per_key_colors["w"],
                },
            ],
        }

    def apply_per_key_colors_by_ui_key(self, edits):
        self.per_key_colors.update(edits)
        self.applied_lighting_edits = edits
        return self.read_per_key_state()

    def apply_global_lighting(self, request):
        self.mode = request.mode
        if request.brightness is not None:
            self.brightness = request.brightness
        self.color = request.color
        return self.read_state()

    def read_keymap(self):
        return {
            "verification_status": "unverified",
            "assignments": [
                {
                    "ui_key": "esc",
                    "logical_id": "ESC",
                    "svg_id": "key_ESC",
                    "label": "Esc",
                    "protocol_pos": 8,
                    "base_action": {
                        "action_id": "esc",
                        "label": "Esc",
                        "category": "Keyboard",
                        "raw_value": 10496,
                    },
                    "fn_action": {
                        "action_id": "media_mute",
                        "label": "Mute",
                        "category": "Media",
                        "raw_value": 33554658,
                    },
                }
            ],
            "available_actions": [
                {
                    "action_id": "esc",
                    "label": "Esc",
                    "category": "Keyboard",
                    "raw_value": 10496,
                }
            ],
        }

    def apply_keymap(self, edits):
        if any(edit.get("fn_raw_value") is not None for edit in edits.values()):
            raise LightingProtocolError("FN-layer remapping is not verified on this keyboard yet")
        self.applied_keymap_edits = edits
        return self.read_keymap()

    def read_macros(self):
        return {
            "supported": True,
            "reason": None,
            "verification_status": "verified",
            "next_slot_id": len(self.macro_slots),
            "max_slots": 16,
            "slots": self.macro_slots,
        }

    def apply_macro(self, slot_id: int, request):
        slot = {
            "slot_id": slot_id,
            "name": request["name"],
            "execution_type": request["execution_type"],
            "cycle_times": request["cycle_times"],
            "bound_ui_keys": [request["bound_ui_key"]] if request["bound_ui_key"] else [],
            "actions": request["actions"],
        }
        if slot_id >= len(self.macro_slots):
            self.macro_slots.append(slot)
        else:
            self.macro_slots[slot_id] = slot
        return self.read_macros()

    def delete_macro(self, slot_id: int):
        self.macro_slots = [slot for slot in self.macro_slots if slot["slot_id"] != slot_id]
        for index, slot in enumerate(self.macro_slots):
            slot["slot_id"] = index
        return self.read_macros()


def test_profiles_endpoint_returns_empty_saved_snapshot_state(tmp_path: Path) -> None:
    client = TestClient(
        create_app(
            lighting_controller=cast(LightingController, SavedProfilesController()),
            saved_profiles_path=tmp_path / "profiles.json",
        )
    )

    response = client.get("/api/profiles")

    assert response.status_code == 200
    assert response.json() == {
        "supported": True,
        "active_profile": None,
        "available_profiles": [],
        "reason": None,
        "storage_kind": "saved_snapshots",
        "active_snapshot_id": None,
        "snapshots": [],
    }


def test_profiles_post_captures_current_keyboard_state(tmp_path: Path) -> None:
    client = TestClient(
        create_app(
            lighting_controller=cast(LightingController, SavedProfilesController()),
            saved_profiles_path=tmp_path / "profiles.json",
        )
    )

    response = client.post("/api/profiles", json={"name": "Desk Setup"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["supported"] is True
    assert payload["active_snapshot_id"] is not None
    assert payload["available_profiles"] == [1]
    assert len(payload["snapshots"]) == 1
    snapshot = payload["snapshots"][0]
    assert snapshot["name"] == "Desk Setup"
    assert snapshot["lighting"]["mode"] == "custom"
    assert snapshot["lighting"]["keys"]["esc"] == "#ff0000"
    assert snapshot["keymap"]["assignments"]["esc"]["base_raw_value"] == 10496
    assert snapshot["keymap"]["assignments"]["esc"]["fn_raw_value"] == 33554658
    assert snapshot["macros"]["slots"][0]["name"] == "Copy Burst"


def test_profiles_apply_replays_saved_lighting_and_keymap(tmp_path: Path) -> None:
    controller = SavedProfilesController()
    client = TestClient(
        create_app(
            lighting_controller=cast(LightingController, controller),
            saved_profiles_path=tmp_path / "profiles.json",
        )
    )

    create_response = client.post("/api/profiles", json={"name": "Desk Setup"})
    snapshot_id = create_response.json()["snapshots"][0]["snapshot_id"]
    controller.macro_slots = [
        {
            "slot_id": 0,
            "name": "Temporary Macro",
            "execution_type": "FIXED_COUNT",
            "cycle_times": 1,
            "bound_ui_keys": ["left_opt"],
            "actions": [
                {"key": "x", "event_type": "press", "delay_ms": 5},
                {"key": "x", "event_type": "release", "delay_ms": 10},
            ],
        }
    ]

    apply_response = client.post(f"/api/profiles/{snapshot_id}/apply")

    assert apply_response.status_code == 200
    assert controller.applied_lighting_edits == {"esc": "#ff0000", "w": "#00ffaa"}
    assert controller.applied_keymap_edits == {
        "esc": {
            "base_raw_value": 10496,
        }
    }
    assert controller.macro_slots[0]["name"] == "Copy Burst"
    assert apply_response.json()["active_snapshot_id"] == snapshot_id


def test_keymap_apply_autosaves_active_snapshot(tmp_path: Path) -> None:
    controller = SavedProfilesController()
    client = TestClient(
        create_app(
            lighting_controller=cast(LightingController, controller),
            saved_profiles_path=tmp_path / "profiles.json",
        )
    )

    create_response = client.post("/api/profiles", json={"name": "Desk Setup"})
    snapshot_id = create_response.json()["snapshots"][0]["snapshot_id"]

    def updated_keymap() -> dict[str, object]:
        return {
            "verification_status": "unverified",
            "assignments": [
                {
                    "ui_key": "esc",
                    "logical_id": "ESC",
                    "svg_id": "key_ESC",
                    "label": "Esc",
                    "protocol_pos": 8,
                    "base_action": {
                        "action_id": "tab",
                        "label": "Tab",
                        "category": "Keyboard",
                        "raw_value": 10497,
                    },
                    "fn_action": {
                        "action_id": "media_mute",
                        "label": "Mute",
                        "category": "Media",
                        "raw_value": 33554658,
                    },
                }
            ],
            "available_actions": [],
        }

    cast(Any, controller).read_keymap = updated_keymap

    response = client.post("/api/keymap/apply", json={"edits": {"esc": {"base_raw_value": 10497}}})

    assert response.status_code == 200
    profiles = client.get("/api/profiles").json()
    snapshot = next(item for item in profiles["snapshots"] if item["snapshot_id"] == snapshot_id)
    assert snapshot["keymap"]["assignments"]["esc"]["base_raw_value"] == 10497
    assert snapshot["macros"]["slots"][0]["name"] == "Copy Burst"


def test_macro_upsert_autosaves_active_snapshot(tmp_path: Path) -> None:
    controller = SavedProfilesController()
    client = TestClient(
        create_app(
            lighting_controller=cast(LightingController, controller),
            saved_profiles_path=tmp_path / "profiles.json",
        )
    )

    create_response = client.post("/api/profiles", json={"name": "Desk Setup"})
    snapshot_id = create_response.json()["snapshots"][0]["snapshot_id"]

    response = client.put(
        "/api/macros/0",
        json={
            "name": "Launch Focus",
            "bound_ui_key": "left_opt",
            "execution_type": "UNTIL_ANY_PRESSED",
            "cycle_times": 1,
            "actions": [
                {"key": "q", "event_type": "press", "delay_ms": 10},
                {"key": "q", "event_type": "release", "delay_ms": 20},
            ],
        },
    )

    assert response.status_code == 200
    profiles = client.get("/api/profiles").json()
    snapshot = next(item for item in profiles["snapshots"] if item["snapshot_id"] == snapshot_id)
    assert snapshot["macros"]["slots"][0]["name"] == "Launch Focus"


def test_apply_without_active_snapshot_does_not_create_autosave(tmp_path: Path) -> None:
    client = TestClient(
        create_app(
            lighting_controller=cast(LightingController, SavedProfilesController()),
            saved_profiles_path=tmp_path / "profiles.json",
        )
    )

    response = client.post("/api/lighting/per-key/apply", json={"edits": {"esc": "#00ff00"}})

    assert response.status_code == 200
    assert client.get("/api/profiles").json()["snapshots"] == []


def test_per_key_lighting_apply_autosaves_active_snapshot(tmp_path: Path) -> None:
    controller = SavedProfilesController()
    client = TestClient(
        create_app(
            lighting_controller=cast(LightingController, controller),
            saved_profiles_path=tmp_path / "profiles.json",
        )
    )

    create_response = client.post("/api/profiles", json={"name": "Desk Setup"})
    snapshot_id = create_response.json()["snapshots"][0]["snapshot_id"]

    response = client.post("/api/lighting/per-key/apply", json={"edits": {"esc": "#00ff00"}})

    assert response.status_code == 200
    profiles = client.get("/api/profiles").json()
    snapshot = next(item for item in profiles["snapshots"] if item["snapshot_id"] == snapshot_id)
    assert snapshot["lighting"]["keys"]["esc"] == "#00ff00"
    assert snapshot["macros"]["slots"][0]["name"] == "Copy Burst"


class FailingSavedProfilesController(SavedProfilesController):
    def apply_keymap(self, edits):
        raise LightingProtocolError("profile replay failed")


def test_profiles_apply_converts_protocol_errors_to_422(tmp_path: Path) -> None:
    client = TestClient(
        create_app(
            lighting_controller=cast(LightingController, FailingSavedProfilesController()),
            saved_profiles_path=tmp_path / "profiles.json",
        ),
        raise_server_exceptions=False,
    )

    create_response = client.post("/api/profiles", json={"name": "Desk Setup"})
    snapshot_id = create_response.json()["snapshots"][0]["snapshot_id"]

    apply_response = client.post(f"/api/profiles/{snapshot_id}/apply")

    assert apply_response.status_code == 422
    assert apply_response.json() == {"detail": "profile replay failed"}
