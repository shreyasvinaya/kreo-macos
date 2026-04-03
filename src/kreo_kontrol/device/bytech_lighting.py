from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Literal, Protocol, TypedDict, cast

from kreo_kontrol.device.domains.keymap import (
    KeyAction,
    KeyActionOption,
    KeyAssignment,
    KeymapPayload,
)
from kreo_kontrol.device.domains.lighting import (
    LightingApplyRequest,
    LightingState,
    LightingVerificationStatus,
)
from kreo_kontrol.device.domains.macros import (
    MacroAction,
    MacroSlot,
    MacrosPayload,
    MacroUpsertRequest,
)
from kreo_kontrol.device.domains.profiles import (
    ProfilesPayload,
    unsupported_profiles_payload,
)

KREO_VENDOR_ID = 0x258A
KREO_PRODUCT_ID = 0x010C
KREO_USAGE_PAGE = 0xFF00
KREO_USAGE = 0x01
RECEIVER_VENDOR_ID = 0x3554
RECEIVER_PRODUCT_ID = 0xFA09
RECEIVER_USAGE_PAGE = 0xFF02
RECEIVER_USAGE = 0x02

WRITE_REPORT_ID = 0x05
READ_REPORT_ID = 0x06
FEATURE_REPORT_SIZE = 520
PROFILE_SIZE = 128
LIGHT_TABLE_SIZE = 480
LIGHT_TABLE_RESPONSE_SIZE = 520
WIRELESS_REPORT_ID = 0x13
WIRELESS_REPORT_SIZE = 19
WIRELESS_PACKET_CHUNK_SIZE = 14
WIRELESS_PADDING_SIZE = 512

PROFILE_READ_COMMAND = b"\x84\x00\x00\x01\x00\x80"
PROFILE_WRITE_COMMAND = b"\x04\x00\x00\x01\x00\x80\x00"
LIGHT_TABLE_READ_COMMAND = b"\x8a\x00\x00\x01\x00\xe3\x01"
LIGHT_TABLE_WRITE_COMMAND = b"\x0a\x00\x00\x00\x00\x00\x02"
KEYS_READ_COMMAND = b"\x83\x00\x00\x01\x00\xf8\x01"
CUSTOM_LIGHT_PREPARE_COMMAND = b"\x86\x00\x00\x01\x00\x7a\x01"
CUSTOM_LIGHT_WRITE_COMMAND = b"\x06\x00\x00\x01\x00\x7a\x01"
WIRELESS_PROFILE_READ_COMMAND = 68
WIRELESS_LIGHT_TABLE_READ_COMMAND = 73
WIRELESS_CUSTOM_LIGHT_READ_COMMAND = 66
WIRELESS_PROFILE_WRITE_COMMAND = 4
WIRELESS_LIGHT_TABLE_WRITE_COMMAND = 9
WIRELESS_CUSTOM_LIGHT_WRITE_COMMAND = 2
MACRO_READ_COMMAND = b"\x85\x00\x00\x01\x00\x00\x02"
MACRO_WRITE_COMMAND = b"\x05\x00\x00\x01\x00\x00\x02"

STATIC_MODE_ID = 1
CUSTOM_MODE_ID = 277
SNOW_MODE_ID = 19
DEVICE_BRIGHTNESS_MAX = 4
CUSTOM_LIGHT_LED_COUNT = 126
CUSTOM_LIGHT_FRAME_SIZE = CUSTOM_LIGHT_LED_COUNT * 3
CUSTOM_LIGHT_RESPONSE_SIZE = 8 + CUSTOM_LIGHT_FRAME_SIZE
DEFAULT_KEYCAP_COLOR = "#273240"
KEYMAP_RECORD_COUNT = 126
KEYMAP_PAYLOAD_SIZE = KEYMAP_RECORD_COUNT * 4
MAX_MACRO_SLOTS = 16
LIGHTING_MODE_IDS: dict[str, int] = {
    "off": 0,
    "static": 1,
    "breathe": 2,
    "neon_rainbow": 3,
    "wave": 4,
    "ripple": 5,
    "raindrop": 6,
    "snake": 7,
    "press_action": 8,
    "converge": 9,
    "sine_wave": 10,
    "kaleidoscope": 11,
    "line_wave": 12,
    "custom": CUSTOM_MODE_ID,
    "laser": 14,
    "circle_wave": 15,
    "dazzling": 16,
    "rain_down": 17,
    "meteor": 18,
    "train": 23,
    "fireworks": 24,
}
MODE_ID_TO_NAME = {mode_id: name for name, mode_id in LIGHTING_MODE_IDS.items()}

MODIFIER_MASK_TO_LABEL: dict[int, str] = {
    1: "Control Left",
    2: "Shift Left",
    4: "Option Left",
    8: "Command Left",
    16: "Control Right",
    32: "Shift Right",
    64: "Option Right",
    128: "Command Right",
}

MEDIA_ACTIONS: dict[int, tuple[str, str, str]] = {
    0x020000B5: ("media_next", "Next Track", "Media"),
    0x020000B6: ("media_previous", "Previous Track", "Media"),
    0x020000B7: ("media_stop", "Stop", "Media"),
    0x020000CD: ("media_play_pause", "Play / Pause", "Media"),
    0x020000E2: ("media_mute", "Mute", "Media"),
    0x020000E9: ("media_volume_up", "Volume Up", "Media"),
    0x020000EA: ("media_volume_down", "Volume Down", "Media"),
    0x02000183: ("media_calculator", "Calculator", "System"),
    0x0200018A: ("media_mail", "Mail", "System"),
    0x02000194: ("media_browser", "Browser", "System"),
}

