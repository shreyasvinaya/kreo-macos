from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from typing import Protocol, TypedDict, cast

from kreo_kontrol.device.domains.lighting import (
    LightingApplyRequest,
    LightingState,
    LightingVerificationStatus,
)

KREO_VENDOR_ID = 0x258A
KREO_PRODUCT_ID = 0x010C
KREO_USAGE_PAGE = 0xFF00
KREO_USAGE = 0x01

WRITE_REPORT_ID = 0x05
READ_REPORT_ID = 0x06
FEATURE_REPORT_SIZE = 520
PROFILE_SIZE = 128
LIGHT_TABLE_SIZE = 480
LIGHT_TABLE_RESPONSE_SIZE = 520

PROFILE_READ_COMMAND = b"\x84\x00\x00\x01\x00\x80"
PROFILE_WRITE_COMMAND = b"\x04\x00\x00\x01\x00\x80\x00"
LIGHT_TABLE_READ_COMMAND = b"\x8a\x00\x00\x01\x00\xe3\x01"
LIGHT_TABLE_WRITE_COMMAND = b"\x0a\x00\x00\x00\x00\x00\x02"
KEYS_READ_COMMAND = b"\x83\x00\x00\x01\x00\xf8\x01"
CUSTOM_LIGHT_PREPARE_COMMAND = b"\x86\x00\x00\x01\x00\x7a\x01"
CUSTOM_LIGHT_WRITE_COMMAND = b"\x06\x00\x00\x01\x00\x7a\x01"

STATIC_MODE_ID = 1
CUSTOM_MODE_ID = 277
SNOW_MODE_ID = 19
DEVICE_BRIGHTNESS_MAX = 4
CUSTOM_LIGHT_LED_COUNT = 126
CUSTOM_LIGHT_FRAME_SIZE = CUSTOM_LIGHT_LED_COUNT * 3
CUSTOM_LIGHT_RESPONSE_SIZE = 8 + CUSTOM_LIGHT_FRAME_SIZE
DEFAULT_KEYCAP_COLOR = "#273240"

HID_VALUE_TO_UI_KEY: dict[int, tuple[str, str]] = {
    4: ("a", "A"),
    5: ("b", "B"),
    6: ("c", "C"),
    7: ("d", "D"),
    8: ("e", "E"),
    9: ("f", "F"),
    10: ("g", "G"),
    11: ("h", "H"),
    12: ("i", "I"),
    13: ("j", "J"),
    14: ("k", "K"),
    15: ("l", "L"),
    16: ("m", "M"),
    17: ("n", "N"),
    18: ("o", "O"),
    19: ("p", "P"),
    20: ("q", "Q"),
    21: ("r", "R"),
    22: ("s", "S"),
    23: ("t", "T"),
    24: ("u", "U"),
    25: ("v", "V"),
    26: ("w", "W"),
    27: ("x", "X"),
    28: ("y", "Y"),
    29: ("z", "Z"),
    30: ("1", "1"),
    31: ("2", "2"),
    32: ("3", "3"),
    33: ("4", "4"),
    34: ("5", "5"),
    35: ("6", "6"),
    36: ("7", "7"),
    37: ("8", "8"),
    38: ("9", "9"),
    39: ("0", "0"),
    40: ("enter", "Enter"),
    41: ("esc", "Esc"),
    42: ("backspace", "Backspace"),
    43: ("tab", "Tab"),
    44: ("space", "Space"),
    45: ("-", "-"),
    46: ("=", "="),
    47: ("[", "["),
    48: ("]", "]"),
    49: ("\\", "\\"),
    51: (";", ";"),
    52: ("'", "'"),
    53: ("`", "`"),
    54: (",", ","),
    55: (".", "."),
    56: ("/", "/"),
    57: ("caps", "Caps"),
    58: ("f1", "F1"),
    59: ("f2", "F2"),
    60: ("f3", "F3"),
    61: ("f4", "F4"),
    62: ("f5", "F5"),
    63: ("f6", "F6"),
    64: ("f7", "F7"),
    65: ("f8", "F8"),
    66: ("f9", "F9"),
    67: ("f10", "F10"),
    68: ("f11", "F11"),
    69: ("f12", "F12"),
    70: ("print_screen", "PrtSc"),
    75: ("page_up", "PgUp"),
    76: ("delete", "Del"),
    77: ("end", "End"),
    78: ("page_down", "PgDn"),
    79: ("right", "Right"),
    80: ("left", "Left"),
    81: ("down", "Down"),
    82: ("up", "Up"),
    224: ("left_ctrl", "Control"),
    225: ("left_shift", "Shift"),
    226: ("left_opt", "Command"),
    227: ("left_cmd", "Option"),
    228: ("right_ctrl", "Control"),
    229: ("right_shift", "Shift"),
    230: ("right_opt", "Command"),
    231: ("right_cmd", "Option"),
    0x00010000: ("left_ctrl", "Control"),
    0x00020000: ("left_shift", "Shift"),
    0x00040000: ("left_opt", "Command"),
    0x00080000: ("left_cmd", "Option"),
    0x00100000: ("right_ctrl", "Control"),
    0x00200000: ("right_shift", "Shift"),
    0x00400000: ("right_opt", "Command"),
    0x0D000000: ("fn", "Fn"),
}


