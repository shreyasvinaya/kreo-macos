from fastapi.testclient import TestClient

from kreo_kontrol.api.app import create_app


class FakeMacrosController:
    def __init__(self) -> None:
        self.slots = [
            {
                "slot_id": 0,
                "name": "Copy Burst",
                "execution_type": "FIXED_COUNT",
                "cycle_times": 3,
                "bound_ui_keys": ["right_opt"],
                "actions": [
                    {"key": "c", "event_type": "press", "delay_ms": 12},
                    {"key": "c", "event_type": "release", "delay_ms": 24},
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
        raise NotImplementedError

    def apply_keymap(self, edits):
        raise NotImplementedError

    def read_macros(self):
        return {
            "supported": True,
            "reason": None,
            "verification_status": "verified",
            "next_slot_id": len(self.slots),
            "max_slots": 16,
            "slots": self.slots,
        }

    def apply_macro(self, slot_id: int, request):
        payload = {
            "slot_id": slot_id,
            "name": request["name"],
            "execution_type": request["execution_type"],
            "cycle_times": request["cycle_times"],
            "bound_ui_keys": [request["bound_ui_key"]] if request["bound_ui_key"] else [],
            "actions": request["actions"],
        }
        if slot_id >= len(self.slots):
            self.slots.append(payload)
        else:
            self.slots[slot_id] = payload
        return self.read_macros()

    def delete_macro(self, slot_id: int):
        self.slots = [slot for slot in self.slots if slot["slot_id"] != slot_id]
        for index, slot in enumerate(self.slots):
            slot["slot_id"] = index
        return self.read_macros()


def test_macros_endpoint_returns_typed_slots() -> None:
    client = TestClient(create_app(lighting_controller=FakeMacrosController()))

    response = client.get("/api/macros")

    assert response.status_code == 200
    payload = response.json()
    assert payload["supported"] is True
    assert payload["slots"][0]["name"] == "Copy Burst"
    assert payload["slots"][0]["bound_ui_keys"] == ["right_opt"]
    assert payload["slots"][0]["actions"][0]["key"] == "c"


def test_macro_upsert_endpoint_returns_updated_slot() -> None:
    client = TestClient(create_app(lighting_controller=FakeMacrosController()))

    response = client.put(
        "/api/macros/1",
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
    payload = response.json()
    assert payload["next_slot_id"] == 2
    assert payload["slots"][1]["name"] == "Launch Focus"
    assert payload["slots"][1]["bound_ui_keys"] == ["left_opt"]


def test_macro_delete_endpoint_removes_slot() -> None:
    client = TestClient(create_app(lighting_controller=FakeMacrosController()))

    response = client.delete("/api/macros/0")

    assert response.status_code == 200
    payload = response.json()
    assert payload["slots"] == []
    assert payload["next_slot_id"] == 0
