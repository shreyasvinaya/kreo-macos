from __future__ import annotations

from typing import cast

from fastapi.testclient import TestClient

from kreo_kontrol.api.app import create_app
from kreo_kontrol.device.bytech_lighting import LightingController
from kreo_kontrol.device.domains.lighting import (
    LightingApplyRequest,
    LightingState,
    LightingVerificationStatus,
)


class FakePerKeyLightingController:
    def read_state(self) -> LightingState:
        return LightingState(
            mode="custom",
            brightness=25,
            per_key_rgb_supported=True,
            color=None,
            verification_status=LightingVerificationStatus.UNVERIFIED,
        )

    def apply_global_lighting(self, request: LightingApplyRequest) -> LightingState:
        return LightingState(
            mode=request.mode,
            brightness=request.brightness if request.brightness is not None else 25,
            per_key_rgb_supported=True,
            color=request.color,
            verification_status=LightingVerificationStatus.UNVERIFIED,
        )

    def read_per_key_state(self) -> dict[str, object]:
        return {
            "mode": "custom",
            "brightness": 25,
            "per_key_rgb_supported": True,
            "verification_status": "unverified",
            "keys": [
                {"ui_key": "esc", "label": "Esc", "light_pos": 8, "color": "#ff0000"},
                {"ui_key": "space", "label": "Space", "light_pos": 43, "color": "#ffffff"},
            ],
        }

    def apply_per_key_colors_by_ui_key(self, edits: dict[str, str]) -> dict[str, object]:
        assert edits == {"esc": "#00ff00"}
        return {
            "mode": "custom",
            "brightness": 25,
            "per_key_rgb_supported": True,
            "verification_status": "unverified",
            "keys": [
                {"ui_key": "esc", "label": "Esc", "light_pos": 8, "color": "#00ff00"},
                {"ui_key": "space", "label": "Space", "light_pos": 43, "color": "#ffffff"},
            ],
        }


def test_per_key_lighting_get_returns_keyboard_colors() -> None:
    client = TestClient(
        create_app(lighting_controller=cast(LightingController, FakePerKeyLightingController()))
    )

    response = client.get("/api/lighting/per-key")

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "custom"
    assert payload["keys"][0]["ui_key"] == "esc"
    assert payload["keys"][0]["color"] == "#ff0000"


def test_per_key_lighting_apply_returns_updated_colors() -> None:
    client = TestClient(
        create_app(lighting_controller=cast(LightingController, FakePerKeyLightingController()))
    )

    response = client.post(
        "/api/lighting/per-key/apply",
        json={"edits": {"esc": "#00ff00"}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["keys"][0]["color"] == "#00ff00"