class HidFeatureDevice(Protocol):
    def open_path(self, path: bytes) -> None:
        ...

    def send_feature_report(self, data: bytes) -> int:
        ...

    def get_feature_report(self, report_id: int, max_length: int) -> bytes:
        ...

    def close(self) -> None:
        ...


class LightingController(Protocol):
    def is_connected(self) -> bool:
        ...

    def supported_devices(self) -> list[str]:
        ...

    def read_state(self) -> LightingState:
        ...

    def apply_global_lighting(self, request: LightingApplyRequest) -> LightingState:
        ...

    def read_per_key_state(self) -> PerKeyLightingPayload:
        ...

    def apply_per_key_colors_by_ui_key(self, edits: dict[str, str]) -> PerKeyLightingPayload:
        ...


class LightingHardwareUnavailableError(RuntimeError):
    pass


class LightingProtocolError(RuntimeError):
    pass


@dataclass(frozen=True)
class BytechKeyRecord:
    value: int
    pos: int
    effect_pos: int
    light_pos: int


class PerKeyLightingEntryPayload(TypedDict):
    ui_key: str
    label: str
    light_pos: int
    color: str


class PerKeyLightingPayload(TypedDict):
    mode: str
    brightness: int
    per_key_rgb_supported: bool
    verification_status: str
    keys: list[PerKeyLightingEntryPayload]


class StubLightingController:
    def is_connected(self) -> bool:
        return False

    def supported_devices(self) -> list[str]:
        return []

    def read_state(self) -> LightingState:
        return LightingState(
            mode="static",
            brightness=80,
            per_key_rgb_supported=False,
            color=None,
            verification_status=LightingVerificationStatus.UNVERIFIED,
        )

    def apply_global_lighting(self, request: LightingApplyRequest) -> LightingState:
        return LightingState(
            mode=request.mode,
            brightness=request.brightness if request.brightness is not None else 80,
            per_key_rgb_supported=False,
            color=request.color,
            verification_status=LightingVerificationStatus.UNVERIFIED,
        )

    def read_per_key_state(self) -> PerKeyLightingPayload:
        return {
            "mode": "custom",
            "brightness": 80,
            "per_key_rgb_supported": False,
            "verification_status": "unverified",
            "keys": [
                {"ui_key": "esc", "label": "Esc", "light_pos": 8, "color": "#273240"},
                {"ui_key": "space", "label": "Space", "light_pos": 43, "color": "#273240"},
            ],
        }

    def apply_per_key_colors_by_ui_key(self, edits: dict[str, str]) -> PerKeyLightingPayload:
        state = self.read_per_key_state()
        keys: list[PerKeyLightingEntryPayload] = [
            {
                "ui_key": entry["ui_key"],
                "label": entry["label"],
                "light_pos": entry["light_pos"],
                "color": normalize_hex_color(edits[entry["ui_key"]])
                if entry["ui_key"] in edits
                else entry["color"],
            }
            for entry in state["keys"]
        ]
        return {
            "mode": state["mode"],
            "brightness": state["brightness"],
            "per_key_rgb_supported": state["per_key_rgb_supported"],
            "verification_status": state["verification_status"],
            "keys": keys,
        }


def build_default_lighting_controller() -> LightingController:
    return BytechLightingController()


def create_hid_device() -> HidFeatureDevice:
    hid_module = import_module("hid")
    return cast(HidFeatureDevice, hid_module.device())


