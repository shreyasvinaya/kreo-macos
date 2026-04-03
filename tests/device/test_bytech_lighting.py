from __future__ import annotations

from collections import deque
from typing import cast

from kreo_kontrol.api.app import create_app
from kreo_kontrol.device.bytech_lighting import (
    BytechLightingController,
    LightingController,
    build_demo_per_key_frame,
    build_per_key_frame,
    parse_key_records,
)
from kreo_kontrol.device.domains.lighting import (
    LightingApplyRequest,
    LightingState,
    LightingVerificationStatus,
)


def build_profile(mode: int = 1, brightness_level: int = 3, speed: int = 2) -> bytes:
    profile = bytearray(128)
    profile[9] = (mode >> 8) & 0xFF
    profile[10] = mode & 0xFF
    profile[30] = 0xFF
    profile[31] = 0xFF
    brightness_index = 32 + (mode * 2) - 2
    speed_index = brightness_index + 1
    profile[brightness_index] = brightness_level
    profile[speed_index] = speed << 4
    return bytes(profile)


def wrap_response(command: bytes, payload: bytes) -> bytes:
    return bytes([5, *command, 0, *payload])


def wrap_light_table_response(command: bytes, payload: bytes) -> bytes:
    return bytes([5, *command, *payload, 0, 0, 0])


def wrap_keys_response(command: bytes, payload: bytes) -> bytes:
    return bytes([5, *command, *payload])


class FakeHidDevice:
    def __init__(self, responses: list[bytes]) -> None:
        self.feature_reads: deque[bytes] = deque(responses)
        self.sent_reports: list[bytes] = []
        self.opened_paths: list[bytes] = []

    def open_path(self, path: bytes) -> None:
        self.opened_paths.append(path)

    def send_feature_report(self, data: bytes) -> int:
        self.sent_reports.append(data)
        return len(data)

    def get_feature_report(self, report_id: int, max_length: int) -> bytes:
        assert report_id == 6
        response = self.feature_reads.popleft()
        assert len(response) <= max_length
        return response

    def close(self) -> None:
        return None


class FakeLightingController:
    def read_state(self) -> LightingState:
        return LightingState(
            mode="static",
            brightness=80,
            per_key_rgb_supported=False,
            color="#ff0000",
            verification_status=LightingVerificationStatus.VERIFIED,
        )

    def apply_global_lighting(self, request: LightingApplyRequest) -> LightingState:
        return LightingState(
            mode=request.mode,
            brightness=request.brightness if request.brightness is not None else 80,
            per_key_rgb_supported=False,
            color=request.color,
            verification_status=LightingVerificationStatus.VERIFIED,
        )

    def read_per_key_state(self) -> dict[str, object]:
        return {
            "mode": "custom",
            "brightness": 25,
            "per_key_rgb_supported": True,
            "verification_status": "verified",
            "keys": [
                {"ui_key": "esc", "label": "Esc", "light_pos": 8, "color": "#ff0000"},
                {"ui_key": "space", "label": "Space", "light_pos": 43, "color": "#ffffff"},
            ],
        }

    def apply_per_key_colors_by_ui_key(self, edits: dict[str, str]) -> dict[str, object]:
        return {
            "mode": "custom",
            "brightness": 25,
            "per_key_rgb_supported": True,
            "verification_status": "verified",
            "keys": [
                {
                    "ui_key": "esc",
                    "label": "Esc",
                    "light_pos": 8,
                    "color": edits.get("esc", "#ff0000"),
                },
                {"ui_key": "space", "label": "Space", "light_pos": 43, "color": "#ffffff"},
            ],
        }


def test_read_profile_extracts_128_byte_payload() -> None:
    profile = build_profile()
    device = FakeHidDevice(
        responses=[wrap_response(b"\x84\x00\x00\x01\x00\x80", profile)]
    )
    controller = BytechLightingController(
        device_path=b"test-device",
        device_factory=lambda: device,
    )

    parsed = controller.read_profile()

    assert parsed == profile
    assert device.opened_paths == [b"test-device"]
    assert device.sent_reports[0][:7] == b"\x05\x84\x00\x00\x01\x00\x80"
    assert len(device.sent_reports[0]) == 520


