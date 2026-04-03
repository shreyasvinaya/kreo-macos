from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from typing import Any, Protocol, TypedDict, cast

from kreo_kontrol.device.bytech_lighting import build_default_lighting_controller


@dataclass(frozen=True)
class CaptureTarget:
    ui_key: str
    prompt: str
    optional: bool = False


@dataclass(frozen=True)
class CaptureMetadata:
    keyboard_name: str
    generated_at: str
    transport: str


@dataclass(frozen=True)
class CapturedEvent:
    event_type: str
    keycode: int
    flags: int
    characters: str | None
    characters_ignoring_modifiers: str | None
    timestamp: float


@dataclass(frozen=True)
class CapturedTarget:
    requested_target: str
    ui_key: str
    event_type: str
    macos_keycode: int
    macos_flags: int
    characters: str | None
    characters_ignoring_modifiers: str | None
    timestamp: float
    assignment_label: str | None
    assignment_raw_value: int | None
    fn_assignment_label: str | None
    fn_assignment_raw_value: int | None
    unsupported_reason: str | None


class AssignmentSnapshot(TypedDict):
    ui_key: str
    base_assignment_label: str | None
    base_assignment_raw_value: int | None
    fn_assignment_label: str | None
    fn_assignment_raw_value: int | None


class CapturePayloadMetadata(TypedDict):
    keyboard_name: str
    generated_at: str
    transport: str


class CapturePayloadTarget(TypedDict):
    requested_target: str
    ui_key: str
    event_type: str
    macos_keycode: int
    macos_flags: int
    characters: str | None
    characters_ignoring_modifiers: str | None
    timestamp: float
    assignment_label: str | None
    assignment_raw_value: int | None
    fn_assignment_label: str | None
    fn_assignment_raw_value: int | None
    unsupported_reason: str | None


class CapturePayload(TypedDict):
    metadata: CapturePayloadMetadata
    targets: list[CapturePayloadTarget]
    skipped_targets: dict[str, str]


class KeymapController(Protocol):
    def read_keymap(self) -> Mapping[str, object]:
        ...

    def supported_devices(self) -> list[str]:
        ...

    def transport_kind(self) -> str:
        ...


class ModifierEventSource(Protocol):
    def capture_target_event(
        self, target_ui_key: str, timeout_seconds: float
    ) -> CapturedEvent | None:
        ...


def build_default_targets() -> list[CaptureTarget]:
    return [
        CaptureTarget("left_ctrl", "Press Left Control"),
        CaptureTarget("left_opt", "Press Left Option / Alt"),
        CaptureTarget("left_cmd", "Press Left Command / Win"),
        CaptureTarget("right_opt", "Press Right Option / Alt"),
        CaptureTarget("right_ctrl", "Press Right Control"),
        CaptureTarget("fn", "Press Fn", optional=True),
    ]


def default_output_filename(generated_at: str) -> str:
    timestamp = generated_at.replace("-", "").replace(":", "")
    timestamp = timestamp.replace("T", "-").replace("Z", "")
    return f"modifier-capture-{timestamp}.json"


def build_assignment_snapshot(controller: KeymapController, ui_key: str) -> AssignmentSnapshot:
    payload = controller.read_keymap()
    assignments = payload["assignments"]
    if not isinstance(assignments, list):
        raise TypeError("controller keymap payload must contain a list of assignments")

    for assignment in assignments:
        if not isinstance(assignment, dict):
            continue
        entry = cast(dict[str, object], assignment)
        if entry.get("ui_key") != ui_key:
            continue

        base_action = entry.get("base_action")
        fn_action = entry.get("fn_action")
        if not isinstance(base_action, dict):
            raise TypeError(f"assignment for {ui_key!r} is missing base_action")
        if not isinstance(fn_action, dict):
            raise TypeError(f"assignment for {ui_key!r} is missing fn_action")
        base_action_dict = cast(dict[str, object], base_action)
        fn_action_dict = cast(dict[str, object], fn_action)

        return {
            "ui_key": ui_key,
            "base_assignment_label": _coerce_optional_str(base_action_dict.get("label")),
            "base_assignment_raw_value": _coerce_optional_int(base_action_dict.get("raw_value")),
            "fn_assignment_label": _coerce_optional_str(fn_action_dict.get("label")),
            "fn_assignment_raw_value": _coerce_optional_int(fn_action_dict.get("raw_value")),
        }

    raise KeyError(ui_key)