def find_supported_vendor_path() -> bytes:
    hid_module = import_module("hid")
    for device in hid_module.enumerate():
        if (
            device.get("vendor_id") == KREO_VENDOR_ID
            and device.get("product_id") == KREO_PRODUCT_ID
            and device.get("usage_page") == KREO_USAGE_PAGE
            and device.get("usage") == KREO_USAGE
        ):
            path = device.get("path")
            if isinstance(path, bytes):
                return path

    raise LightingHardwareUnavailableError("Kreo Swarm vendor HID interface not found")


def normalize_hex_color(color: str) -> str:
    value = color.strip()
    if not value.startswith("#") or len(value) != 7:
        raise LightingProtocolError("expected #RRGGBB color")
    return value.lower()


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    normalized = normalize_hex_color(color)
    return (
        int(normalized[1:3], 16),
        int(normalized[3:5], 16),
        int(normalized[5:7], 16),
    )


def percent_to_device_brightness(brightness: int) -> int:
    return round((brightness / 100) * DEVICE_BRIGHTNESS_MAX)


def device_to_percent_brightness(level: int) -> int:
    return round((level / DEVICE_BRIGHTNESS_MAX) * 100)


def find_second_255_index(profile: bytes | bytearray) -> int:
    for index in range(len(profile) - 1):
        if profile[index] == 0xFF and profile[index + 1] == 0xFF:
            return index + 2
    raise LightingProtocolError("lighting brightness table marker not found in profile")


def parse_mode_id(profile: bytes) -> int:
    high_byte = profile[9]
    low_byte = profile[10]
    if high_byte:
        return (high_byte << 8) | low_byte
    return low_byte & 0x0F


def parse_effect_indices(profile: bytes | bytearray, mode_id: int) -> tuple[int, int]:
    marker_index = find_second_255_index(profile)
    brightness_index = marker_index + (mode_id * 2) - 2
    speed_index = brightness_index + 1
    if speed_index >= len(profile):
        raise LightingProtocolError("lighting mode index falls outside the profile")
    return brightness_index, speed_index


def parse_effect_type(profile: bytes, mode_id: int) -> int:
    _, speed_index = parse_effect_indices(profile, mode_id)
    return 1 if (profile[speed_index] & 0x0F) == 0 else 2


def parse_effect_speed(profile: bytes, mode_id: int) -> int:
    _, speed_index = parse_effect_indices(profile, mode_id)
    return (profile[speed_index] >> 4) & 0x0F


def parse_effect_brightness(profile: bytes, mode_id: int) -> int:
    brightness_index, _ = parse_effect_indices(profile, mode_id)
    return profile[brightness_index]


def parse_mode_name(mode_id: int) -> str:
    if mode_id == 0:
        return "off"
    if mode_id == STATIC_MODE_ID:
        return "static"
    if mode_id == CUSTOM_MODE_ID:
        return "custom"
    return f"effect_{mode_id}"


def update_group_color(light_table: bytes, mode_id: int, color: tuple[int, int, int]) -> bytes:
    offset = mode_id * 21
    if offset + 2 >= len(light_table):
        raise LightingProtocolError("lighting color group offset is outside the table")

    updated = bytearray(light_table)
    updated[offset] = color[0]
    updated[offset + 1] = color[1]
    updated[offset + 2] = color[2]
    return bytes(updated)


def parse_group_color(light_table: bytes, mode_id: int) -> str | None:
    offset = mode_id * 21
    if offset + 2 >= len(light_table):
        return None

    red, green, blue = light_table[offset : offset + 3]
    if red == 0 and green == 0 and blue == 0:
        return None
    return f"#{red:02x}{green:02x}{blue:02x}"


def rgb_to_hex(red: int, green: int, blue: int) -> str:
    return f"#{red:02x}{green:02x}{blue:02x}"


def parse_custom_light_color(planar_frame: bytes, light_pos: int) -> str:
    led_index = light_pos - 8
    if led_index < 0 or led_index >= CUSTOM_LIGHT_LED_COUNT:
        raise LightingProtocolError(f"light_pos {light_pos} is outside the custom LED range")
    return rgb_to_hex(
        planar_frame[led_index],
        planar_frame[led_index + CUSTOM_LIGHT_LED_COUNT],
        planar_frame[led_index + (CUSTOM_LIGHT_LED_COUNT * 2)],
    )


