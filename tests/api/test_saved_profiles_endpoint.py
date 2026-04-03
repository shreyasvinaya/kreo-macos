from __future__ import annotations

from pathlib import Path
from typing import cast

from fastapi.testclient import TestClient

from kreo_kontrol.api.app import create_app
from kreo_kontrol.device.bytech_lighting import LightingController
from kreo_kontrol.device.domains.lighting import (
    LightingState,
    LightingVerificationStatus,
)


class SavedProfilesController:
    def __init__(self) -> None:
        self.applied_keymap_edits: dict[str, dict[str, int | None]] | None = None
        self.applied_lighting_edits: dict[str, str] | None = None

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
            mode="custom",
            brightness=25,
            per_key_rgb_supported=True,
            color=None,
            verification_status=LightingVerificationStatus.UNVERIFIED,
        )

    def read_per_key_state(self):
        return {
            "mode": "custom",
            "brightness": 25,
            "per_key_rgb_supported": True,
            "verification_status": "unverified",
            "keys": [
                {
                    "ui_key": "esc",
                    "label": "Esc",
                    "light_pos": 8,
                    "color": "#ff0000",
                },
                {
                    "ui_key": "w",
                    "label": "W",
                    "light_pos": 40,
                    "color": "#00ffaa",
                },
            ],
        }

    def apply_per_key_colors_by_ui_key(self, edits):
        self.applied_lighting_edits = edits
        return self.read_per_key_state()

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
        self.applied_keymap_edits = edits
        return self.read_keymap()


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

    apply_response = client.post(f"/api/profiles/{snapshot_id}/apply")

    assert apply_response.status_code == 200
    assert controller.applied_lighting_edits == {"esc": "#ff0000", "w": "#00ffaa"}
    assert controller.applied_keymap_edits == {
        "esc": {
            "base_raw_value": 10496,
            "fn_raw_value": 33554658,
        }
    }
    assert apply_response.json()["active_snapshot_id"] == snapshot_id