def test_apply_global_lighting_writes_updated_profile_and_verifies_brightness() -> None:
    initial_profile = build_profile(mode=1, brightness_level=3)
    verified_profile = build_profile(mode=1, brightness_level=1)
    device = FakeHidDevice(
        responses=[
            wrap_response(b"\x84\x00\x00\x01\x00\x80", initial_profile),
            wrap_response(b"\x84\x00\x00\x01\x00\x80", verified_profile),
        ]
    )
    controller = BytechLightingController(
        device_path=b"test-device",
        device_factory=lambda: device,
    )

    state = controller.apply_global_lighting(
        LightingApplyRequest(mode="static", brightness=35)
    )

    assert state.mode == "static"
    assert state.brightness == 35
    assert state.verification_status == LightingVerificationStatus.VERIFIED
    assert device.sent_reports[1][:8] == b"\x05\x04\x00\x00\x01\x00\x80\x00"
    written_profile = device.sent_reports[1][8 : 8 + 128]
    assert written_profile[32] == 1


def test_apply_global_lighting_updates_static_color_group() -> None:
    profile = build_profile(mode=1, brightness_level=3)
    verified_profile = build_profile(mode=1, brightness_level=2)
    light_table = bytes([0] * 480)
    verified_light_table = bytearray(light_table)
    verified_light_table[21] = 0x12
    verified_light_table[22] = 0x34
    verified_light_table[23] = 0x56
    device = FakeHidDevice(
        responses=[
            wrap_response(b"\x84\x00\x00\x01\x00\x80", profile),
            wrap_light_table_response(b"\x8a\x00\x00\x01\x00\xe3\x01", light_table),
            wrap_response(b"\x84\x00\x00\x01\x00\x80", verified_profile),
            wrap_light_table_response(
                b"\x8a\x00\x00\x01\x00\xe3\x01", bytes(verified_light_table)
            ),
        ]
    )
    controller = BytechLightingController(
        device_path=b"test-device",
        device_factory=lambda: device,
    )

    state = controller.apply_global_lighting(
        LightingApplyRequest(mode="static", brightness=40, color="#123456")
    )

    assert state.color == "#123456"
    assert state.verification_status == LightingVerificationStatus.VERIFIED
    assert device.sent_reports[3][:8] == b"\x05\x0a\x00\x00\x00\x00\x00\x02"
    written_table = device.sent_reports[3][8 : 8 + 480]
    assert written_table[21:24] == b"\x12\x34\x56"