def build_profile_write(
    profile: bytes,
    *,
    mode_id: int,
    brightness_level: int,
    speed: int,
    effect_type: int,
) -> bytes:
    updated = bytearray(profile)
    updated[9] = (mode_id >> 8) & 0xFF
    updated[10] = mode_id & 0xFF

    if mode_id not in {CUSTOM_MODE_ID, 0, SNOW_MODE_ID}:
        brightness_index, speed_index = parse_effect_indices(updated, mode_id)
        updated[brightness_index] = brightness_level & 0xFF
        updated[speed_index] = ((speed & 0x0F) << 4) | (0 if effect_type == 1 else 7)

    return bytes(updated)


def build_demo_per_key_frame() -> bytes:
    red = [0] * CUSTOM_LIGHT_LED_COUNT
    green = [0] * CUSTOM_LIGHT_LED_COUNT
    blue = [0] * CUSTOM_LIGHT_LED_COUNT
    band_size = CUSTOM_LIGHT_LED_COUNT // 3

    for index in range(CUSTOM_LIGHT_LED_COUNT):
        if index < band_size:
            red[index] = 0xFF
            continue
        if index < band_size * 2:
            green[index] = 0xFF
            continue
        blue[index] = 0xFF

    return bytes([*red, *green, *blue])


def parse_key_records(payload: bytes) -> list[BytechKeyRecord]:
    records: list[BytechKeyRecord] = []
    for index in range(0, len(payload), 4):
        if index + 3 >= len(payload):
            break
        value = (
            (payload[index] << 24)
            | (payload[index + 1] << 16)
            | (payload[index + 2] << 8)
            | payload[index + 3]
        )
        slot = index // 4
        records.append(
            BytechKeyRecord(
                value=value,
                pos=8 + (slot * 4),
                effect_pos=8 + (slot * 3),
                light_pos=8 + slot,
            )
        )
    return records


def build_per_key_frame(colors_by_light_pos: dict[int, tuple[int, int, int]]) -> bytes:
    red = [0] * CUSTOM_LIGHT_LED_COUNT
    green = [0] * CUSTOM_LIGHT_LED_COUNT
    blue = [0] * CUSTOM_LIGHT_LED_COUNT

    for light_pos, (red_value, green_value, blue_value) in colors_by_light_pos.items():
        led_index = light_pos - 8
        if led_index < 0 or led_index >= CUSTOM_LIGHT_LED_COUNT:
            raise LightingProtocolError(f"light_pos {light_pos} is outside the custom LED range")
        red[led_index] = red_value & 0xFF
        green[led_index] = green_value & 0xFF
        blue[led_index] = blue_value & 0xFF

    return bytes([*red, *green, *blue])


