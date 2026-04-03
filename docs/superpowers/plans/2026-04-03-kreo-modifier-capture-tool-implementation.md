# Kreo Modifier Capture Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a guided one-shot terminal script that captures the Kreo Swarm modifier/remap keys, writes a JSON evidence file, and stops automatically after every target has been recorded.

**Architecture:** Add a small Python capture module with pure sequencing and serialization helpers plus a thin macOS Quartz event-tap adapter. The script will read the current keymap directly from the existing Bytech controller, prompt the user through the modifier target list, capture one event per target, and write a timestamped JSON file under `captures/`.

**Tech Stack:** Python 3.12, Quartz via PyObjC, existing `bytech_lighting` controller, `pytest`, `ruff`, `ty`

---

## File Structure

- Modify: `pyproject.toml`
  - add the Quartz dependency and a console script entry point for the capture tool
- Modify: `.gitignore`
  - ignore generated capture JSON files while keeping the directory usable
- Create: `src/kreo_kontrol/tools/modifier_capture.py`
  - guided capture runner, pure data helpers, controller integration, CLI entry point
- Create: `tests/tools/test_modifier_capture.py`
  - red-green coverage for target sequencing, payload building, unsupported `fn`, and output shape
- Modify: `README.md`
  - add a short section showing how to run the capture tool and where output is saved

### Task 1: Lock The Capture Model And JSON Output

**Files:**
- Create: `tests/tools/test_modifier_capture.py`
- Create: `src/kreo_kontrol/tools/modifier_capture.py`

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path

from kreo_kontrol.tools.modifier_capture import (
    CaptureMetadata,
    CapturedTarget,
    build_capture_payload,
    build_default_targets,
    write_capture_payload,
)


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


def test_write_capture_payload_uses_timestamped_json_file(tmp_path: Path) -> None:
    payload = {"metadata": {"generated_at": "2026-04-03T17:10:00Z"}, "targets": []}

    output_path = write_capture_payload(payload, output_dir=tmp_path, filename="modifier-capture-test.json")

    assert output_path.name == "modifier-capture-test.json"
    assert output_path.read_text().startswith("{\n")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
uv run --group dev pytest tests/tools/test_modifier_capture.py -q
```

Expected: FAIL because `kreo_kontrol.tools.modifier_capture` does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

```python
from dataclasses import dataclass
from pathlib import Path
import json


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
class CapturedTarget:
    requested_target: str
    ui_key: str
    event_type: str
    macos_keycode: int
    macos_flags: int
    characters: str | None
    characters_ignoring_modifiers: str | None
    assignment_label: str | None
    assignment_raw_value: int | None
    fn_assignment_label: str | None
    fn_assignment_raw_value: int | None
    unsupported_reason: str | None


def build_default_targets() -> list[CaptureTarget]:
    return [
        CaptureTarget("left_ctrl", "Press Left Control"),
        CaptureTarget("left_opt", "Press Left Option / Alt"),
        CaptureTarget("left_cmd", "Press Left Command / Win"),
        CaptureTarget("right_opt", "Press Right Option / Alt"),
        CaptureTarget("right_ctrl", "Press Right Control"),
        CaptureTarget("fn", "Press Fn", optional=True),
    ]


def build_capture_payload(
    *,
    metadata: CaptureMetadata,
    captured_targets: list[CapturedTarget],
    skipped_targets: dict[str, str],
) -> dict[str, object]:
    return {
        "metadata": {
            "keyboard_name": metadata.keyboard_name,
            "generated_at": metadata.generated_at,
            "transport": metadata.transport,
        },
        "targets": [
            {
                "requested_target": entry.requested_target,
                "ui_key": entry.ui_key,
                "event_type": entry.event_type,
                "macos_keycode": entry.macos_keycode,
                "macos_flags": entry.macos_flags,
                "characters": entry.characters,
                "characters_ignoring_modifiers": entry.characters_ignoring_modifiers,
                "assignment_label": entry.assignment_label,
                "assignment_raw_value": entry.assignment_raw_value,
                "fn_assignment_label": entry.fn_assignment_label,
                "fn_assignment_raw_value": entry.fn_assignment_raw_value,
                "unsupported_reason": entry.unsupported_reason,
            }
            for entry in captured_targets
        ],
        "skipped_targets": skipped_targets,
    }