MOUSE_ACTIONS: dict[int, tuple[str, str, str]] = {
    0x01010100: ("mouse_left", "Left Click", "Mouse"),
    0x01020100: ("mouse_right", "Right Click", "Mouse"),
    0x01030100: ("mouse_middle", "Middle Click", "Mouse"),
    0x01040100: ("mouse_back", "Back", "Mouse"),
    0x01050100: ("mouse_forward", "Forward", "Mouse"),
}

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
MACRO_UI_KEY_TO_CODE: dict[str, int] = {
    ui_key: raw_value
    for raw_value, (ui_key, _label) in HID_VALUE_TO_UI_KEY.items()
    if raw_value <= 0xFF
}
MACRO_CODE_TO_UI_KEY: dict[int, str] = {
    code: ui_key for ui_key, code in MACRO_UI_KEY_TO_CODE.items()
}
MACRO_EXECUTION_TYPE_TO_ID = {
    "FIXED_COUNT": 1,
    "UNTIL_ANY_PRESSED": 2,
    "UNTIL_RELEASED": 4,
}
MACRO_ID_TO_EXECUTION_TYPE = {
    mode_id: name for name, mode_id in MACRO_EXECUTION_TYPE_TO_ID.items()
}
MACRO_RELEASE_NIBBLES = {8, 9, 10, 11}
MACRO_MODIFIER_NIBBLES = {1, 9}
MACRO_MODIFIER_KEYS = {
    "left_ctrl",
    "left_shift",
    "left_opt",
    "left_cmd",
    "right_ctrl",
    "right_shift",
    "right_opt",
    "right_cmd",
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

    def write(self, data: bytes) -> int:
        ...

    def read(self, max_length: int, timeout_ms: int = 0) -> bytes:
        ...


class LightingController(Protocol):
    def configurable(self) -> bool:
        ...

    def transport_kind(self) -> str:
        ...

    def is_connected(self) -> bool:
        ...

    def supported_devices(self) -> list[str]:
        ...

    def supports_profiles(self) -> bool:
        ...

    def read_profiles(self) -> ProfilesPayload:
        ...

    def read_state(self) -> LightingState:
        ...

    def apply_global_lighting(self, request: LightingApplyRequest) -> LightingState:
        ...

    def read_per_key_state(self) -> PerKeyLightingPayload:
        ...

    def apply_per_key_colors_by_ui_key(self, edits: dict[str, str]) -> PerKeyLightingPayload:
        ...

    def read_keymap(self) -> KeymapPayload:
        ...

    def apply_keymap(
        self,
        edits: dict[str, dict[str, int | None]],
    ) -> KeymapPayload:
        ...

    def read_macros(self) -> MacrosPayload:
        ...

    def apply_macro(
        self,
        *,
        slot_id: int,
        request: dict[str, object],
    ) -> MacrosPayload:
        ...

    def delete_macro(self, slot_id: int) -> MacrosPayload:
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


@dataclass(frozen=True)
class ReceiverLedMapKey:
    logical_id: str
    ui_key: str
    label: str
    svg_id: str
    led_index: int
    protocol_pos: int


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
    def configurable(self) -> bool:
        return False

    def transport_kind(self) -> str:
        return "none"

    def is_connected(self) -> bool:
        return False

    def supported_devices(self) -> list[str]:
        return []

    def supports_profiles(self) -> bool:
        return False

    def read_profiles(self) -> ProfilesPayload:
        return unsupported_profiles_payload(
            "Bytech transport does not expose hardware profile slots"
        )

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

    def read_keymap(self) -> KeymapPayload:
        catalog = build_keymap_action_catalog()
        return {
            "verification_status": "unverified",
            "available_actions": [option.model_dump() for option in catalog],
            "assignments": [
                {
                    "ui_key": "right_opt",
                    "logical_id": "RALT",
                    "svg_id": "key_RALT",
                    "label": "Command",
                    "protocol_pos": 380,
                    "base_action": decode_key_action(0x00400000).model_dump(),
                    "fn_action": decode_key_action(0).model_dump(),
                }
            ],
        }

    def apply_keymap(
        self,
        edits: dict[str, dict[str, int | None]],
    ) -> KeymapPayload:
        state = self.read_keymap()
        assignments = []
        for assignment in state["assignments"]:
            update = edits.get(str(assignment["ui_key"]), {})
            assignment_data = assignment
            base_action = cast(dict[str, object], assignment_data["base_action"])
            fn_action = cast(dict[str, object], assignment_data["fn_action"])
            base_raw_value = update.get("base_raw_value", base_action["raw_value"])
            fn_raw_value = update.get("fn_raw_value", fn_action["raw_value"])
            assignments.append(
                {
                    **assignment_data,
                    "base_action": decode_key_action(
                        int(cast(int, base_raw_value))
                    ).model_dump(),
                    "fn_action": decode_key_action(
                        int(cast(int, fn_raw_value))
                    ).model_dump(),
                }
            )
        return {
            "verification_status": "unverified",
            "available_actions": state["available_actions"],
            "assignments": assignments,
        }

    def read_macros(self) -> MacrosPayload:
        return {
            "supported": False,
            "reason": "Macros require wired USB mode on this keyboard",
            "verification_status": LightingVerificationStatus.UNVERIFIED.value,
            "next_slot_id": 0,
            "max_slots": MAX_MACRO_SLOTS,
            "slots": [],
        }

    def apply_macro(
        self,
        *,
        slot_id: int,
        request: dict[str, object],
    ) -> MacrosPayload:
        raise LightingProtocolError("macros require wired USB mode on this keyboard")

    def delete_macro(self, slot_id: int) -> MacrosPayload:
        raise LightingProtocolError("macros require wired USB mode on this keyboard")


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


def find_supported_receiver_path() -> bytes:
    hid_module = import_module("hid")
    for device in hid_module.enumerate():
        if (
            device.get("vendor_id") == RECEIVER_VENDOR_ID
            and device.get("product_id") == RECEIVER_PRODUCT_ID
            and device.get("usage_page") == RECEIVER_USAGE_PAGE
            and device.get("usage") == RECEIVER_USAGE
        ):
            path = device.get("path")
            if isinstance(path, bytes):
                return path

    raise LightingHardwareUnavailableError("Kreo Swarm receiver HID interface not found")


def map_logical_id_to_ui_key(logical_id: str) -> tuple[str, str]:
    if logical_id.startswith("F") and logical_id[1:].isdigit():
        return logical_id.lower(), logical_id
    if len(logical_id) == 1 and logical_id.isalpha():
        return logical_id.lower(), logical_id
    if len(logical_id) == 1 and logical_id.isdigit():
        return logical_id, logical_id

    mapping = {
        "ESC": ("esc", "Esc"),
        "PRINTSCREEN": ("print_screen", "PrtSc"),
        "GRAVE": ("`", "`"),
        "MINUS": ("-", "-"),
        "EQUAL": ("=", "="),
        "BACKSPACE": ("backspace", "Backspace"),
        "TAB": ("tab", "Tab"),
        "LBRACKET": ("[", "["),
        "RBRACKET": ("]", "]"),
        "BACKSLASH": ("\\", "\\"),
        "CAPSLOCK": ("caps", "Caps"),
        "SEMICOLON": (";", ";"),
        "QUOTE": ("'", "'"),
        "ENTER": ("enter", "Enter"),
        "LSHIFT": ("left_shift", "Shift"),
        "COMMA": (",", ","),
        "DOT": (".", "."),
        "SLASH": ("/", "/"),
        "RSHIFT": ("right_shift", "Shift"),
        "LCTRL": ("left_ctrl", "Control"),
        "LGUI": ("left_cmd", "Option"),
        "LALT": ("left_opt", "Command"),
        "SPACE": ("space", "Space"),
        "RALT": ("right_opt", "Command"),
        "FN": ("fn", "Fn"),
        "RCTRL": ("right_ctrl", "Control"),
        "UP": ("up", "Up"),
        "LEFT": ("left", "Left"),
        "DOWN": ("down", "Down"),
        "RIGHT": ("right", "Right"),
        "DELETE": ("delete", "Del"),
        "PAGEUP": ("page_up", "PgUp"),
        "PAGEDOWN": ("page_down", "PgDn"),
        "END": ("end", "End"),
    }
    result = mapping.get(logical_id)
    if result is None:
        raise LightingProtocolError(f"unsupported Swarm75 logical key {logical_id!r}")
    return result


def load_swarm75_led_map() -> list[ReceiverLedMapKey]:
    asset_path = (
        Path(__file__).resolve().parents[3]
        / "kreo_website_dump"
        / "kontrol.kreo-tech.com"
        / "assets"
        / "keyboard"
        / "swarm75"
        / "meta"
        / "led-map.json"
    )
    if not asset_path.exists():
        raise LightingProtocolError(f"missing Swarm75 LED map at {asset_path}")

    payload = json.loads(asset_path.read_text())
    keys: list[ReceiverLedMapKey] = []
    for raw_key in payload.get("keys", []):
        logical_id = raw_key.get("logicalId")
        led_index = raw_key.get("ledIndex")
        protocol_pos = raw_key.get("protocolPos")
        svg_id = raw_key.get("svgId")
        if (
            not isinstance(logical_id, str)
            or not isinstance(led_index, int)
            or not isinstance(protocol_pos, int)
            or not isinstance(svg_id, str)
        ):
            continue
        ui_key, label = map_logical_id_to_ui_key(logical_id.upper())
        keys.append(
            ReceiverLedMapKey(
                logical_id=logical_id.upper(),
                ui_key=ui_key,
                label=label,
                svg_id=svg_id,
                led_index=led_index,
                protocol_pos=protocol_pos,
            )
        )

    return keys


def build_keymap_action_catalog() -> list[KeyActionOption]:
    modifier_side_suffixes = {
        "left_ctrl": "Left",
        "left_shift": "Left",
        "left_opt": "Left",
        "left_cmd": "Left",
        "right_ctrl": "Right",
        "right_shift": "Right",
        "right_opt": "Right",
        "right_cmd": "Right",
    }
    options = [
        KeyActionOption(
            action_id="disabled",
            label="Disabled",
            category="System",
            raw_value=0,
        )
    ]
    seen_raw_values = {0}

    key_entries = sorted(HID_VALUE_TO_UI_KEY.items(), key=lambda item: item[1][1])
    for raw_value, (ui_key, label) in key_entries:
        if raw_value in seen_raw_values:
            continue
        seen_raw_values.add(raw_value)
        is_modifier = ui_key.endswith(("ctrl", "shift", "cmd", "opt")) or ui_key == "fn"
        category = "Modifiers" if is_modifier else "Keys"
        display_label = (
            f"{label} {modifier_side_suffixes[ui_key]}"
            if ui_key in modifier_side_suffixes
            else label
        )
        options.append(
            KeyActionOption(
                action_id=f"basic:{ui_key}",
                label=display_label,
                category=category,
                raw_value=raw_value,
            )
        )

    for raw_value, (action_id, label, category) in sorted(MOUSE_ACTIONS.items()):
        options.append(
            KeyActionOption(
                action_id=action_id,
                label=label,
                category=category,
                raw_value=raw_value,
            )
        )

    for raw_value, (action_id, label, category) in sorted(MEDIA_ACTIONS.items()):
        options.append(
            KeyActionOption(
                action_id=action_id,
                label=label,
                category=category,
                raw_value=raw_value,
            )
        )

    return options


def build_macro_action_options(macro_slots: list[dict[str, object]]) -> list[KeyActionOption]:
    options: list[KeyActionOption] = []
    for slot in macro_slots:
        slot_id = slot.get("slot_id")
        name = slot.get("name")
        if not isinstance(slot_id, int) or not isinstance(name, str):
            continue
        options.append(
            KeyActionOption(
                action_id=f"macro:{slot_id}",
                label=name,
                category="Macro",
                raw_value=(3 << 24) | (slot_id & 0xFF),
            )
        )
    return options


def decode_key_action(raw_value: int) -> KeyAction:
    for option in build_keymap_action_catalog():
        if option.raw_value == raw_value:
            return KeyAction.model_validate(option.model_dump())

    if raw_value == 0:
        return KeyAction(
            action_id="disabled",
            label="Disabled",
            category="System",
            raw_value=0,
        )

    action_type = (raw_value >> 24) & 0xFF
    high_param = (raw_value >> 16) & 0xFF
    mid_param = (raw_value >> 8) & 0xFF
    low_param = raw_value & 0xFF

    if action_type == 3:
        return KeyAction(
            action_id=f"macro:{low_param}",
            label=f"Macro {low_param}",
            category="Macro",
            raw_value=raw_value,
        )

    if action_type == 0 and high_param and mid_param:
        modifiers = [
            label
            for bit, label in MODIFIER_MASK_TO_LABEL.items()
            if high_param & bit
        ]
        key_name = HID_VALUE_TO_UI_KEY.get(
            mid_param,
            (f"0x{mid_param:02x}", f"0x{mid_param:02x}"),
        )[1]
        return KeyAction(
            action_id=f"combo:{raw_value:08x}",
            label=" + ".join([*modifiers, key_name]),
            category="Shortcut",
            raw_value=raw_value,
        )

    if action_type == 0 and high_param and not mid_param and not low_param:
        modifier_label = MODIFIER_MASK_TO_LABEL.get(high_param, f"Modifier 0x{high_param:02x}")
        return KeyAction(
            action_id=f"modifier:{raw_value:08x}",
            label=modifier_label,
            category="Modifiers",
            raw_value=raw_value,
        )

    if action_type == 13:
        fn_label = "Fn" if low_param == 0 else f"Fn{low_param}"
        return KeyAction(
            action_id=f"fn:{low_param}",
            label=fn_label,
            category="Function",
            raw_value=raw_value,
        )

    return KeyAction(
        action_id=f"raw:{raw_value:08x}",
        label=f"0x{raw_value:08x}",
        category="Raw",
        raw_value=raw_value,
    )


def encode_macro_execution_id(execution_type: str) -> int:
    try:
        return MACRO_EXECUTION_TYPE_TO_ID[execution_type]
    except KeyError as exc:
        raise LightingProtocolError(
            f"unsupported macro execution type {execution_type!r}"
        ) from exc


def decode_macro_execution_type(execution_id: int) -> str:
    return MACRO_ID_TO_EXECUTION_TYPE.get(execution_id, "FIXED_COUNT")


def normalize_macro_cycle_times(execution_type: str, cycle_times: int) -> int:
    if execution_type == "FIXED_COUNT":
        return max(1, min(250, cycle_times))
    return 1


def encode_macro_binding_value(
    slot_id: int,
    *,
    execution_type: str,
    cycle_times: int,
) -> int:
    execution_id = encode_macro_execution_id(execution_type)
    repeat_count = normalize_macro_cycle_times(execution_type, cycle_times)
    return (3 << 24) | (execution_id << 16) | (repeat_count << 8) | (slot_id & 0xFF)


def parse_macro_headers(blob: bytes) -> list[bytes]:
    groups: list[bytes] = []
    headers: list[tuple[int, int]] = []
    offset = 0
    while offset + 3 < len(blob):
        header_start = blob[offset]
        group_length = blob[offset + 2]
        if blob[offset + 1] == 0 and blob[offset + 3] == 0 and 0 < group_length < 1000:
            headers.append((header_start, group_length))
            offset += 4
            continue
        break

    payload_offset = offset
    for header_start, group_length in headers:
        if payload_offset + group_length > len(blob):
            break
        groups.append(
            bytes(
                [
                    header_start,
                    0,
                    group_length,
                    0,
                    *blob[payload_offset : payload_offset + group_length],
                ]
            )
        )
        payload_offset += group_length
    return groups


def assemble_macro_groups(groups: list[bytes]) -> bytes:
    headers = bytearray()
    payload = bytearray()
    for group in groups:
        if len(group) < 4:
            continue
        headers.extend(group[:4])
        payload.extend(group[4:])
    return bytes([*headers, *payload])


def encode_macro_group_data(request: MacroUpsertRequest) -> bytes:
    encoded_name = request.name.encode("utf-8")
    payload = bytearray([len(encoded_name), *encoded_name])
    for action in request.actions:
        key_code = MACRO_UI_KEY_TO_CODE.get(action.key)
        if key_code is None:
            raise LightingProtocolError(f"unsupported macro key {action.key!r}")
        nibble = 1 if action.key in MACRO_MODIFIER_KEYS else 0
        if action.event_type == "release":
            nibble += 8
        payload.extend(
            [
                ((nibble & 0x0F) << 4) | ((action.delay_ms >> 16) & 0x0F),
                (action.delay_ms >> 8) & 0xFF,
                action.delay_ms & 0xFF,
                key_code & 0xFF,
            ]
        )
    return bytes(payload)


def decode_macro_group(
    slot_id: int,
    group: bytes,
    *,
    bound_ui_keys: list[str],
    execution_type: str,
    cycle_times: int,
) -> MacroSlot:
    payload = group[4:]
    name_length = payload[0] if payload else 0
    name_bytes = bytes(payload[1 : 1 + name_length])
    name = name_bytes.decode("utf-8", errors="ignore")
    actions: list[MacroAction] = []
    action_payload = payload[1 + name_length :]
    for index in range(0, len(action_payload), 4):
        chunk = action_payload[index : index + 4]
        if len(chunk) < 4:
            continue
        event_nibble = (chunk[0] >> 4) & 0x0F
        key = MACRO_CODE_TO_UI_KEY.get(chunk[3], f"raw_{chunk[3]:02x}")
        actions.append(
            MacroAction(
                key=key,
                event_type="release"
                if event_nibble in MACRO_RELEASE_NIBBLES
                else "press",
                delay_ms=((chunk[0] & 0x0F) << 16) | (chunk[1] << 8) | chunk[2],
            )
        )
    return MacroSlot(
        slot_id=slot_id,
        name=name,
        execution_type=cast(
            Literal["FIXED_COUNT", "UNTIL_RELEASED", "UNTIL_ANY_PRESSED"],
            execution_type,
        ),
        cycle_times=cycle_times,
        bound_ui_keys=bound_ui_keys,
        actions=actions,
    )


def build_key_records_payload(records: list[BytechKeyRecord]) -> bytes:
    payload = bytearray(KEYMAP_PAYLOAD_SIZE)
    for record in records:
        slot = (record.pos - 8) // 4
        if slot < 0 or slot >= KEYMAP_RECORD_COUNT:
            continue
        offset = slot * 4
        payload[offset] = (record.value >> 24) & 0xFF
        payload[offset + 1] = (record.value >> 16) & 0xFF
        payload[offset + 2] = (record.value >> 8) & 0xFF
        payload[offset + 3] = record.value & 0xFF
    return bytes(payload)


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
    return MODE_ID_TO_NAME.get(mode_id, f"effect_{mode_id}")


def parse_mode_id_from_name(mode_name: str) -> int:
    mode_id = LIGHTING_MODE_IDS.get(mode_name)
    if mode_id is None:
        raise LightingProtocolError(f"lighting mode {mode_name!r} is not supported")
    return mode_id


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


def parse_receiver_custom_light_color(frame: bytes, led_index: int) -> str:
    offset = led_index * 3
    if offset + 2 >= len(frame):
        raise LightingProtocolError(f"receiver led index {led_index} is outside the custom frame")
    return rgb_to_hex(frame[offset], frame[offset + 1], frame[offset + 2])


def update_receiver_frame_color(
    frame: bytes,
    led_index: int,
    color: tuple[int, int, int],
) -> bytes:
    offset = led_index * 3
    if offset + 2 >= len(frame):
        raise LightingProtocolError(f"receiver led index {led_index} is outside the custom frame")
    updated = bytearray(frame)
    updated[offset] = color[0]
    updated[offset + 1] = color[1]
    updated[offset + 2] = color[2]
    return bytes(updated)


def pad_receiver_payload(payload: bytes, padded_size: int) -> bytes:
    if len(payload) > padded_size:
        raise LightingProtocolError(
            f"receiver payload of {len(payload)} bytes exceeds padded size {padded_size}"
        )
    return bytes([*payload, *([0] * (padded_size - len(payload)))])


class BytechLightingController:
    def __init__(
        self,
        *,
        device_path: bytes | None = None,
        path_provider: Callable[[], bytes] = find_supported_vendor_path,
        receiver_path: bytes | None = None,
        receiver_path_provider: Callable[[], bytes] = find_supported_receiver_path,
        device_factory: Callable[[], HidFeatureDevice] | None = None,
    ) -> None:
        self._device_path = device_path
        self._path_provider = path_provider
        self._receiver_path = receiver_path
        self._receiver_path_provider = receiver_path_provider
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
            try:
                with self._open_receiver_device() as device:
                    profile = self._receiver_read_profile(device)
                    mode_id = parse_mode_id(profile)
                    brightness_percent = device_to_percent_brightness(
                        parse_effect_brightness(
                            profile,
                            STATIC_MODE_ID if mode_id == CUSTOM_MODE_ID else mode_id,
                        )
                    )
                    color = None
                    if mode_id == STATIC_MODE_ID:
                        color = parse_group_color(
                            self._receiver_read_light_table(device),
                            mode_id,
                        )
                return LightingState(
                    mode=parse_mode_name(mode_id),
                    brightness=brightness_percent,
                    per_key_rgb_supported=True,
                    color=color,
                    verification_status=LightingVerificationStatus.UNVERIFIED,
                )
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
        return self._has_vendor_hid() or self._has_receiver_hid()

    def configurable(self) -> bool:
        return self._has_vendor_hid() or self._has_receiver_hid()

    def _has_vendor_hid(self) -> bool:
        try:
            self._resolve_path()
        except LightingHardwareUnavailableError:
            return False
        return True

    def transport_kind(self) -> str:
        if self._has_vendor_hid():
            return "vendor_hid"
        if self._has_receiver_hid():
            return "wireless_receiver"
        return "none"

    def supported_devices(self) -> list[str]:
        return ["Kreo Swarm"] if self.is_connected() else []

    def supports_profiles(self) -> bool:
        return False

    def read_profiles(self) -> ProfilesPayload:
        return unsupported_profiles_payload(
            "Bytech transport does not expose hardware profile slots"
        )

    def read_profile(self) -> bytes:
        with self._open_device() as device:
            return self._read_profile(device)

    def read_key_records(self) -> list[BytechKeyRecord]:
        with self._open_device() as device:
            return self._read_key_records(device)

    def read_keymap(self) -> KeymapPayload:
        try:
            with self._open_device() as device:
                return self._read_keymap_from_device(device)
        except LightingHardwareUnavailableError:
            try:
                with self._open_receiver_device() as device:
                    return self._read_keymap_from_receiver(device)
            except LightingHardwareUnavailableError:
                return StubLightingController().read_keymap()

    def apply_keymap(
        self,
        edits: dict[str, dict[str, int | None]],
    ) -> KeymapPayload:
        try:
            with self._open_device() as device:
                base_records = self._read_key_records_for_layer(device, layer=0)
                fn_records = self._read_key_records_for_layer(device, layer=1)
                self._apply_keymap_edits_to_records(base_records, fn_records, edits)
                self._write_key_records_for_layer(device, layer=0, records=base_records)
                self._write_key_records_for_layer(device, layer=1, records=fn_records)
                return self._read_keymap_from_device(device)
        except LightingHardwareUnavailableError:
            with self._open_receiver_device() as device:
                base_records = self._receiver_read_key_records_for_layer(device, layer=0)
                fn_records = self._receiver_read_key_records_for_layer(device, layer=1)
                self._apply_keymap_edits_to_records(base_records, fn_records, edits)
                self._receiver_write_key_records_for_layer(device, layer=0, records=base_records)
                self._receiver_write_key_records_for_layer(device, layer=1, records=fn_records)
                return self._read_keymap_from_receiver(device)

    def read_macros(self) -> MacrosPayload:
        try:
            with self._open_device() as device:
                return self._read_macros_from_device(device)
        except LightingHardwareUnavailableError:
            return StubLightingController().read_macros()

    def apply_macro(
        self,
        *,
        slot_id: int,
        request: dict[str, object],
    ) -> MacrosPayload:
        try:
            upsert_request = MacroUpsertRequest.model_validate(request)
        except Exception as exc:  # pragma: no cover - converted to protocol error for API
            raise LightingProtocolError("invalid macro request payload") from exc

        try:
            with self._open_device() as device:
                groups = parse_macro_headers(self._read_macro_blob(device))
                if slot_id < 0 or slot_id > len(groups) or slot_id >= MAX_MACRO_SLOTS:
                    raise LightingProtocolError(f"macro slot {slot_id} is unavailable")

                encoded_group = encode_macro_group_data(upsert_request)
                group_list = list(groups)
                if slot_id == len(group_list):
                    group_list.append(bytes([0, 0, len(encoded_group), 0, *encoded_group]))
                else:
                    header_start = group_list[slot_id][0]
                    group_list[slot_id] = bytes(
                        [header_start, 0, len(encoded_group), 0, *encoded_group]
                    )
                self._normalize_macro_group_headers(group_list)
                self._write_macro_blob(device, assemble_macro_groups(group_list))

                if upsert_request.bound_ui_key is not None:
                    base_records = self._read_key_records_for_layer(device, layer=0)
                    self._bind_macro_to_ui_key(
                        base_records,
                        ui_key=upsert_request.bound_ui_key,
                        slot_id=slot_id,
                        execution_type=upsert_request.execution_type,
                        cycle_times=upsert_request.cycle_times,
                    )
                    self._write_key_records_for_layer(device, layer=0, records=base_records)

                return self._read_macros_from_device(device)
        except LightingHardwareUnavailableError as exc:
            raise LightingProtocolError("macros require wired USB mode on this keyboard") from exc

    def delete_macro(self, slot_id: int) -> MacrosPayload:
        try:
            with self._open_device() as device:
                groups = parse_macro_headers(self._read_macro_blob(device))
                if slot_id < 0 or slot_id >= len(groups):
                    raise LightingProtocolError(f"macro slot {slot_id} is unavailable")
                updated_groups = [group for index, group in enumerate(groups) if index != slot_id]
                self._normalize_macro_group_headers(updated_groups)
                self._write_macro_blob(device, assemble_macro_groups(updated_groups))

                base_records = self._read_key_records_for_layer(device, layer=0)
                self._delete_macro_bindings(base_records, slot_id=slot_id)
                self._write_key_records_for_layer(device, layer=0, records=base_records)
                return self._read_macros_from_device(device)
        except LightingHardwareUnavailableError as exc:
            raise LightingProtocolError("macros require wired USB mode on this keyboard") from exc

    def read_per_key_state(self) -> PerKeyLightingPayload:
        try:
            with self._open_device() as device:
                return self._read_per_key_state_from_device(device)
        except LightingHardwareUnavailableError:
            try:
                with self._open_receiver_device() as device:
                    return self._read_per_key_state_from_receiver(device)
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

        try:
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
        except LightingHardwareUnavailableError:
            with self._open_receiver_device() as device:
                return self._apply_per_key_colors_by_ui_key_to_receiver(
                    device,
                    normalized_edits,
                )

    def apply_global_lighting(self, request: LightingApplyRequest) -> LightingState:
        requested_mode_id = parse_mode_id_from_name(request.mode)
        requested_brightness = request.brightness if request.brightness is not None else 80
        device_brightness = percent_to_device_brightness(requested_brightness)

        try:
            with self._open_device() as device:
                profile = self._read_profile(device)
                speed_source_mode = (
                    requested_mode_id
                    if requested_mode_id not in {0, CUSTOM_MODE_ID}
                    else STATIC_MODE_ID
                )
                current_speed = parse_effect_speed(profile, speed_source_mode)

                updated_profile = build_profile_write(
                    profile,
                    mode_id=requested_mode_id,
                    brightness_level=device_brightness,
                    speed=current_speed,
                    effect_type=(
                        1
                        if request.color is not None or requested_mode_id == STATIC_MODE_ID
                        else parse_effect_type(profile, speed_source_mode)
                    ),
                )
                self._write_profile(device, updated_profile)

                if request.color is not None and requested_mode_id == STATIC_MODE_ID:
                    current_table = self._read_light_table(device)
                    updated_table = update_group_color(
                        current_table,
                        STATIC_MODE_ID,
                        hex_to_rgb(request.color),
                    )
                    self._write_light_table(device, updated_table)

                verification_status = self._verify_state(
                    device=device,
                    mode_id=requested_mode_id,
                    brightness_level=device_brightness,
                    color=request.color,
                )
        except LightingHardwareUnavailableError:
            with self._open_receiver_device() as device:
                profile = self._receiver_read_profile(device)
                speed_source_mode = (
                    requested_mode_id
                    if requested_mode_id not in {0, CUSTOM_MODE_ID}
                    else STATIC_MODE_ID
                )
                current_speed = parse_effect_speed(profile, speed_source_mode)
                updated_profile = build_profile_write(
                    profile,
                    mode_id=requested_mode_id,
                    brightness_level=device_brightness,
                    speed=current_speed,
                    effect_type=(
                        1
                        if request.color is not None or requested_mode_id == STATIC_MODE_ID
                        else parse_effect_type(profile, speed_source_mode)
                    ),
                )
                self._receiver_write_profile(device, updated_profile)

                if request.color is not None and requested_mode_id == STATIC_MODE_ID:
                    current_table = self._receiver_read_light_table(device)
                    updated_table = update_group_color(
                        current_table,
                        STATIC_MODE_ID,
                        hex_to_rgb(request.color),
                    )
                    self._receiver_write_light_table(device, updated_table)

                verification_status = self._verify_receiver_state(
                    device=device,
                    mode_id=requested_mode_id,
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
        mode_id: int,
        brightness_level: int,
        color: str | None,
    ) -> LightingVerificationStatus:
        try:
            profile = self._read_profile(device)
            verified_mode = parse_mode_id(profile)
            if verified_mode != mode_id:
                return LightingVerificationStatus.FAILED

            if mode_id not in {0, CUSTOM_MODE_ID}:
                verified_brightness = parse_effect_brightness(profile, mode_id)
                if verified_brightness != brightness_level:
                    return LightingVerificationStatus.FAILED

            if color is not None and mode_id == STATIC_MODE_ID:
                expected_color = normalize_hex_color(color)
                verified_color = parse_group_color(self._read_light_table(device), STATIC_MODE_ID)
                if verified_color != expected_color:
                    return LightingVerificationStatus.FAILED
        except LightingProtocolError:
            return LightingVerificationStatus.FAILED
        except LightingHardwareUnavailableError:
            return LightingVerificationStatus.UNVERIFIED

        return LightingVerificationStatus.VERIFIED

    def _read_keymap_from_device(self, device: HidFeatureDevice) -> KeymapPayload:
        base_records = self._read_key_records_for_layer(device, layer=0)
        fn_records = self._read_key_records_for_layer(device, layer=1)
        try:
            macros = self._read_macros_from_device(device, base_records=base_records)
            macro_slots = macros["slots"]
        except (LightingProtocolError, IndexError):
            macro_slots = []
        return self._build_keymap_payload(base_records, fn_records, macro_slots)

    def _read_keymap_from_receiver(self, device: HidFeatureDevice) -> KeymapPayload:
        base_records = self._receiver_read_key_records_for_layer(device, layer=0)
        fn_records = self._receiver_read_key_records_for_layer(device, layer=1)
        return self._build_keymap_payload(base_records, fn_records, [])

    def _read_macros_from_device(
        self,
        device: HidFeatureDevice,
        *,
        base_records: list[BytechKeyRecord] | None = None,
    ) -> MacrosPayload:
        if base_records is None:
            base_records = self._read_key_records_for_layer(device, layer=0)
        groups = parse_macro_headers(self._read_macro_blob(device))
        bound_keys_by_slot: dict[int, list[str]] = {}
        execution_by_slot: dict[int, tuple[str, int]] = {}
        for record in base_records:
            if ((record.value >> 24) & 0xFF) != 3:
                continue
            slot_id = record.value & 0xFF
            execution_type = decode_macro_execution_type((record.value >> 16) & 0xFF)
            cycle_times = max(1, (record.value >> 8) & 0xFF)
            asset_key = next(
                (
                    entry
                    for entry in load_swarm75_led_map()
                    if entry.protocol_pos == record.pos
                ),
                None,
            )
            if asset_key is None:
                continue
            bound_keys_by_slot.setdefault(slot_id, []).append(asset_key.ui_key)
            execution_by_slot.setdefault(slot_id, (execution_type, cycle_times))

        slots = []
        for slot_id, group in enumerate(groups):
            execution_type, cycle_times = execution_by_slot.get(
                slot_id,
                ("FIXED_COUNT", 1),
            )
            slots.append(
                decode_macro_group(
                    slot_id,
                    group,
                    bound_ui_keys=bound_keys_by_slot.get(slot_id, []),
                    execution_type=execution_type,
                    cycle_times=cycle_times,
                ).model_dump()
            )

        return {
            "supported": True,
            "reason": None,
            "verification_status": LightingVerificationStatus.VERIFIED.value,
            "next_slot_id": min(len(slots), MAX_MACRO_SLOTS),
            "max_slots": MAX_MACRO_SLOTS,
            "slots": slots,
        }

    def _build_keymap_payload(
        self,
        base_records: list[BytechKeyRecord],
        fn_records: list[BytechKeyRecord],
        macro_slots: list[dict[str, object]],
    ) -> KeymapPayload:
        base_by_pos = {record.pos: record for record in base_records}
        fn_by_pos = {record.pos: record for record in fn_records}

        assignments = [
            self._build_key_assignment_payload(asset_key, base_by_pos, fn_by_pos)
            for asset_key in load_swarm75_led_map()
        ]

        return {
            "verification_status": LightingVerificationStatus.UNVERIFIED.value,
            "assignments": assignments,
            "available_actions": [
                option.model_dump()
                for option in [
                    *build_keymap_action_catalog(),
                    *build_macro_action_options(macro_slots),
                ]
            ],
        }

    def _normalize_macro_group_headers(self, groups: list[bytes]) -> None:
        offset = len(groups) * 4
        for index, group in enumerate(list(groups)):
            payload = group[4:]
            groups[index] = bytes([offset, 0, len(payload), 0, *payload])
            offset += len(payload)

    def _bind_macro_to_ui_key(
        self,
        records: list[BytechKeyRecord],
        *,
        ui_key: str,
        slot_id: int,
        execution_type: str,
        cycle_times: int,
    ) -> None:
        asset_key = next(
            (entry for entry in load_swarm75_led_map() if entry.ui_key == ui_key),
            None,
        )
        if asset_key is None:
            raise LightingProtocolError(f"macro binding target {ui_key!r} is unavailable")

        binding_value = encode_macro_binding_value(
            slot_id,
            execution_type=execution_type,
            cycle_times=cycle_times,
        )
        current = next((record for record in records if record.pos == asset_key.protocol_pos), None)
        if current is None:
            records.append(
                BytechKeyRecord(
                    value=binding_value,
                    pos=asset_key.protocol_pos,
                    effect_pos=0,
                    light_pos=0,
                )
            )
            return

        records[records.index(current)] = BytechKeyRecord(
            value=binding_value,
            pos=current.pos,
            effect_pos=current.effect_pos,
            light_pos=current.light_pos,
        )

    def _delete_macro_bindings(
        self,
        records: list[BytechKeyRecord],
        *,
        slot_id: int,
    ) -> None:
        for index, record in enumerate(list(records)):
            if ((record.value >> 24) & 0xFF) != 3:
                continue
            current_slot = record.value & 0xFF
            if current_slot == slot_id:
                records[index] = BytechKeyRecord(
                    value=0,
                    pos=record.pos,
                    effect_pos=record.effect_pos,
                    light_pos=record.light_pos,
                )
            elif current_slot > slot_id:
                records[index] = BytechKeyRecord(
                    value=(record.value & 0xFFFFFF00) | ((current_slot - 1) & 0xFF),
                    pos=record.pos,
                    effect_pos=record.effect_pos,
                    light_pos=record.light_pos,
                )

    def _build_key_assignment_payload(
        self,
        asset_key: ReceiverLedMapKey,
        base_by_pos: dict[int, BytechKeyRecord],
        fn_by_pos: dict[int, BytechKeyRecord],
    ) -> dict[str, object]:
        empty_record = BytechKeyRecord(0, asset_key.protocol_pos, 0, 0)
        base_record = base_by_pos.get(asset_key.protocol_pos, empty_record)
        fn_record = fn_by_pos.get(asset_key.protocol_pos, empty_record)
        return KeyAssignment(
            ui_key=asset_key.ui_key,
            logical_id=asset_key.logical_id,
            svg_id=asset_key.svg_id,
            label=asset_key.label,
            protocol_pos=asset_key.protocol_pos,
            base_action=decode_key_action(base_record.value),
            fn_action=decode_key_action(fn_record.value),
        ).model_dump()

    def _apply_keymap_edits_to_records(
        self,
        base_records: list[BytechKeyRecord],
        fn_records: list[BytechKeyRecord],
        edits: dict[str, dict[str, int | None]],
    ) -> None:
        asset_keys = {entry.ui_key: entry for entry in load_swarm75_led_map()}
        base_by_pos = {record.pos: record for record in base_records}
        fn_by_pos = {record.pos: record for record in fn_records}

        for ui_key, edit in edits.items():
            asset_key = asset_keys.get(ui_key)
            if asset_key is None:
                raise LightingProtocolError(f"keymap target {ui_key!r} is unavailable")

            base_raw_value = edit.get("base_raw_value")
            if base_raw_value is not None:
                raw_value = int(base_raw_value)
                current = base_by_pos.get(asset_key.protocol_pos)
                if current is None:
                    base_records.append(
                        BytechKeyRecord(
                            value=raw_value,
                            pos=asset_key.protocol_pos,
                            effect_pos=0,
                            light_pos=0,
                        )
                    )
                else:
                    base_records[base_records.index(current)] = BytechKeyRecord(
                        value=raw_value,
                        pos=current.pos,
                        effect_pos=current.effect_pos,
                        light_pos=current.light_pos,
                    )

            fn_raw_value = edit.get("fn_raw_value")
            if fn_raw_value is not None:
                raw_value = int(fn_raw_value)
                current = fn_by_pos.get(asset_key.protocol_pos)
                if current is None:
                    fn_records.append(
                        BytechKeyRecord(
                            value=raw_value,
                            pos=asset_key.protocol_pos,
                            effect_pos=0,
                            light_pos=0,
                        )
                    )
                else:
                    fn_records[fn_records.index(current)] = BytechKeyRecord(
                        value=raw_value,
                        pos=current.pos,
                        effect_pos=current.effect_pos,
                        light_pos=current.light_pos,
                    )

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

    def _read_per_key_state_from_receiver(
        self,
        device: HidFeatureDevice,
    ) -> PerKeyLightingPayload:
        profile = self._receiver_read_profile(device)
        mode_id = parse_mode_id(profile)
        brightness = device_to_percent_brightness(
            parse_effect_brightness(
                profile,
                STATIC_MODE_ID if mode_id == CUSTOM_MODE_ID else mode_id,
            )
        )
        keys: list[PerKeyLightingEntryPayload]

        if mode_id == CUSTOM_MODE_ID:
            custom_frame = self._receiver_read_custom_light_frame(device)
            keys = [
                {
                    "ui_key": entry.ui_key,
                    "label": entry.label,
                    "light_pos": 8 + (entry.led_index * 4),
                    "color": parse_receiver_custom_light_color(
                        custom_frame,
                        entry.led_index,
                    ),
                }
                for entry in load_swarm75_led_map()
            ]
        else:
            default_color = DEFAULT_KEYCAP_COLOR
            if mode_id == STATIC_MODE_ID:
                static_color = parse_group_color(
                    self._receiver_read_light_table(device),
                    STATIC_MODE_ID,
                )
                if static_color is not None:
                    default_color = static_color
            keys = [
                {
                    "ui_key": entry.ui_key,
                    "label": entry.label,
                    "light_pos": 8 + (entry.led_index * 4),
                    "color": default_color,
                }
                for entry in load_swarm75_led_map()
            ]

        return {
            "mode": parse_mode_name(mode_id),
            "brightness": brightness,
            "per_key_rgb_supported": True,
            "verification_status": LightingVerificationStatus.UNVERIFIED.value,
            "keys": keys,
        }

    def _apply_per_key_colors_by_ui_key_to_receiver(
        self,
        device: HidFeatureDevice,
        edits: dict[str, str],
    ) -> PerKeyLightingPayload:
        profile = self._receiver_read_profile(device)
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
            self._receiver_write_profile(device, updated_profile)

        frame = self._receiver_read_custom_light_frame(device)
        led_entries = {entry.ui_key: entry for entry in load_swarm75_led_map()}
        for ui_key, color in edits.items():
            entry = led_entries.get(ui_key)
            if entry is None:
                raise LightingProtocolError(f"per-key lighting target {ui_key!r} is unavailable")
            frame = update_receiver_frame_color(frame, entry.led_index, hex_to_rgb(color))

        self._receiver_write_custom_light_frame(device, frame)

        return {
            "mode": "custom",
            "brightness": device_to_percent_brightness(current_brightness),
            "per_key_rgb_supported": True,
            "verification_status": LightingVerificationStatus.UNVERIFIED.value,
            "keys": [
                {
                    "ui_key": entry.ui_key,
                    "label": entry.label,
                    "light_pos": 8 + (entry.led_index * 4),
                    "color": parse_receiver_custom_light_color(frame, entry.led_index),
                }
                for entry in load_swarm75_led_map()
            ],
        }

    def _read_profile(self, device: HidFeatureDevice) -> bytes:
        response = self._exchange_command(
            device=device,
            command=PROFILE_READ_COMMAND,
            response_length=8 + PROFILE_SIZE,
            min_response_length=8 + PROFILE_SIZE,
        )
        return response[-PROFILE_SIZE:]

    def _read_key_records(self, device: HidFeatureDevice) -> list[BytechKeyRecord]:
        return self._read_key_records_for_layer(device, layer=0)

    def _read_key_records_for_layer(
        self,
        device: HidFeatureDevice,
        *,
        layer: int,
    ) -> list[BytechKeyRecord]:
        command = bytes([0x83, 0x00, layer & 0xFF, 0x01, 0x00, 0xF8, 0x01])
        response = self._exchange_command(
            device=device,
            command=command,
            response_length=FEATURE_REPORT_SIZE,
            min_response_length=8,
        )
        return parse_key_records(response[8:])

    def _write_key_records_for_layer(
        self,
        device: HidFeatureDevice,
        *,
        layer: int,
        records: list[BytechKeyRecord],
    ) -> None:
        payload = build_key_records_payload(records)
        command = bytes([0x03, 0x00, layer & 0xFF, 0x01, 0x00, 0xF8, 0x01])
        self._send_command(device, command + payload)

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

    def _read_macro_blob(self, device: HidFeatureDevice) -> bytes:
        response = self._exchange_command(
            device=device,
            command=MACRO_READ_COMMAND,
            response_length=FEATURE_REPORT_SIZE,
            min_response_length=8,
        )
        return response[8:]

    def _write_macro_blob(self, device: HidFeatureDevice, blob: bytes) -> None:
        truncated = blob.rstrip(b"\x00")
        padded = bytes([*truncated, *([0] * (512 - len(truncated)))])[:512]
        self._send_command(device, MACRO_WRITE_COMMAND + padded)

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

    def _receiver_read_profile(self, device: HidFeatureDevice) -> bytes:
        return self._receiver_read_packet_sequence(
            device=device,
            command=WIRELESS_PROFILE_READ_COMMAND,
            response_command=WIRELESS_PROFILE_READ_COMMAND,
            expected_size=PROFILE_SIZE,
        )

    def _receiver_read_key_records_for_layer(
        self,
        device: HidFeatureDevice,
        *,
        layer: int,
    ) -> list[BytechKeyRecord]:
        payload = self._receiver_read_packet_sequence(
            device=device,
            command=65,
            response_command=65,
            expected_size=KEYMAP_PAYLOAD_SIZE,
            query_payload=bytes([65, layer & 0xFF, 0, 0, 0, 0, 0]),
        )
        return parse_key_records(payload)

    def _receiver_write_key_records_for_layer(
        self,
        device: HidFeatureDevice,
        *,
        layer: int,
        records: list[BytechKeyRecord],
    ) -> None:
        payload = bytes([layer & 0xFF, 0, 0, 0, 0, 0, *build_key_records_payload(records)])
        self._receiver_send_chunked_command(
            device=device,
            command=1,
            payload=payload,
        )

    def _receiver_read_light_table(self, device: HidFeatureDevice) -> bytes:
        return self._receiver_read_packet_sequence(
            device=device,
            command=WIRELESS_LIGHT_TABLE_READ_COMMAND,
            response_command=WIRELESS_LIGHT_TABLE_READ_COMMAND,
            expected_size=LIGHT_TABLE_SIZE,
        )

    def _receiver_read_custom_light_frame(self, device: HidFeatureDevice) -> bytes:
        return self._receiver_read_packet_sequence(
            device=device,
            command=WIRELESS_CUSTOM_LIGHT_READ_COMMAND,
            response_command=WIRELESS_CUSTOM_LIGHT_WRITE_COMMAND,
            expected_size=CUSTOM_LIGHT_FRAME_SIZE,
        )

    def _receiver_write_profile(self, device: HidFeatureDevice, profile: bytes) -> None:
        if len(profile) != PROFILE_SIZE:
            raise LightingProtocolError("receiver profile write requires exactly 128 bytes")
        self._receiver_send_chunked_command(
            device=device,
            command=WIRELESS_PROFILE_WRITE_COMMAND,
            payload=profile,
        )

    def _receiver_write_light_table(self, device: HidFeatureDevice, light_table: bytes) -> None:
        if len(light_table) != LIGHT_TABLE_SIZE:
            raise LightingProtocolError("receiver light-table write requires exactly 480 bytes")
        self._receiver_send_chunked_command(
            device=device,
            command=WIRELESS_LIGHT_TABLE_WRITE_COMMAND,
            payload=pad_receiver_payload(light_table, WIRELESS_PADDING_SIZE),
        )

    def _receiver_write_custom_light_frame(self, device: HidFeatureDevice, frame: bytes) -> None:
        if len(frame) != CUSTOM_LIGHT_FRAME_SIZE:
            raise LightingProtocolError(
                f"receiver custom light frame requires exactly {CUSTOM_LIGHT_FRAME_SIZE} bytes"
            )
        self._receiver_send_query(
            device,
            bytes([WIRELESS_CUSTOM_LIGHT_READ_COMMAND, 0, 0, 0, 0, 0, 0]),
        )
        _ = device.read(64, 2000)
        time.sleep(0.2)
        self._receiver_send_chunked_command(
            device=device,
            command=WIRELESS_CUSTOM_LIGHT_WRITE_COMMAND,
            payload=pad_receiver_payload(frame, WIRELESS_PADDING_SIZE),
        )

    def _receiver_read_packet_sequence(
        self,
        *,
        device: HidFeatureDevice,
        command: int,
        response_command: int,
        expected_size: int,
        query_payload: bytes | None = None,
    ) -> bytes:
        self._receiver_send_query(
            device,
            query_payload if query_payload is not None else bytes([command, 0, 0, 0, 0, 0, 0]),
        )
        packets: dict[int, bytes] = {}
        total_packets: int | None = None
        deadline = time.monotonic() + 2.0
        while total_packets is None or len(packets) < total_packets:
            if time.monotonic() > deadline:
                raise LightingProtocolError(
                    f"timed out waiting for receiver response to command {command}"
                )
            packet = bytes(device.read(64, 200))
            if len(packet) == 0:
                continue
            payload = packet[1:] if packet[0] == WIRELESS_REPORT_ID else packet
            if len(payload) < 5 or payload[0] != response_command:
                continue
            total_packets = payload[1]
            packets[payload[2]] = payload[4:-1]
        assembled = b"".join(packets[index] for index in range(total_packets or 0))
        return assembled[:expected_size]

    def _receiver_send_query(self, device: HidFeatureDevice, payload: bytes) -> None:
        padded_payload = bytes(
            [*payload, *([0] * max(0, WIRELESS_REPORT_SIZE - len(payload)))]
        )[:WIRELESS_REPORT_SIZE]
        bytes_sent = device.write(bytes([WIRELESS_REPORT_ID, *padded_payload]))
        if bytes_sent <= 0:
            raise LightingHardwareUnavailableError("failed to send receiver report to keyboard")

    def _receiver_send_chunked_command(
        self,
        *,
        device: HidFeatureDevice,
        command: int,
        payload: bytes,
    ) -> None:
        total_chunks = max(
            1,
            (len(payload) + WIRELESS_PACKET_CHUNK_SIZE - 1)
            // WIRELESS_PACKET_CHUNK_SIZE,
        )
        for index in range(total_chunks):
            start = index * WIRELESS_PACKET_CHUNK_SIZE
            chunk = payload[start : start + WIRELESS_PACKET_CHUNK_SIZE]
            padded_chunk = bytes(
                [*chunk, *([0] * (WIRELESS_PACKET_CHUNK_SIZE - len(chunk)))]
            )
            length_byte = len(chunk)
            if index == total_chunks - 1 and len(chunk) == WIRELESS_PACKET_CHUNK_SIZE:
                length_byte = 2
            body = bytes([command, total_chunks & 0xFF, index & 0xFF, length_byte, *padded_chunk])
            checksum = (WIRELESS_REPORT_ID + sum(body)) & 0xFF
            bytes_sent = device.write(bytes([WIRELESS_REPORT_ID, *body, checksum]))
            if bytes_sent <= 0:
                raise LightingHardwareUnavailableError("failed to send receiver chunk to keyboard")

    def _verify_receiver_state(
        self,
        *,
        device: HidFeatureDevice,
        mode_id: int,
        brightness_level: int,
        color: str | None,
    ) -> LightingVerificationStatus:
        try:
            profile = self._receiver_read_profile(device)
            verified_mode = parse_mode_id(profile)
            if verified_mode != mode_id:
                return LightingVerificationStatus.FAILED

            if mode_id not in {0, CUSTOM_MODE_ID}:
                verified_brightness = parse_effect_brightness(profile, mode_id)
                if verified_brightness != brightness_level:
                    return LightingVerificationStatus.FAILED

            if color is not None and mode_id == STATIC_MODE_ID:
                expected_color = normalize_hex_color(color)
                verified_color = parse_group_color(
                    self._receiver_read_light_table(device),
                    STATIC_MODE_ID,
                )
                if verified_color != expected_color:
                    return LightingVerificationStatus.FAILED
        except LightingProtocolError:
            return LightingVerificationStatus.FAILED
        except LightingHardwareUnavailableError:
            return LightingVerificationStatus.UNVERIFIED

        return LightingVerificationStatus.VERIFIED

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

    def _resolve_receiver_path(self) -> bytes:
        if self._receiver_path is not None:
            return self._receiver_path
        return self._receiver_path_provider()

    def _has_receiver_hid(self) -> bool:
        try:
            self._resolve_receiver_path()
        except LightingHardwareUnavailableError:
            return False
        return True

    def _open_device(self) -> _OpenedFeatureDevice:
        return _OpenedFeatureDevice(self._resolve_path(), self._device_factory)

    def _open_receiver_device(self) -> _OpenedFeatureDevice:
        return _OpenedFeatureDevice(self._resolve_receiver_path(), self._device_factory)


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