class BytechLightingController:
    def __init__(
        self,
        *,
        device_path: bytes | None = None,
        path_provider: Callable[[], bytes] = find_supported_vendor_path,
        device_factory: Callable[[], HidFeatureDevice] | None = None,
    ) -> None:
        self._device_path = device_path
        self._path_provider = path_provider
        self._device_factory = device_factory or create_hid_device

    def read_state(self) -> LightingState:
        try:
            with self._open_device() as device:
                profile = self._read_profile(device)
                mode_id = parse_mode_id(profile)
                brightness_percent = device_to_percent_brightness(
                    parse_effect_brightness(
                        profile,
                        STATIC_MODE_ID if mode_id == CUSTOM_MODE_ID else mode_id,
                    )
                )
                color = None
                if mode_id == STATIC_MODE_ID:
                    color = parse_group_color(self._read_light_table(device), mode_id)
        except LightingHardwareUnavailableError:
            return StubLightingController().read_state()

        return LightingState(
            mode=parse_mode_name(mode_id),
            brightness=brightness_percent,
            per_key_rgb_supported=True,
            color=color,
            verification_status=LightingVerificationStatus.UNVERIFIED,
        )

    def is_connected(self) -> bool:
        try:
            self._resolve_path()
        except LightingHardwareUnavailableError:
            return False
        return True

    def supported_devices(self) -> list[str]:
        return ["Kreo Swarm"] if self.is_connected() else []

    def read_profile(self) -> bytes:
        with self._open_device() as device:
            return self._read_profile(device)

    def read_key_records(self) -> list[BytechKeyRecord]:
        with self._open_device() as device:
            return self._read_key_records(device)

    def read_per_key_state(self) -> PerKeyLightingPayload:
        try:
            with self._open_device() as device:
                return self._read_per_key_state_from_device(device)
        except LightingHardwareUnavailableError:
            return StubLightingController().read_per_key_state()

    def apply_per_key_colors(
        self,
        colors_by_light_pos: dict[int, tuple[int, int, int]],
    ) -> LightingState:
        with self._open_device() as device:
            profile = self._read_profile(device)
            current_mode_id = parse_mode_id(profile)
            brightness_source_mode = (
                STATIC_MODE_ID if current_mode_id == CUSTOM_MODE_ID else current_mode_id
            )
            current_brightness = parse_effect_brightness(profile, brightness_source_mode)

            if current_mode_id != CUSTOM_MODE_ID:
                updated_profile = build_profile_write(
                    profile,
                    mode_id=CUSTOM_MODE_ID,
                    brightness_level=current_brightness,
                    speed=0,
                    effect_type=1,
                )
                self._write_profile(device, updated_profile)

            self._prepare_custom_light_write(device)
            self._write_custom_light_frame(
                device,
                build_per_key_frame(colors_by_light_pos),
            )

        return LightingState(
            mode="custom",
            brightness=device_to_percent_brightness(current_brightness),
            per_key_rgb_supported=True,
            color=None,
            verification_status=LightingVerificationStatus.UNVERIFIED,
        )

    def apply_per_key_colors_by_ui_key(self, edits: dict[str, str]) -> PerKeyLightingPayload:
        normalized_edits = {
            ui_key: normalize_hex_color(color) for ui_key, color in edits.items()
        }

        with self._open_device() as device:
            profile = self._read_profile(device)
            key_records = self._read_key_records(device)
            current_mode_id = parse_mode_id(profile)
            brightness_source_mode = (
                STATIC_MODE_ID if current_mode_id == CUSTOM_MODE_ID else current_mode_id
            )
            current_brightness = parse_effect_brightness(profile, brightness_source_mode)

            base_colors = self._build_base_per_key_colors(
                device=device,
                profile=profile,
                key_records=key_records,
            )
            colors_by_light_pos = {
                entry["light_pos"]: hex_to_rgb(entry["color"]) for entry in base_colors
            }

            records_by_ui_key = self._build_records_by_ui_key(key_records)
            for ui_key, color in normalized_edits.items():
                record = records_by_ui_key.get(ui_key)
                if record is None:
                    raise LightingProtocolError(
                        f"per-key lighting target {ui_key!r} is unavailable"
                    )
                colors_by_light_pos[record.light_pos] = hex_to_rgb(color)

            if current_mode_id != CUSTOM_MODE_ID:
                updated_profile = build_profile_write(
                    profile,
                    mode_id=CUSTOM_MODE_ID,
                    brightness_level=current_brightness,
                    speed=0,
                    effect_type=1,
                )
                self._write_profile(device, updated_profile)

            self._prepare_custom_light_write(device)
            self._write_custom_light_frame(device, build_per_key_frame(colors_by_light_pos))

            return self._read_per_key_state_from_device(device)

    def apply_global_lighting(self, request: LightingApplyRequest) -> LightingState:
        if request.mode != "static":
            raise LightingProtocolError(
                "only static mode is currently supported for hardware writes"
            )

        requested_brightness = request.brightness if request.brightness is not None else 80
        device_brightness = percent_to_device_brightness(requested_brightness)

        with self._open_device() as device:
            profile = self._read_profile(device)
            current_mode_id = parse_mode_id(profile)
            current_speed = parse_effect_speed(profile, current_mode_id)

            updated_profile = build_profile_write(
                profile,
                mode_id=STATIC_MODE_ID,
                brightness_level=device_brightness,
                speed=current_speed,
                effect_type=(
                    1
                    if request.color is not None
                    else parse_effect_type(profile, current_mode_id)
                ),
            )
            self._write_profile(device, updated_profile)

            if request.color is not None:
                current_table = self._read_light_table(device)
                updated_table = update_group_color(
                    current_table,
                    STATIC_MODE_ID,
                    hex_to_rgb(request.color),
                )
                self._write_light_table(device, updated_table)

            verification_status = self._verify_state(
                device=device,
                brightness_level=device_brightness,
                color=request.color,
            )

        return LightingState(
            mode=request.mode,
            brightness=requested_brightness,
            per_key_rgb_supported=False,
            color=normalize_hex_color(request.color) if request.color is not None else None,
            verification_status=verification_status,
        )

    def apply_demo_per_key_lighting(self) -> LightingState:
        with self._open_device() as device:
            profile = self._read_profile(device)
            current_mode_id = parse_mode_id(profile)
            current_brightness = parse_effect_brightness(profile, current_mode_id)

            if current_mode_id != CUSTOM_MODE_ID:
                updated_profile = build_profile_write(
                    profile,
                    mode_id=CUSTOM_MODE_ID,
                    brightness_level=current_brightness,
                    speed=0,
                    effect_type=1,
                )
                self._write_profile(device, updated_profile)

            self._prepare_custom_light_write(device)
            self._write_custom_light_frame(device, build_demo_per_key_frame())

        return LightingState(
            mode="custom",
            brightness=device_to_percent_brightness(current_brightness),
            per_key_rgb_supported=True,
            color=None,
            verification_status=LightingVerificationStatus.UNVERIFIED,
        )

    def _verify_state(
        self,
        *,
        device: HidFeatureDevice,
        brightness_level: int,
        color: str | None,
    ) -> LightingVerificationStatus:
        try:
            profile = self._read_profile(device)
            verified_mode = parse_mode_id(profile)
            verified_brightness = parse_effect_brightness(profile, STATIC_MODE_ID)
            if verified_mode != STATIC_MODE_ID or verified_brightness != brightness_level:
                return LightingVerificationStatus.FAILED

            if color is not None:
                expected_color = normalize_hex_color(color)
                verified_color = parse_group_color(self._read_light_table(device), STATIC_MODE_ID)
                if verified_color != expected_color:
                    return LightingVerificationStatus.FAILED
        except LightingProtocolError:
            return LightingVerificationStatus.FAILED
        except LightingHardwareUnavailableError:
            return LightingVerificationStatus.UNVERIFIED

        return LightingVerificationStatus.VERIFIED

    def _read_per_key_state_from_device(self, device: HidFeatureDevice) -> PerKeyLightingPayload:
        profile = self._read_profile(device)
        key_records = self._read_key_records(device)
        mode_id = parse_mode_id(profile)
        brightness = device_to_percent_brightness(
            parse_effect_brightness(
                profile,
                STATIC_MODE_ID if mode_id == CUSTOM_MODE_ID else mode_id,
            )
        )
        keys = self._build_base_per_key_colors(
            device=device,
            profile=profile,
            key_records=key_records,
        )
        return {
            "mode": parse_mode_name(mode_id),
            "brightness": brightness,
            "per_key_rgb_supported": True,
            "verification_status": LightingVerificationStatus.UNVERIFIED.value,
            "keys": keys,
        }

    def _build_base_per_key_colors(
        self,
        *,
        device: HidFeatureDevice,
        profile: bytes,
        key_records: list[BytechKeyRecord],
    ) -> list[PerKeyLightingEntryPayload]:
        mode_id = parse_mode_id(profile)
        records_by_ui_key = self._build_records_by_ui_key(key_records)
        if mode_id == CUSTOM_MODE_ID:
            custom_frame = self._read_custom_light_frame(device)
            return [
                {
                    "ui_key": ui_key,
                    "label": HID_VALUE_TO_UI_KEY[record.value][1],
                    "light_pos": record.light_pos,
                    "color": parse_custom_light_color(custom_frame, record.light_pos),
                }
                for ui_key, record in records_by_ui_key.items()
            ]

        default_color = DEFAULT_KEYCAP_COLOR
        if mode_id == STATIC_MODE_ID:
            static_color = parse_group_color(self._read_light_table(device), STATIC_MODE_ID)
            if static_color is not None:
                default_color = static_color

        return [
            {
                "ui_key": ui_key,
                "label": HID_VALUE_TO_UI_KEY[record.value][1],
                "light_pos": record.light_pos,
                "color": default_color,
            }
            for ui_key, record in records_by_ui_key.items()
        ]

    def _build_records_by_ui_key(
        self,
        key_records: list[BytechKeyRecord],
    ) -> dict[str, BytechKeyRecord]:
        records_by_ui_key: dict[str, BytechKeyRecord] = {}
        for record in key_records:
            mapping = HID_VALUE_TO_UI_KEY.get(record.value)
            if mapping is None:
                continue
            ui_key, _label = mapping
            records_by_ui_key.setdefault(ui_key, record)
        return records_by_ui_key

    def _read_profile(self, device: HidFeatureDevice) -> bytes:
        response = self._exchange_command(
            device=device,
            command=PROFILE_READ_COMMAND,
            response_length=8 + PROFILE_SIZE,
            min_response_length=8 + PROFILE_SIZE,
        )
        return response[-PROFILE_SIZE:]

    def _read_key_records(self, device: HidFeatureDevice) -> list[BytechKeyRecord]:
        response = self._exchange_command(
            device=device,
            command=KEYS_READ_COMMAND,
            response_length=FEATURE_REPORT_SIZE,
            min_response_length=8,
        )
        return parse_key_records(response[8:])

    def _write_profile(self, device: HidFeatureDevice, profile: bytes) -> None:
        if len(profile) != PROFILE_SIZE:
            raise LightingProtocolError("profile write requires exactly 128 bytes")
        self._send_command(device, PROFILE_WRITE_COMMAND + profile)

    def _read_light_table(self, device: HidFeatureDevice) -> bytes:
        response = self._exchange_command(
            device=device,
            command=LIGHT_TABLE_READ_COMMAND,
            response_length=LIGHT_TABLE_RESPONSE_SIZE,
            min_response_length=8 + LIGHT_TABLE_SIZE,
        )
        return response[8 : 8 + LIGHT_TABLE_SIZE]

    def _write_light_table(self, device: HidFeatureDevice, light_table: bytes) -> None:
        if len(light_table) != LIGHT_TABLE_SIZE:
            raise LightingProtocolError("light-table write requires exactly 480 bytes")
        self._send_command(device, LIGHT_TABLE_WRITE_COMMAND + light_table)

    def _read_custom_light_frame(self, device: HidFeatureDevice) -> bytes:
        response = self._exchange_command(
            device=device,
            command=CUSTOM_LIGHT_PREPARE_COMMAND,
            response_length=FEATURE_REPORT_SIZE,
            min_response_length=CUSTOM_LIGHT_RESPONSE_SIZE,
        )
        return response[8 : 8 + CUSTOM_LIGHT_FRAME_SIZE]

    def _prepare_custom_light_write(self, device: HidFeatureDevice) -> None:
        self._exchange_command(
            device=device,
            command=CUSTOM_LIGHT_PREPARE_COMMAND,
            response_length=FEATURE_REPORT_SIZE,
            min_response_length=8,
        )

    def _write_custom_light_frame(self, device: HidFeatureDevice, planar_frame: bytes) -> None:
        if len(planar_frame) != CUSTOM_LIGHT_FRAME_SIZE:
            raise LightingProtocolError(
                f"custom light frame requires exactly {CUSTOM_LIGHT_FRAME_SIZE} bytes"
            )
        self._send_command(device, CUSTOM_LIGHT_WRITE_COMMAND + planar_frame)

    def _exchange_command(
        self,
        *,
        device: HidFeatureDevice,
        command: bytes,
        response_length: int,
        min_response_length: int,
    ) -> bytes:
        self._send_command(device, command)
        response = bytes(device.get_feature_report(READ_REPORT_ID, response_length))
        if len(response) < min_response_length:
            raise LightingProtocolError(
                f"expected at least {min_response_length} bytes from report "
                f"{READ_REPORT_ID}, got {len(response)}"
            )
        return response

    def _send_command(self, device: HidFeatureDevice, command: bytes) -> None:
        if len(command) > FEATURE_REPORT_SIZE - 1:
            raise LightingProtocolError("feature command is larger than the HID report size")

        padding = [0] * (FEATURE_REPORT_SIZE - 1 - len(command))
        payload = bytes([WRITE_REPORT_ID, *command, *padding])
        bytes_sent = device.send_feature_report(payload)
        if bytes_sent <= 0:
            raise LightingHardwareUnavailableError("failed to send feature report to keyboard")

    def _resolve_path(self) -> bytes:
        if self._device_path is not None:
            return self._device_path
        return self._path_provider()

    def _open_device(self) -> _OpenedFeatureDevice:
        return _OpenedFeatureDevice(self._resolve_path(), self._device_factory)


class _OpenedFeatureDevice:
    def __init__(self, path: bytes, factory: Callable[[], HidFeatureDevice]) -> None:
        self._path = path
        self._factory = factory
        self._device: HidFeatureDevice | None = None

    def __enter__(self) -> HidFeatureDevice:
        device = self._factory()
        try:
            device.open_path(self._path)
        except OSError as exc:
            raise LightingHardwareUnavailableError(
                "failed to open Kreo Swarm HID interface"
            ) from exc
        self._device = device
        return device

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._device is not None:
            self._device.close()
