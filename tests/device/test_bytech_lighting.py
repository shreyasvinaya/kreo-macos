from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import cast

import pytest

from kreo_kontrol.api.app import create_app
from kreo_kontrol.device.bytech_lighting import (
    BytechLightingController,
    LightingController,
    LightingHardwareUnavailableError,
    LightingProtocolError,
    build_demo_per_key_frame,
    build_keymap_action_catalog,
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


def build_keymap_payload(values_by_pos: dict[int, int]) -> bytes:
    payload = bytearray(126 * 4)
    for pos, value in values_by_pos.items():
        slot = (pos - 8) // 4
        offset = slot * 4
        payload[offset] = (value >> 24) & 0xFF
        payload[offset + 1] = (value >> 16) & 0xFF
        payload[offset + 2] = (value >> 8) & 0xFF
        payload[offset + 3] = value & 0xFF
    return bytes(payload)


def build_macro_blob(groups: list[bytes]) -> bytes:
    headers = bytearray()
    payload = bytearray()
    offset = len(groups) * 4
    for group in groups:
        headers.extend([offset, 0, len(group), 0])
        payload.extend(group)
        offset += len(group)
    blob = bytes([*headers, *payload])
    return bytes([*blob, *([0] * (512 - len(blob)))])


def build_macro_group(
    name: str,
    actions: list[tuple[int, int, int]],
) -> bytes:
    encoded_name = name.encode("utf-8")
    payload = bytearray([len(encoded_name), *encoded_name])
    for event_type, delay_ms, keycode in actions:
        payload.extend(
            [
                ((event_type & 0x0F) << 4) | ((delay_ms >> 16) & 0x0F),
                (delay_ms >> 8) & 0xFF,
                delay_ms & 0xFF,
                keycode & 0xFF,
            ]
        )
    return bytes(payload)


def build_receiver_packets(command: int, payload: bytes) -> list[bytes]:
    packets: list[bytes] = []
    chunk_size = 14
    total_packets = max(1, (len(payload) + chunk_size - 1) // chunk_size)
    for index in range(total_packets):
        start = index * chunk_size
        chunk = payload[start : start + chunk_size]
        padded_chunk = bytes([*chunk, *([0] * (chunk_size - len(chunk)))])
        packets.append(
            bytes(
                [
                    0x13,
                    command,
                    total_packets,
                    index,
                    len(chunk) if len(chunk) > 0 else 2,
                    *padded_chunk,
                    0,
                ]
            )
        )
    return packets


def load_swarm75_led_map() -> list[dict[str, object]]:
    led_map_path = (
        Path(__file__).resolve().parents[2]
        / "kreo_website_dump"
        / "kontrol.kreo-tech.com"
        / "assets"
        / "keyboard"
        / "swarm75"
        / "meta"
        / "led-map.json"
    )
    return json.loads(led_map_path.read_text())["keys"]


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

    def write(self, data: bytes) -> int:
        raise AssertionError("wired path should not use standard HID writes")

    def read(self, max_length: int, timeout_ms: int = 0) -> bytes:
        raise AssertionError("wired path should not use standard HID reads")

    def close(self) -> None:
        return None


class FakeWirelessHidDevice:
    def __init__(self, responses: list[bytes]) -> None:
        self.reads: deque[bytes] = deque(responses)
        self.writes: list[bytes] = []
        self.opened_paths: list[bytes] = []

    def open_path(self, path: bytes) -> None:
        self.opened_paths.append(path)

    def send_feature_report(self, data: bytes) -> int:
        raise AssertionError("wireless path should not use feature reports")

    def get_feature_report(self, report_id: int, max_length: int) -> bytes:
        raise AssertionError("wireless path should not use feature reports")

    def write(self, data: bytes) -> int:
        self.writes.append(data)
        return len(data)

    def read(self, max_length: int, timeout_ms: int = 0) -> bytes:
        if not self.reads:
            return b""
        response = self.reads.popleft()
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


def test_apply_global_lighting_supports_effect_presets_without_color() -> None:
    initial_profile = build_profile(mode=1, brightness_level=3)
    verified_profile = build_profile(mode=4, brightness_level=2)
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
        LightingApplyRequest(mode="wave", brightness=50)
    )

    assert state.mode == "wave"
    assert state.brightness == 50
    assert state.verification_status == LightingVerificationStatus.VERIFIED
    written_profile = device.sent_reports[1][8 : 8 + 128]
    assert written_profile[9:11] == b"\x00\x04"


def test_receiver_session_reports_wireless_transport_when_vendor_hid_is_missing(
) -> None:
    controller = BytechLightingController(
        path_provider=lambda: (_ for _ in ()).throw(LightingHardwareUnavailableError()),
        receiver_path_provider=lambda: b"wireless-device",
    )

    assert controller.transport_kind() == "wireless_receiver"


def test_receiver_session_is_marked_configurable() -> None:
    controller = BytechLightingController(
        path_provider=lambda: (_ for _ in ()).throw(LightingHardwareUnavailableError()),
        receiver_path_provider=lambda: b"wireless-device",
    )

    assert controller.configurable() is True


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


def test_read_keymap_decodes_base_and_fn_assignments() -> None:
    base_payload = build_keymap_payload(
        {
            8: 41,
            220: 0x00400000,
        }
    )
    fn_payload = build_keymap_payload(
        {
            8: 58,
            220: 0,
        }
    )
    device = FakeHidDevice(
        responses=[
            wrap_keys_response(b"\x83\x00\x00\x01\x00\xf8\x01", base_payload),
            wrap_keys_response(b"\x83\x00\x01\x01\x00\xf8\x01", fn_payload),
        ]
    )
    controller = BytechLightingController(
        device_path=b"test-device",
        device_factory=lambda: device,
    )

    payload = controller.read_keymap()

    esc = next(
        assignment
        for assignment in payload["assignments"]
        if assignment["ui_key"] == "esc"
    )
    right_opt = next(
        assignment
        for assignment in payload["assignments"]
        if assignment["ui_key"] == "right_opt"
    )
    esc_base_action = cast(dict[str, object], esc["base_action"])
    esc_fn_action = cast(dict[str, object], esc["fn_action"])
    right_opt_base_action = cast(dict[str, object], right_opt["base_action"])
    assert esc_base_action["label"] == "Esc"
    assert esc_fn_action["label"] == "F1"
    assert right_opt_base_action["raw_value"] == 0x00400000


def test_apply_keymap_rejects_combined_base_and_fn_layer_edits_until_verified() -> None:
    base_before = build_keymap_payload({220: 0x00400000})
    fn_before = build_keymap_payload({220: 0})
    device = FakeHidDevice(
        responses=[
            wrap_keys_response(b"\x83\x00\x00\x01\x00\xf8\x01", base_before),
            wrap_keys_response(b"\x83\x00\x01\x01\x00\xf8\x01", fn_before),
        ]
    )
    controller = BytechLightingController(
        device_path=b"test-device",
        device_factory=lambda: device,
    )

    with pytest.raises(LightingProtocolError, match="FN-layer remapping is not verified"):
        controller.apply_keymap(
            {
                "right_opt": {
                    "base_raw_value": 0x00040000,
                    "fn_raw_value": 0x020000CD,
                }
            }
        )

    assert device.sent_reports == []


def test_apply_keymap_with_base_only_edit_writes_base_layer_only() -> None:
    base_before = build_keymap_payload({220: 0x00400000})
    fn_before = build_keymap_payload({220: 0x00400000})
    base_after = build_keymap_payload({220: 0x00800000})
    fn_after = build_keymap_payload({220: 0x00400000})
    device = FakeHidDevice(
        responses=[
            wrap_keys_response(b"\x83\x00\x00\x01\x00\xf8\x01", base_before),
            wrap_keys_response(b"\x83\x00\x01\x01\x00\xf8\x01", fn_before),
            wrap_keys_response(b"\x83\x00\x00\x01\x00\xf8\x01", base_after),
            wrap_keys_response(b"\x83\x00\x01\x01\x00\xf8\x01", fn_after),
        ]
    )
    controller = BytechLightingController(
        device_path=b"test-device",
        device_factory=lambda: device,
    )

    payload = controller.apply_keymap({"right_opt": {"base_raw_value": 0x00800000}})

    right_opt = next(
        assignment
        for assignment in payload["assignments"]
        if assignment["ui_key"] == "right_opt"
    )
    right_opt_base_action = cast(dict[str, object], right_opt["base_action"])
    assert right_opt_base_action["raw_value"] == 0x00800000
    assert device.sent_reports[2][:8] == b"\x05\x03\x00\x00\x01\x00\xf8\x01"
    assert all(report[:8] != b"\x05\x03\x00\x01\x01\x00\xf8\x01" for report in device.sent_reports)


def test_apply_keymap_rejects_fn_layer_edits_until_protocol_is_verified() -> None:
    device = FakeHidDevice(responses=[])
    controller = BytechLightingController(
        device_path=b"test-device",
        device_factory=lambda: device,
    )

    with pytest.raises(LightingProtocolError, match="FN-layer remapping is not verified"):
        controller.apply_keymap({"right_opt": {"fn_raw_value": 0x020000CD}})


def test_keymap_action_catalog_distinguishes_left_and_right_modifiers() -> None:
    catalog = build_keymap_action_catalog()
    entries_by_action_id = {entry.action_id: entry for entry in catalog}
    modifier_values = {
        entry.raw_value
        for entry in catalog
        if entry.category == "Modifiers" and entry.action_id.startswith("basic:")
    }

    assert entries_by_action_id["basic:left_ctrl"].label == "Control Left"
    assert entries_by_action_id["basic:right_ctrl"].label == "Control Right"
    assert entries_by_action_id["basic:left_opt"].label == "Option Left"
    assert entries_by_action_id["basic:right_opt"].label == "Option Right"
    assert entries_by_action_id["basic:left_cmd"].label == "Command Left"
    assert entries_by_action_id["basic:right_cmd"].label == "Command Right"
    assert entries_by_action_id["basic:right_cmd"].raw_value == 0x00800000
    assert 0xE7 not in modifier_values
    assert 0xE6 not in modifier_values


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


def test_read_per_key_state_reads_wireless_custom_frame_colors() -> None:
    custom_profile = bytearray(build_profile(mode=1, brightness_level=2))
    custom_profile[9] = 0x01
    custom_profile[10] = 0x15
    receiver_frame = bytearray([0] * 378)
    receiver_frame[0:3] = bytes([0x12, 0x34, 0x56])
    receiver_frame[12 * 3 : (12 * 3) + 3] = bytes([0xAB, 0xCD, 0xEF])
    device = FakeWirelessHidDevice(
        responses=[
            *build_receiver_packets(68, bytes(custom_profile)),
            *build_receiver_packets(2, bytes(receiver_frame)),
        ]
    )
    controller = BytechLightingController(
        path_provider=lambda: (_ for _ in ()).throw(LightingHardwareUnavailableError()),
        receiver_path_provider=lambda: b"wireless-device",
        device_factory=lambda: device,
    )

    state = controller.read_per_key_state()

    colors_by_key = {entry["ui_key"]: entry["color"] for entry in state["keys"]}
    assert state["mode"] == "custom"
    assert state["per_key_rgb_supported"] is True
    assert colors_by_key["esc"] == "#123456"
    assert colors_by_key["f1"] == "#abcdef"


def test_apply_per_key_colors_by_ui_key_writes_wireless_custom_frame() -> None:
    custom_profile = bytearray(build_profile(mode=1, brightness_level=2))
    custom_profile[9] = 0x01
    custom_profile[10] = 0x15
    receiver_frame = bytearray([0] * 378)
    device = FakeWirelessHidDevice(
        responses=[
            *build_receiver_packets(68, bytes(custom_profile)),
            *build_receiver_packets(2, bytes(receiver_frame)),
        ]
    )
    controller = BytechLightingController(
        path_provider=lambda: (_ for _ in ()).throw(LightingHardwareUnavailableError()),
        receiver_path_provider=lambda: b"wireless-device",
        device_factory=lambda: device,
    )

    state = controller.apply_per_key_colors_by_ui_key({"esc": "#00ff00"})

    assert any(write[1] == 66 for write in device.writes)
    assert any(write[1] == 2 for write in device.writes)
    colors_by_key = {entry["ui_key"]: entry["color"] for entry in state["keys"]}
    assert colors_by_key["esc"] == "#00ff00"


def test_apply_global_lighting_writes_wireless_profile_and_light_table() -> None:
    profile = build_profile(mode=1, brightness_level=3)
    light_table = bytearray([0] * 480)
    verified_profile = build_profile(mode=1, brightness_level=1)
    verified_light_table = bytearray(light_table)
    verified_light_table[21:24] = bytes([0x12, 0x34, 0x56])
    device = FakeWirelessHidDevice(
        responses=[
            *build_receiver_packets(68, bytes(profile)),
            *build_receiver_packets(73, bytes(light_table)),
            *build_receiver_packets(68, bytes(verified_profile)),
            *build_receiver_packets(73, bytes(verified_light_table)),
        ]
    )
    controller = BytechLightingController(
        path_provider=lambda: (_ for _ in ()).throw(LightingHardwareUnavailableError()),
        receiver_path_provider=lambda: b"wireless-device",
        device_factory=lambda: device,
    )

    state = controller.apply_global_lighting(
        LightingApplyRequest(mode="static", brightness=25, color="#123456")
    )

    assert state.verification_status == LightingVerificationStatus.VERIFIED
    assert any(write[1] == 4 for write in device.writes)
    assert any(write[1] == 9 for write in device.writes)


def test_apply_global_lighting_supports_wireless_effect_presets_without_color() -> None:
    initial_profile = build_profile(mode=1, brightness_level=3)
    verified_profile = build_profile(mode=7, brightness_level=2)
    device = FakeWirelessHidDevice(
        responses=[
            *build_receiver_packets(68, bytes(initial_profile)),
            *build_receiver_packets(68, bytes(verified_profile)),
        ]
    )
    controller = BytechLightingController(
        path_provider=lambda: (_ for _ in ()).throw(LightingHardwareUnavailableError()),
        receiver_path_provider=lambda: b"wireless-device",
        device_factory=lambda: device,
    )

    state = controller.apply_global_lighting(
        LightingApplyRequest(mode="snake", brightness=50)
    )

    assert state.mode == "snake"
    assert state.verification_status == LightingVerificationStatus.VERIFIED
    assert any(write[1] == 4 for write in device.writes)


def test_read_macros_decodes_named_slot_and_bound_key() -> None:
    macro_blob = build_macro_blob(
        [
            build_macro_group(
                "Copy Burst",
                [
                    (0, 12, 6),
                    (8, 24, 6),
                ],
            )
        ]
    )
    base_keymap = build_keymap_payload(
        {
            220: 0x03010300,
        }
    )
    device = FakeHidDevice(
        responses=[
            wrap_keys_response(b"\x83\x00\x00\x01\x00\xf8\x01", base_keymap),
            wrap_keys_response(b"\x85\x00\x00\x01\x00\x00\x02", macro_blob),
        ]
    )
    controller = BytechLightingController(
        device_path=b"wired-macro-device",
        device_factory=lambda: device,
    )

    payload = controller.read_macros()

    assert payload["supported"] is True
    assert payload["next_slot_id"] == 1
    assert payload["slots"][0]["slot_id"] == 0
    assert payload["slots"][0]["name"] == "Copy Burst"
    assert payload["slots"][0]["execution_type"] == "FIXED_COUNT"
    assert payload["slots"][0]["cycle_times"] == 3
    assert payload["slots"][0]["bound_ui_keys"] == ["right_opt"]
    assert payload["slots"][0]["actions"] == [
        {"key": "c", "event_type": "press", "delay_ms": 12},
        {"key": "c", "event_type": "release", "delay_ms": 24},
    ]


def test_apply_macro_appends_slot_and_updates_bound_key() -> None:
    initial_blob = build_macro_blob([])
    initial_keymap = build_keymap_payload({})
    updated_blob = build_macro_blob(
        [
            build_macro_group(
                "Launch Focus",
                [
                    (0, 10, 20),
                    (8, 20, 20),
                ],
            )
        ]
    )
    updated_keymap = build_keymap_payload({220: 0x03010200})
    device = FakeHidDevice(
        responses=[
            wrap_keys_response(b"\x85\x00\x00\x01\x00\x00\x02", initial_blob),
            wrap_keys_response(b"\x83\x00\x00\x01\x00\xf8\x01", initial_keymap),
            wrap_keys_response(b"\x83\x00\x00\x01\x00\xf8\x01", updated_keymap),
            wrap_keys_response(b"\x85\x00\x00\x01\x00\x00\x02", updated_blob),
        ]
    )
    controller = BytechLightingController(
        device_path=b"wired-macro-device",
        device_factory=lambda: device,
    )

    payload = controller.apply_macro(
        slot_id=0,
        request={
            "name": "Launch Focus",
            "bound_ui_key": "right_opt",
            "execution_type": "UNTIL_ANY_PRESSED",
            "cycle_times": 1,
            "actions": [
                {"key": "q", "event_type": "press", "delay_ms": 10},
                {"key": "q", "event_type": "release", "delay_ms": 20},
            ],
        },
    )

    macro_write = device.sent_reports[1]
    keymap_write = device.sent_reports[3]

    assert macro_write[:8] == b"\x05\x05\x00\x00\x01\x00\x00\x02"
    assert keymap_write[:8] == b"\x05\x03\x00\x00\x01\x00\xf8\x01"
    assert payload["slots"][0]["name"] == "Launch Focus"
    assert payload["slots"][0]["bound_ui_keys"] == ["right_opt"]
