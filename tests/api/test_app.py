from typing import cast

from fastapi.testclient import TestClient

from kreo_kontrol.api.app import create_app
from kreo_kontrol.device.bytech_lighting import LightingController
from kreo_kontrol.device.domains.lighting import (
    LightingState,
    LightingVerificationStatus,
)


class ConnectedLightingController:
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

    def apply_global_lighting(self, request):
        raise NotImplementedError

    def read_per_key_state(self):
        raise NotImplementedError

    def apply_per_key_colors_by_ui_key(self, edits):
        raise NotImplementedError

    def read_profiles(self):
        return {
            "supported": False,
            "active_profile": None,
            "available_profiles": [],
            "reason": "Bytech transport does not expose hardware profile slots",
        }


class WirelessLightingController:
    def configurable(self) -> bool:
        return True

    def transport_kind(self) -> str:
        return "wireless_receiver"

    def supports_profiles(self) -> bool:
        return False

    def is_connected(self) -> bool:
        return True

    def supported_devices(self) -> list[str]:
        return ["Kreo Swarm"]

    def read_state(self) -> LightingState:
        return LightingState(
            mode="static",
            brightness=80,
            per_key_rgb_supported=False,
            color=None,
            verification_status=LightingVerificationStatus.UNVERIFIED,
        )

    def apply_global_lighting(self, request):
        raise NotImplementedError

    def read_per_key_state(self):
        raise NotImplementedError

    def apply_per_key_colors_by_ui_key(self, edits):
        raise NotImplementedError

    def read_profiles(self):
        return {
            "supported": False,
            "active_profile": None,
            "available_profiles": [],
            "reason": "Bytech transport does not expose hardware profile slots",
        }


def test_health_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_serves_frontend_index(tmp_path) -> None:
    index_file = tmp_path / "index.html"
    index_file.write_text("<!doctype html><title>Kreo Kontrol</title>", encoding="utf-8")

    client = TestClient(create_app(frontend_dist=tmp_path))

    response = client.get("/")

    assert response.status_code == 200
    assert "Kreo Kontrol" in response.text


def test_device_endpoint_uses_live_controller_connection_state() -> None:
    client = TestClient(
        create_app(
            lighting_controller=cast(LightingController, ConnectedLightingController())
        )
    )

    response = client.get("/api/device")

    assert response.status_code == 200
    assert response.json() == {
        "connected": True,
        "configurable": True,
        "supported_devices": ["Kreo Swarm"],
        "supports_profiles": False,
        "transport_kind": "vendor_hid",
    }


def test_device_endpoint_reports_wireless_receiver_as_connected_but_basic() -> None:
    client = TestClient(
        create_app(
            lighting_controller=cast(LightingController, WirelessLightingController())
        )
    )

    response = client.get("/api/device")

    assert response.status_code == 200
    assert response.json() == {
        "connected": True,
        "configurable": True,
        "supported_devices": ["Kreo Swarm"],
        "supports_profiles": False,
        "transport_kind": "wireless_receiver",
    }


def test_profiles_endpoint_reports_saved_snapshot_storage(tmp_path) -> None:
    client = TestClient(
        create_app(
            lighting_controller=cast(LightingController, WirelessLightingController()),
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