def normalize_captured_event(
    *,
    event_type: str,
    keycode: int,
    flags: int,
    characters: str | None,
    characters_ignoring_modifiers: str | None,
    timestamp: float,
) -> CapturedEvent:
    return CapturedEvent(
        event_type=event_type,
        keycode=keycode,
        flags=flags,
        characters=characters,
        characters_ignoring_modifiers=characters_ignoring_modifiers,
        timestamp=timestamp,
    )


def should_accept_event_for_target(target_ui_key: str, *, event_type: str) -> bool:
    del target_ui_key
    return event_type == "flagsChanged"


def next_target_prompt(target: CaptureTarget) -> str:
    return target.prompt


def build_capture_payload(
    *,
    metadata: CaptureMetadata,
    captured_targets: list[CapturedTarget],
    skipped_targets: dict[str, str],
) -> CapturePayload:
    return {
        "metadata": {
            "keyboard_name": metadata.keyboard_name,
            "generated_at": metadata.generated_at,
            "transport": metadata.transport,
        },
        "targets": [
            {
                "requested_target": target.requested_target,
                "ui_key": target.ui_key,
                "event_type": target.event_type,
                "macos_keycode": target.macos_keycode,
                "macos_flags": target.macos_flags,
                "characters": target.characters,
                "characters_ignoring_modifiers": target.characters_ignoring_modifiers,
                "timestamp": target.timestamp,
                "assignment_label": target.assignment_label,
                "assignment_raw_value": target.assignment_raw_value,
                "fn_assignment_label": target.fn_assignment_label,
                "fn_assignment_raw_value": target.fn_assignment_raw_value,
                "unsupported_reason": target.unsupported_reason,
            }
            for target in captured_targets
        ],
        "skipped_targets": skipped_targets,
    }


def run_guided_capture(
    *,
    controller: KeymapController,
    event_source: ModifierEventSource,
    timeout_seconds: float,
    prompt_sink: Callable[[str], None],
    generated_at: str,
) -> CapturePayload:
    supported_devices = controller.supported_devices()
    metadata = CaptureMetadata(
        keyboard_name=supported_devices[0] if supported_devices else "Unknown",
        generated_at=generated_at,
        transport=controller.transport_kind(),
    )
    captured_targets: list[CapturedTarget] = []
    skipped_targets: dict[str, str] = {}

    for target in build_default_targets():
        prompt_sink(next_target_prompt(target))
        event = event_source.capture_target_event(target.ui_key, timeout_seconds)
        if event is None:
            if target.optional:
                skipped_targets[target.ui_key] = "No observable event captured within timeout"
                continue
            raise TimeoutError(f"Timed out waiting for target {target.ui_key}")

        assignment = build_assignment_snapshot(controller, target.ui_key)
        captured_targets.append(
            CapturedTarget(
                requested_target=target.ui_key,
                ui_key=target.ui_key,
                event_type=event.event_type,
                macos_keycode=event.keycode,
                macos_flags=event.flags,
                characters=event.characters,
                characters_ignoring_modifiers=event.characters_ignoring_modifiers,
                timestamp=event.timestamp,
                assignment_label=assignment["base_assignment_label"],
                assignment_raw_value=assignment["base_assignment_raw_value"],
                fn_assignment_label=assignment["fn_assignment_label"],
                fn_assignment_raw_value=assignment["fn_assignment_raw_value"],
                unsupported_reason=None,
            )
        )

    return build_capture_payload(
        metadata=metadata,
        captured_targets=captured_targets,
        skipped_targets=skipped_targets,
    )


