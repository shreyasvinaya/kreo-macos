from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import pytest

from kreo_kontrol.tools.modifier_capture import (
    CapturedEvent,
    CapturedTarget,
    CaptureMetadata,
    build_assignment_snapshot,
    build_capture_payload,
    build_default_targets,
    run_guided_capture,
    write_capture_payload,
)


class StubController:
    def __init__(self) -> None:
        self.payload: dict[str, object] = {
            "verification_status": "verified",
            "assignments": [
                {
                    "ui_key": "left_ctrl",
                    "base_action": {"label": "Control Left", "raw_value": 0x00010000},
                    "fn_action": {"label": "Control Left", "raw_value": 0x00010000},
                },
                {
                    "ui_key": "left_opt",
                    "base_action": {"label": "Alt Left", "raw_value": 0x00040000},
                    "fn_action": {"label": "Alt Left", "raw_value": 0x00040000},
                },
                {
                    "ui_key": "left_cmd",
                    "base_action": {"label": "Win Left", "raw_value": 0x00080000},
                    "fn_action": {"label": "Win Left", "raw_value": 0x00080000},
                },
                {
                    "ui_key": "right_opt",
                    "base_action": {"label": "Alt Right", "raw_value": 0x00400000},
                    "fn_action": {"label": "Alt Right", "raw_value": 0x00400000},
                },
                {
                    "ui_key": "right_ctrl",
                    "base_action": {"label": "Control Right", "raw_value": 0x00100000},
                    "fn_action": {"label": "Mission Control", "raw_value": 0x020000CD},
                },
            ],
            "available_actions": [],
        }

    def read_keymap(self) -> Mapping[str, object]:
        return self.payload

    def supported_devices(self) -> list[str]:
        return ["Kreo Swarm"]

    def transport_kind(self) -> str:
        return "wireless_receiver"


class StubEventSource:
    def __init__(self, events_by_key: dict[str, CapturedEvent | None]) -> None:
        self.events_by_key = events_by_key

    def capture_target_event(
        self, target_ui_key: str, timeout_seconds: float
    ) -> CapturedEvent | None:
        assert timeout_seconds == 3.0
        return self.events_by_key[target_ui_key]


def test_build_default_targets_keeps_modifier_order_and_marks_fn_optional() -> None:
    targets = build_default_targets()

    assert [target.ui_key for target in targets] == [
        "left_ctrl",
        "left_opt",
        "left_cmd",
        "right_opt",
        "right_ctrl",
        "fn",
    ]
    assert targets[-1].optional is True


def test_build_assignment_snapshot_reads_matching_target_assignment() -> None:
    snapshot = build_assignment_snapshot(StubController(), "right_ctrl")

    assert snapshot["ui_key"] == "right_ctrl"
    assert snapshot["base_assignment_label"] == "Control Right"
    assert snapshot["base_assignment_raw_value"] == 0x00100000
    assert snapshot["fn_assignment_label"] == "Mission Control"
    assert snapshot["fn_assignment_raw_value"] == 0x020000CD


def test_build_capture_payload_records_results_and_skipped_targets() -> None:
    metadata = CaptureMetadata(
        keyboard_name="Kreo Swarm",
        generated_at="2026-04-03T17:10:00Z",
        transport="wired",
    )
    payload = build_capture_payload(
        metadata=metadata,
        captured_targets=[
            CapturedTarget(
                requested_target="right_ctrl",
                ui_key="right_ctrl",
                event_type="flagsChanged",
                macos_keycode=62,
                macos_flags=0x2000,
                characters=None,
                characters_ignoring_modifiers=None,
                timestamp=12.5,
                assignment_label="Control Right",
                assignment_raw_value=0x00100000,
                fn_assignment_label=None,
                fn_assignment_raw_value=None,
                unsupported_reason=None,
            )
        ],
        skipped_targets={"fn": "event tap did not expose fn"},
    )

    assert payload["metadata"]["keyboard_name"] == "Kreo Swarm"
    assert payload["targets"][0]["ui_key"] == "right_ctrl"
    assert payload["skipped_targets"]["fn"] == "event tap did not expose fn"


def test_run_guided_capture_collects_targets_and_skips_optional_fn() -> None:
    events = {
        "left_ctrl": CapturedEvent(
            event_type="flagsChanged",
            keycode=59,
            flags=0x1,
            characters=None,
            characters_ignoring_modifiers=None,
            timestamp=1.0,
        ),
        "left_opt": CapturedEvent(
            event_type="flagsChanged",
            keycode=58,
            flags=0x20,
            characters=None,
            characters_ignoring_modifiers=None,
            timestamp=2.0,
        ),
        "left_cmd": CapturedEvent(
            event_type="flagsChanged",
            keycode=55,
            flags=0x8,
            characters=None,
            characters_ignoring_modifiers=None,
            timestamp=3.0,
        ),
        "right_opt": CapturedEvent(
            event_type="flagsChanged",
            keycode=61,
            flags=0x40,
            characters=None,
            characters_ignoring_modifiers=None,
            timestamp=4.0,
        ),
        "right_ctrl": CapturedEvent(
            event_type="flagsChanged",
            keycode=62,
            flags=0x10,
            characters=None,
            characters_ignoring_modifiers=None,
            timestamp=5.0,
        ),
        "fn": None,
    }
    prompts: list[str] = []

    payload = run_guided_capture(
        controller=StubController(),
        event_source=StubEventSource(events),
        timeout_seconds=3.0,
        prompt_sink=prompts.append,
        generated_at="2026-04-03T17:10:00Z",
    )

    assert payload["metadata"]["keyboard_name"] == "Kreo Swarm"
    assert payload["metadata"]["transport"] == "wireless_receiver"
    assert [entry["ui_key"] for entry in payload["targets"]] == [
        "left_ctrl",
        "left_opt",
        "left_cmd",
        "right_opt",
        "right_ctrl",
    ]
    assert payload["skipped_targets"] == {"fn": "No observable event captured within timeout"}
    assert prompts[0] == "Press Left Control"


def test_run_guided_capture_raises_for_required_target_timeout() -> None:
    events = {
        "left_ctrl": None,
        "left_opt": None,
        "left_cmd": None,
        "right_opt": None,
        "right_ctrl": None,
        "fn": None,
    }

    with pytest.raises(TimeoutError, match="left_ctrl"):
        run_guided_capture(
            controller=StubController(),
            event_source=StubEventSource(events),
            timeout_seconds=3.0,
            prompt_sink=lambda _message: None,
            generated_at="2026-04-03T17:10:00Z",
        )


def test_write_capture_payload_uses_json_file(tmp_path: Path) -> None:
    payload = {"metadata": {"generated_at": "2026-04-03T17:10:00Z"}, "targets": []}

    output_path = write_capture_payload(
        payload,
        output_dir=tmp_path,
        filename="modifier-capture-test.json",
    )

    assert output_path.name == "modifier-capture-test.json"
    assert json.loads(output_path.read_text())["metadata"]["generated_at"] == "2026-04-03T17:10:00Z"