def write_capture_payload(
    payload: dict[str, object], *, output_dir: Path, filename: str
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output_path
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
uv run --group dev pytest tests/tools/test_modifier_capture.py -q
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/tools/test_modifier_capture.py src/kreo_kontrol/tools/modifier_capture.py
git commit -m "feat: add modifier capture payload helpers"
```

### Task 2: Lock Event Normalization And Guided Sequencing

**Files:**
- Modify: `tests/tools/test_modifier_capture.py`
- Modify: `src/kreo_kontrol/tools/modifier_capture.py`

- [ ] **Step 1: Write the failing tests**

```python
from kreo_kontrol.tools.modifier_capture import (
    CaptureTarget,
    CapturedEvent,
    normalize_captured_event,
    next_target_prompt,
)


def test_normalize_captured_event_supports_flags_changed_for_modifiers() -> None:
    event = normalize_captured_event(
        event_type="flagsChanged",
        keycode=62,
        flags=0x2000,
        characters=None,
        characters_ignoring_modifiers=None,
        timestamp=12.5,
    )

    assert event.event_type == "flagsChanged"
    assert event.keycode == 62
    assert event.flags == 0x2000


def test_next_target_prompt_uses_requested_target_label() -> None:
    prompt = next_target_prompt(CaptureTarget("right_ctrl", "Press Right Control"))

    assert prompt == "Press Right Control"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
uv run --group dev pytest tests/tools/test_modifier_capture.py -q
```

Expected: FAIL because `CapturedEvent`, `normalize_captured_event`, and `next_target_prompt` are not defined yet.

- [ ] **Step 3: Write the minimal implementation**

```python
@dataclass(frozen=True)
class CapturedEvent:
    event_type: str
    keycode: int
    flags: int
    characters: str | None
    characters_ignoring_modifiers: str | None
    timestamp: float


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


def next_target_prompt(target: CaptureTarget) -> str:
    return target.prompt
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
uv run --group dev pytest tests/tools/test_modifier_capture.py -q
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/tools/test_modifier_capture.py src/kreo_kontrol/tools/modifier_capture.py
git commit -m "feat: add modifier event normalization"
```

### Task 3: Wire The Controller Snapshot And CLI

**Files:**
- Modify: `pyproject.toml`
- Modify: `.gitignore`
- Modify: `src/kreo_kontrol/tools/modifier_capture.py`
- Modify: `tests/tools/test_modifier_capture.py`
- Modify: `README.md`

- [ ] **Step 1: Write the failing tests**

```python
from kreo_kontrol.tools.modifier_capture import build_assignment_snapshot


class StubController:
    def read_keymap(self) -> dict[str, object]:
        return {
            "activeProfile": 1,
            "assignments": [
                {
                    "uiKey": "right_ctrl",
                    "baseAction": {"label": "Control Right", "rawValue": 0x00100000},
                    "fnAction": {"label": "Mission Control", "rawValue": 0x020000CD},
                }
            ],
            "verificationStatus": "verified",
        }


def test_build_assignment_snapshot_reads_matching_target_assignment() -> None:
    snapshot = build_assignment_snapshot(StubController(), "right_ctrl")

    assert snapshot["ui_key"] == "right_ctrl"
    assert snapshot["base_assignment_label"] == "Control Right"
    assert snapshot["base_assignment_raw_value"] == 0x00100000
    assert snapshot["fn_assignment_label"] == "Mission Control"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
uv run --group dev pytest tests/tools/test_modifier_capture.py -q
```

Expected: FAIL because `build_assignment_snapshot` does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

```python
def build_assignment_snapshot(controller: object, ui_key: str) -> dict[str, object | None]:
    payload = controller.read_keymap()
    for assignment in payload["assignments"]:
        if assignment["uiKey"] == ui_key:
            base_action = assignment["baseAction"]
            fn_action = assignment["fnAction"]
            return {
                "ui_key": ui_key,
                "base_assignment_label": base_action["label"],
                "base_assignment_raw_value": base_action["rawValue"],
                "fn_assignment_label": fn_action["label"] if fn_action else None,
                "fn_assignment_raw_value": fn_action["rawValue"] if fn_action else None,
            }
    raise KeyError(ui_key)
```

- [ ] **Step 4: Extend the module into a runnable CLI**

```python
def main() -> int:
    print("Modifier capture is ready.")
    return 0
```

Update `pyproject.toml`:

```toml
[project]
dependencies = [
  "fastapi>=0.115",
  "hidapi>=0.14",
  "pydantic>=2.11",
  "pyside6>=6.9",
  "pyobjc-framework-Quartz>=11.1",
  "uvicorn>=0.34",
]

[project.scripts]
kreo-kontrol = "kreo_kontrol.main:main"
kreo-kontrol-capture-modifiers = "kreo_kontrol.tools.modifier_capture:main"
```

Update `.gitignore`:

```gitignore
captures/*.json
```

Update `README.md` with a short usage section:

```markdown
## Modifier Capture

Run:

```sh
uv run kreo-kontrol-capture-modifiers
```

The script writes a JSON results file under `captures/`.
```

- [ ] **Step 5: Run the tests to verify they pass**

Run:

```bash
uv run --group dev pytest tests/tools/test_modifier_capture.py -q
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore README.md tests/tools/test_modifier_capture.py src/kreo_kontrol/tools/modifier_capture.py
git commit -m "feat: add modifier capture CLI"
```

### Task 4: Build The Real Quartz Capture Loop

**Files:**
- Modify: `src/kreo_kontrol/tools/modifier_capture.py`
- Modify: `tests/tools/test_modifier_capture.py`

- [ ] **Step 1: Write the failing tests**

```python
from kreo_kontrol.tools.modifier_capture import should_accept_event_for_target


def test_should_accept_event_for_target_accepts_flags_changed_for_modifier_targets() -> None:
    assert should_accept_event_for_target("right_ctrl", event_type="flagsChanged") is True


def test_should_accept_event_for_target_rejects_key_down_for_optional_fn_when_unavailable() -> None:
    assert should_accept_event_for_target("fn", event_type="keyDown") is False
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
uv run --group dev pytest tests/tools/test_modifier_capture.py -q
```

Expected: FAIL because `should_accept_event_for_target` is not implemented yet.

- [ ] **Step 3: Write the minimal implementation**

```python
def should_accept_event_for_target(target_ui_key: str, *, event_type: str) -> bool:
    if target_ui_key == "fn":
        return event_type == "flagsChanged"
    return event_type == "flagsChanged"
```

- [ ] **Step 4: Implement the Quartz-backed adapter**

```python
def capture_target_event(target: CaptureTarget, timeout_seconds: float) -> CapturedEvent | None:
    """Open a temporary event tap, wait for a matching modifier event, then return it."""
```

The implementation must:

- listen for `flagsChanged` and `keyDown`
- normalize the event through `normalize_captured_event`
- time out cleanly
- return `None` for optional `fn` if no observable event arrives

- [ ] **Step 5: Run the tests to verify they pass**

Run:

```bash
uv run --group dev pytest tests/tools/test_modifier_capture.py -q
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tests/tools/test_modifier_capture.py src/kreo_kontrol/tools/modifier_capture.py
git commit -m "feat: add quartz-backed modifier capture"
```

### Task 5: Full Verification

**Files:**
- Verify only

- [ ] **Step 1: Run targeted backend tests**

Run:

```bash
uv run --group dev pytest tests/tools/test_modifier_capture.py -q
```

Expected: PASS

- [ ] **Step 2: Run project verification**

Run:

```bash
uv run --group dev pytest -q
uv run --group dev ruff check .
uv run --group dev ty check
```

Expected: PASS

- [ ] **Step 3: Smoke-test the CLI**

Run:

```bash
uv run kreo-kontrol-capture-modifiers --help
```

Expected: exit `0` and usage output showing the capture command is installed.