def write_capture_payload(
    payload: Mapping[str, object], *, output_dir: Path, filename: str
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output_path


class QuartzModifierEventSource:
    def __init__(self) -> None:
        self._quartz = cast(Any, import_module("Quartz"))

    def capture_target_event(
        self, target_ui_key: str, timeout_seconds: float
    ) -> CapturedEvent | None:
        quartz = self._quartz
        captured: CapturedEvent | None = None

        def callback(_proxy: Any, cg_event_type: int, event: Any, _refcon: Any) -> Any:
            nonlocal captured
            event_type = _event_type_name(quartz, cg_event_type)
            if not should_accept_event_for_target(target_ui_key, event_type=event_type):
                return event

            keycode = int(
                quartz.CGEventGetIntegerValueField(event, quartz.kCGKeyboardEventKeycode)
            )
            flags = int(quartz.CGEventGetFlags(event))
            captured = normalize_captured_event(
                event_type=event_type,
                keycode=keycode,
                flags=flags,
                characters=None,
                characters_ignoring_modifiers=None,
                timestamp=time.time(),
            )
            return event

        event_mask = quartz.CGEventMaskBit(quartz.kCGEventFlagsChanged) | quartz.CGEventMaskBit(
            quartz.kCGEventKeyDown
        )
        tap = quartz.CGEventTapCreate(
            quartz.kCGHIDEventTap,
            quartz.kCGHeadInsertEventTap,
            quartz.kCGEventTapOptionListenOnly,
            event_mask,
            callback,
            None,
        )
        if tap is None:
            raise RuntimeError(
                "Unable to create a macOS event tap. "
                "Check Input Monitoring and Accessibility permissions."
            )

        run_loop_source = quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
        run_loop = quartz.CFRunLoopGetCurrent()
        quartz.CFRunLoopAddSource(run_loop, run_loop_source, quartz.kCFRunLoopDefaultMode)
        quartz.CGEventTapEnable(tap, True)

        deadline = time.monotonic() + timeout_seconds
        try:
            while captured is None and time.monotonic() < deadline:
                remaining = max(0.0, deadline - time.monotonic())
                quartz.CFRunLoopRunInMode(
                    quartz.kCFRunLoopDefaultMode,
                    min(0.1, remaining),
                    False,
                )
        finally:
            quartz.CFRunLoopRemoveSource(run_loop, run_loop_source, quartz.kCFRunLoopDefaultMode)
            quartz.CFMachPortInvalidate(tap)

        return captured


def _event_type_name(quartz: Any, cg_event_type: int) -> str:
    if cg_event_type == quartz.kCGEventFlagsChanged:
        return "flagsChanged"
    if cg_event_type == quartz.kCGEventKeyDown:
        return "keyDown"
    return f"event:{cg_event_type}"


def _coerce_optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    raise TypeError(f"expected int or None, got {type(value).__name__}")


def _coerce_optional_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    raise TypeError(f"expected str or None, got {type(value).__name__}")


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kreo-kontrol-capture-modifiers",
        description="Capture modifier/remap key evidence from macOS and the current Kreo keymap.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("captures"),
        help="Directory where the JSON capture file will be written.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=5.0,
        help="Seconds to wait for each target key before failing or skipping optional Fn.",
    )
    parser.add_argument(
        "--filename",
        type=str,
        default=None,
        help="Optional output filename. Defaults to a timestamped modifier-capture-*.json name.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_argument_parser()
    args = parser.parse_args(argv)

    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )
    controller = cast(KeymapController, build_default_lighting_controller())
    payload = run_guided_capture(
        controller=controller,
        event_source=QuartzModifierEventSource(),
        timeout_seconds=args.timeout_seconds,
        prompt_sink=lambda message: print(message, flush=True),
        generated_at=generated_at,
    )
    output_path = write_capture_payload(
        payload,
        output_dir=args.output_dir,
        filename=args.filename or default_output_filename(generated_at),
    )
    print(f"Wrote capture results to {output_path}", flush=True)
    return 0