def test_lighting_apply_endpoint_uses_injected_controller() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(
        create_app(lighting_controller=cast(LightingController, FakeLightingController()))
    )

    response = client.post(
        "/api/lighting/apply",
        json={"mode": "static", "brightness": 35, "color": "#123456"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["verification_status"] == "verified"
    assert payload["color"] == "#123456"


def test_per_key_lighting_endpoint_uses_injected_controller() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(
        create_app(lighting_controller=cast(LightingController, FakeLightingController()))
    )

    response = client.get("/api/lighting/per-key")

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "custom"
    assert payload["keys"][0]["ui_key"] == "esc"
    assert payload["keys"][0]["color"] == "#ff0000"


def test_per_key_lighting_apply_endpoint_uses_injected_controller() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(
        create_app(lighting_controller=cast(LightingController, FakeLightingController()))
    )

    response = client.post(
        "/api/lighting/per-key/apply",
        json={"edits": {"esc": "#00ff00"}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["keys"][0]["color"] == "#00ff00"


def test_build_demo_per_key_frame_splits_leds_into_three_color_bands() -> None:
    frame = build_demo_per_key_frame()

    assert len(frame) == 378
    assert frame[0] == 0xFF
    assert frame[41] == 0xFF
    assert frame[42] == 0x00
    assert frame[126] == 0x00
    assert frame[126 + 42] == 0xFF
    assert frame[252 + 84] == 0xFF
    assert frame[252 + 41] == 0x00


def test_apply_demo_per_key_lighting_switches_to_custom_mode_and_writes_frame() -> None:
    profile = build_profile(mode=1, brightness_level=3)
    device = FakeHidDevice(
        responses=[
            wrap_response(b"\x84\x00\x00\x01\x00\x80", profile),
            wrap_response(b"\x86\x00\x00\x01\x00\x7a\x01", b"\x00"),
        ]
    )
    controller = BytechLightingController(
        device_path=b"test-device",
        device_factory=lambda: device,
    )

    state = controller.apply_demo_per_key_lighting()

    assert state.mode == "custom"
    assert state.per_key_rgb_supported is True
    assert state.verification_status == LightingVerificationStatus.UNVERIFIED
    assert device.sent_reports[1][:8] == b"\x05\x04\x00\x00\x01\x00\x80\x00"
    written_profile = device.sent_reports[1][8 : 8 + 128]
    assert written_profile[9] == 0x01
    assert written_profile[10] == 0x15
    assert device.sent_reports[2][:8] == b"\x05\x86\x00\x00\x01\x00\x7a\x01"
    assert device.sent_reports[3][:8] == b"\x05\x06\x00\x00\x01\x00\x7a\x01"
    written_frame = device.sent_reports[3][8 : 8 + 378]
    assert len(written_frame) == 378


def test_parse_key_records_sets_positions_and_light_positions() -> None:
    payload = bytes(
        [
            0x00,
            0x00,
            0x00,
            0x29,
            0x00,
            0x00,
            0x00,
            0x35,
            0x00,
            0x00,
            0x00,
            0x2B,
        ]
    )

    records = parse_key_records(payload)

    assert [record.value for record in records] == [41, 53, 43]
    assert [record.pos for record in records] == [8, 12, 16]
    assert [record.light_pos for record in records] == [8, 9, 10]


def test_read_per_key_state_maps_vendor_modifier_codes() -> None:
    profile = build_profile(mode=1, brightness_level=2)
    custom_profile = bytearray(profile)
    custom_profile[9] = 0x01
    custom_profile[10] = 0x15
    keys_payload = bytes(
        [
            0x00,
            0x02,
            0x00,
            0x00,
            0x00,
            0x01,
            0x00,
            0x00,
            0x00,
            0x08,
            0x00,
            0x00,
            0x0D,
            0x00,
            0x00,
            0x00,
            0x00,
            0x10,
            0x00,
            0x00,
            0x00,
            0x20,
            0x00,
            0x00,
        ]
    )
    custom_frame = bytearray([0] * 378)
    device = FakeHidDevice(
        responses=[
            wrap_response(b"\x84\x00\x00\x01\x00\x80", bytes(custom_profile)),
            wrap_keys_response(b"\x83\x00\x00\x01\x00\xf8\x01", keys_payload),
            wrap_keys_response(b"\x86\x00\x00\x01\x00\x7a\x01", bytes(custom_frame)),
        ]
    )
    controller = BytechLightingController(
        device_path=b"test-device",
        device_factory=lambda: device,
    )

    state = controller.read_per_key_state()

    assert [entry["ui_key"] for entry in state["keys"]] == [
        "left_shift",
        "left_ctrl",
        "left_cmd",
        "fn",
        "right_ctrl",
        "right_shift",
    ]


def test_build_per_key_frame_writes_requested_led_colors_only() -> None:
    frame = build_per_key_frame(
        {
            8: (0xFF, 0x00, 0x00),
            9: (0x00, 0xFF, 0x00),
            10: (0x00, 0x00, 0xFF),
        }
    )

    assert len(frame) == 378
    assert frame[0] == 0xFF
    assert frame[1] == 0x00
    assert frame[2] == 0x00
    assert frame[126] == 0x00
    assert frame[127] == 0xFF
    assert frame[128] == 0x00
    assert frame[252] == 0x00
    assert frame[253] == 0x00
    assert frame[254] == 0xFF


def test_read_key_records_decodes_keyboard_light_positions() -> None:
    payload = bytes(
        [
            0x00,
            0x00,
            0x00,
            0x29,
            0x00,
            0x00,
            0x00,
            0x35,
            0x00,
            0x00,
            0x00,
            0x2B,
        ]
    )
    device = FakeHidDevice(
        responses=[wrap_keys_response(b"\x83\x00\x00\x01\x00\xf8\x01", payload)]
    )
    controller = BytechLightingController(
        device_path=b"test-device",
        device_factory=lambda: device,
    )

    records = controller.read_key_records()

    assert [record.light_pos for record in records] == [8, 9, 10]


def test_apply_per_key_colors_writes_targeted_custom_frame() -> None:
    profile = build_profile(mode=1, brightness_level=2)
    device = FakeHidDevice(
        responses=[
            wrap_response(b"\x84\x00\x00\x01\x00\x80", profile),
            wrap_response(b"\x86\x00\x00\x01\x00\x7a\x01", b"\x00"),
        ]
    )
    controller = BytechLightingController(
        device_path=b"test-device",
        device_factory=lambda: device,
    )

    state = controller.apply_per_key_colors(
        {
            8: (0xFF, 0x00, 0x00),
            50: (0x00, 0xFF, 0x00),
            80: (0x00, 0x00, 0xFF),
        }
    )

    assert state.mode == "custom"
    assert state.per_key_rgb_supported is True
    assert state.verification_status == LightingVerificationStatus.UNVERIFIED
    assert device.sent_reports[2][:8] == b"\x05\x86\x00\x00\x01\x00\x7a\x01"
    assert device.sent_reports[3][:8] == b"\x05\x06\x00\x00\x01\x00\x7a\x01"
    written_frame = device.sent_reports[3][8 : 8 + 378]
    assert written_frame[0] == 0xFF
    assert written_frame[126 + (50 - 8)] == 0xFF
    assert written_frame[252 + (80 - 8)] == 0xFF


def test_apply_per_key_colors_uses_static_brightness_when_profile_is_already_custom() -> None:
    profile = build_profile(mode=1, brightness_level=2)
    custom_profile = bytearray(profile)
    custom_profile[9] = 0x01
    custom_profile[10] = 0x15
    device = FakeHidDevice(
        responses=[
            wrap_response(b"\x84\x00\x00\x01\x00\x80", bytes(custom_profile)),
            wrap_response(b"\x86\x00\x00\x01\x00\x7a\x01", b"\x00"),
        ]
    )
    controller = BytechLightingController(
        device_path=b"test-device",
        device_factory=lambda: device,
    )

    state = controller.apply_per_key_colors({8: (0xFF, 0x00, 0x00)})

    assert state.brightness == 50
    assert state.mode == "custom"


def test_read_per_key_state_reads_custom_frame_colors() -> None:
    profile = build_profile(mode=1, brightness_level=2)
    custom_profile = bytearray(profile)
    custom_profile[9] = 0x01
    custom_profile[10] = 0x15
    keys_payload = bytes([0x00, 0x00, 0x00, 0x29, 0x00, 0x00, 0x00, 0x2c])
    custom_frame = bytearray([0] * 378)
    custom_frame[0] = 0x12
    custom_frame[1] = 0xAB
    custom_frame[126] = 0x34
    custom_frame[127] = 0xCD
    custom_frame[252] = 0x56
    custom_frame[253] = 0xEF
    device = FakeHidDevice(
        responses=[
            wrap_response(b"\x84\x00\x00\x01\x00\x80", bytes(custom_profile)),
            wrap_keys_response(b"\x83\x00\x00\x01\x00\xf8\x01", keys_payload),
            wrap_keys_response(b"\x86\x00\x00\x01\x00\x7a\x01", bytes(custom_frame)),
        ]
    )
    controller = BytechLightingController(
        device_path=b"test-device",
        device_factory=lambda: device,
    )

    state = controller.read_per_key_state()

    assert state["mode"] == "custom"
    assert state["keys"] == [
        {"ui_key": "esc", "label": "Esc", "light_pos": 8, "color": "#123456"},
        {"ui_key": "space", "label": "Space", "light_pos": 9, "color": "#abcdef"},
    ]


def test_apply_per_key_colors_by_ui_key_maps_keys_and_updates_frame() -> None:
    profile = build_profile(mode=1, brightness_level=2)
    custom_profile = bytearray(profile)
    custom_profile[9] = 0x01
    custom_profile[10] = 0x15
    keys_payload = bytes([0x00, 0x00, 0x00, 0x29, 0x00, 0x00, 0x00, 0x2c])
    custom_frame = bytearray([0] * 378)
    custom_frame[0] = 0x00
    custom_frame[1] = 0x40
    custom_frame[126] = 0xFF
    custom_frame[127] = 0x50
    custom_frame[252] = 0x00
    custom_frame[253] = 0x60
    device = FakeHidDevice(
        responses=[
            wrap_response(b"\x84\x00\x00\x01\x00\x80", profile),
            wrap_keys_response(b"\x83\x00\x00\x01\x00\xf8\x01", keys_payload),
            wrap_keys_response(b"\x8a\x00\x00\x01\x00\xe3\x01", bytes([0] * 480)),
            wrap_response(b"\x86\x00\x00\x01\x00\x7a\x01", b"\x00"),
            wrap_response(b"\x84\x00\x00\x01\x00\x80", bytes(custom_profile)),
            wrap_keys_response(b"\x83\x00\x00\x01\x00\xf8\x01", keys_payload),
            wrap_keys_response(b"\x86\x00\x00\x01\x00\x7a\x01", bytes(custom_frame)),
        ]
    )
    controller = BytechLightingController(
        device_path=b"test-device",
        device_factory=lambda: device,
    )

    state = controller.apply_per_key_colors_by_ui_key({"esc": "#00ff00"})

    assert state["keys"][0]["ui_key"] == "esc"
    assert state["keys"][0]["color"] == "#00ff00"
    assert device.sent_reports[4][:8] == b"\x05\x86\x00\x00\x01\x00\x7a\x01"
    assert device.sent_reports[5][:8] == b"\x05\x06\x00\x00\x01\x00\x7a\x01"
