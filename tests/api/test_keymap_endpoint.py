from typing import cast

from fastapi.testclient import TestClient

from kreo_kontrol.api.app import create_app
from kreo_kontrol.device.bytech_lighting import LightingController, LightingProtocolError


class FakeKeymapController:
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

    def read_profiles(self):
        return {
            "supported": False,
            "active_profile": None,
            "available_profiles": [],
            "reason": "Bytech transport does not expose hardware profile slots",
        }

    def read_state(self):
        raise NotImplementedError

    def apply_global_lighting(self, request):
        raise NotImplementedError

    def read_per_key_state(self):
        raise NotImplementedError

    def apply_per_key_colors_by_ui_key(self, edits):
        raise NotImplementedError

    def read_keymap(self):
        return {
            "verification_status": "verified",
            "available_actions": [
                {
                    "action_id": "disabled",
                    "label": "Disabled",
                    "category": "System",
                    "raw_value": 0,
                }
            ],
            "assignments": [
                {
                    "ui_key": "right_opt",
                    "logical_id": "RALT",
                    "svg_id": "key_RALT",
                    "label": "Command",
                    "protocol_pos": 380,
                    "base_action": {
                        "action_id": "basic:right_opt",
                        "label": "Command",
                        "category": "Modifiers",
                        "raw_value": 4194304,
                    },
                    "fn_action": {
                        "action_id": "disabled",
                        "label": "Disabled",
                        "category": "System",
                        "raw_value": 0,
                    },
                }
            ],
        }

    def apply_keymap(self, edits):
        payload = self.read_keymap()
        payload["assignments"][0]["base_action"] = {
            "action_id": "basic:left_opt",
            "label": "Command",
            "category": "Modifiers",
            "raw_value": 262144,
        }
        payload["verification_status"] = "unverified"
        return payload


class RejectingKeymapController(FakeKeymapController):
    def apply_keymap(self, edits):
        raise LightingProtocolError("FN-layer remapping is not verified on this keyboard yet")


def test_keymap_endpoint_returns_typed_assignments() -> None:
    client = TestClient(
        create_app(lighting_controller=cast(LightingController, FakeKeymapController()))
    )

    response = client.get("/api/keymap")

    assert response.status_code == 200
    payload = response.json()
    assert payload["verification_status"] == "verified"
    assert payload["assignments"][0]["ui_key"] == "right_opt"
    assert payload["assignments"][0]["base_action"]["raw_value"] == 4194304
    assert payload["available_actions"][0]["action_id"] == "disabled"


def test_keymap_apply_endpoint_returns_updated_assignment_payload() -> None:
    client = TestClient(
        create_app(lighting_controller=cast(LightingController, FakeKeymapController()))
    )

    response = client.post(
        "/api/keymap/apply",
        json={
            "edits": {
                "right_opt": {
                    "base_raw_value": 262144,
                    "fn_raw_value": 0,
                }
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["verification_status"] == "unverified"
    assert payload["assignments"][0]["base_action"]["raw_value"] == 262144


def test_keymap_apply_endpoint_converts_protocol_errors_to_422() -> None:
    client = TestClient(
        create_app(lighting_controller=cast(LightingController, RejectingKeymapController()))
    )

    response = client.post(
        "/api/keymap/apply",
        json={
            "edits": {
                "right_opt": {
                    "base_raw_value": None,
                    "fn_raw_value": 33554637,
                }
            }
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "FN-layer remapping is not verified on this keyboard yet"
    }
