# Kreo Per-Key Lighting Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the `Lighting` screen into a real device-backed per-key RGB editor with staged single-key edits and explicit apply/reset behavior.

**Architecture:** Extend the FastAPI backend with per-key lighting read/apply endpoints that own `ui_key` to `light_pos` mapping and custom-frame assembly. Replace the current fake Lighting shell with a keyboard-driven editor that renders live colors immediately, stages local edits, and applies only staged diffs through the new API.

**Tech Stack:** FastAPI, Pydantic, Python HID controller, React 19, TypeScript, Bun test runner, pytest, Ruff, ty.

---

## File Structure

- Modify: `src/kreo_kontrol/device/bytech_lighting.py`
  - expose per-key lighting state from live hardware
  - resolve `ui_key` to `light_pos`
  - apply staged per-key diffs through the existing custom-light frame path
- Modify: `src/kreo_kontrol/api/models.py`
  - add typed request/response models for per-key lighting
- Modify: `src/kreo_kontrol/api/app.py`
  - add `GET /api/lighting/per-key`
  - add `POST /api/lighting/per-key/apply`
- Modify: `tests/device/test_bytech_lighting.py`
  - cover backend per-key mapping and diff-apply behavior
- Create: `tests/api/test_per_key_lighting_endpoint.py`
  - cover per-key API contracts
- Modify: `frontend/src/lib/api.ts`
  - add per-key lighting fetch/apply client helpers and types
- Modify: `frontend/src/App.tsx`
  - make the `Lighting` screen a real staged per-key editor
- Modify: `frontend/src/styles.css`
  - add keycap color rendering, selected-state, inspector controls, and lighting-screen actions
- Create: `frontend/src/lib/lighting.test.ts`
  - cover staged overlay logic and payload construction

## Task 1: Backend Per-Key API

**Files:**
- Modify: `src/kreo_kontrol/device/bytech_lighting.py`
- Modify: `src/kreo_kontrol/api/models.py`
- Modify: `src/kreo_kontrol/api/app.py`
- Modify: `tests/device/test_bytech_lighting.py`
- Create: `tests/api/test_per_key_lighting_endpoint.py`

- [ ] **Step 1: Write the failing API tests**

```python
from fastapi.testclient import TestClient

from kreo_kontrol.api.app import create_app
from kreo_kontrol.device.domains.lighting import (
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

    def apply_per_key_colors_by_ui_key(self, staged: dict[str, str]) -> dict[str, object]:
        assert staged == {"esc": "#00ff00"}
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
    client = TestClient(create_app(lighting_controller=FakePerKeyLightingController()))

    response = client.get("/api/lighting/per-key")

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "custom"
    assert payload["keys"][0]["ui_key"] == "esc"
    assert payload["keys"][0]["color"] == "#ff0000"


def test_per_key_lighting_apply_returns_updated_colors() -> None:
    client = TestClient(create_app(lighting_controller=FakePerKeyLightingController()))

    response = client.post(
        "/api/lighting/per-key/apply",
        json={"edits": {"esc": "#00ff00"}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["keys"][0]["color"] == "#00ff00"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/api/test_per_key_lighting_endpoint.py -v`
Expected: FAIL because the per-key models/endpoints do not exist yet.

- [ ] **Step 3: Write the failing controller test for `ui_key` mapping and diff apply**

```python
def test_apply_per_key_colors_by_ui_key_maps_keys_and_updates_frame() -> None:
    profile = build_profile(mode=1, brightness_level=2)
    light_table = bytes([0] * 480)
    device = FakeHidDevice(
        responses=[
            wrap_response(b"\x84\x00\x00\x01\x00\x80", profile),
            wrap_response(b"\x83\x00\x00\x01\x00\xf8\x01", bytes([0, 0, 0, 41])),
            wrap_light_table_response(b"\x8a\x00\x00\x01\x00\xe3\x01", light_table),
            wrap_response(b"\x86\x00\x00\x01\x00\x7a\x01", b"\x00"),
        ]
    )
    controller = BytechLightingController(
        device_path=b"test-device",
        device_factory=lambda: device,
    )

    state = controller.apply_per_key_colors_by_ui_key({"esc": "#00ff00"})

    assert state["keys"][0]["ui_key"] == "esc"
    assert state["keys"][0]["color"] == "#00ff00"
```

- [ ] **Step 4: Run test to verify it fails**

Run: `uv run --group dev pytest tests/device/test_bytech_lighting.py::test_apply_per_key_colors_by_ui_key_maps_keys_and_updates_frame -v`
Expected: FAIL because the keyed per-key API does not exist yet.

- [ ] **Step 5: Implement minimal backend models, controller helpers, and endpoints**

```python
class PerKeyLightingEntry(BaseModel):
    ui_key: str
    label: str
    light_pos: int
    color: str


class PerKeyLightingResponse(BaseModel):
    mode: str
    brightness: int
    per_key_rgb_supported: bool
    verification_status: str
    keys: list[PerKeyLightingEntry]


class PerKeyLightingApplyPayload(BaseModel):
    edits: dict[str, str]
```

```python
@app.get("/api/lighting/per-key", response_model=PerKeyLightingResponse)
def lighting_per_key() -> PerKeyLightingResponse:
    payload = controller.read_per_key_state()
    return PerKeyLightingResponse(**payload)


@app.post("/api/lighting/per-key/apply", response_model=PerKeyLightingResponse)
def apply_per_key_lighting(payload: PerKeyLightingApplyPayload) -> PerKeyLightingResponse:
    result = controller.apply_per_key_colors_by_ui_key(payload.edits)
    return PerKeyLightingResponse(**result)
```

- [ ] **Step 6: Run backend tests to verify they pass**

Run: `uv run --group dev pytest tests/device/test_bytech_lighting.py tests/api/test_per_key_lighting_endpoint.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/kreo_kontrol/device/bytech_lighting.py src/kreo_kontrol/api/models.py src/kreo_kontrol/api/app.py tests/device/test_bytech_lighting.py tests/api/test_per_key_lighting_endpoint.py
git commit -m "feat: add per-key lighting API"
```

## Task 2: Frontend Lighting Screen State

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/lighting.test.ts`

- [ ] **Step 1: Write the failing frontend state tests**

```ts
import { expect, test } from "bun:test";

import { buildRenderedLightingState, buildPerKeyApplyPayload } from "./lighting";

test("staged edits override device colors in rendered state", () => {
  const rendered = buildRenderedLightingState(
    [
      { uiKey: "esc", color: "#ff0000" },
      { uiKey: "space", color: "#ffffff" },
    ],
    { esc: "#00ff00" },
  );

  expect(rendered.find((entry) => entry.uiKey === "esc")?.color).toBe("#00ff00");
  expect(rendered.find((entry) => entry.uiKey === "space")?.color).toBe("#ffffff");
});

test("apply payload only includes staged edits", () => {
  expect(buildPerKeyApplyPayload({ esc: "#00ff00" })).toEqual({
    edits: { esc: "#00ff00" },
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && bun test src/lib/lighting.test.ts`
Expected: FAIL because the lighting helpers do not exist yet.

- [ ] **Step 3: Implement minimal lighting client/types/helpers**

```ts
export interface PerKeyLightingEntry {
  uiKey: string;
  label: string;
  lightPos: number;
  color: string;
}

export interface PerKeyLightingModel {
  mode: string;
  brightness: number;
  perKeyRgbSupported: boolean;
  verificationStatus: string;
  keys: PerKeyLightingEntry[];
}

export function buildRenderedLightingState(
  deviceKeys: PerKeyLightingEntry[],
  staged: Record<string, string>,
): PerKeyLightingEntry[] {
  return deviceKeys.map((entry) => ({
    ...entry,
    color: staged[entry.uiKey] ?? entry.color,
  }));
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && bun test src/lib/lighting.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/lib/lighting.test.ts
git commit -m "feat: add per-key lighting frontend state"
```

## Task 3: Real Lighting Screen UI

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Write the failing interaction test**

```ts
import { expect, test } from "bun:test";

import { buildRenderedLightingState } from "./lib/api";

test("selected key renders staged color in the keyboard visual", () => {
  const rendered = buildRenderedLightingState(
    [{ uiKey: "esc", label: "Esc", lightPos: 8, color: "#ff0000" }],
    { esc: "#00ff00" },
  );

  expect(rendered[0].color).toBe("#00ff00");
});
```

- [ ] **Step 2: Run test to verify it fails if needed**

Run: `cd frontend && bun test`
Expected: FAIL only if the render/state helpers are not wired correctly yet.

- [ ] **Step 3: Replace the fake Lighting screen with a real staged editor**

```tsx
const isLightingScreen = activeScreen === "Lighting";
const lightingKeys = isLightingScreen ? renderedLighting.keys : [];

<div className="keyboard-grid">
  {keyboardRows.map((row, index) => (
    <div className="key-row" key={`row-${index}`}>
      {row.map((key, keyIndex) =>
        renderKeycap({
          keyDef: key,
          visualKeyId: visualKeyOrder[index][keyIndex],
          lightingEntry: lightingKeyMap.get(visualKeyOrder[index][keyIndex]),
          selectedKeyId,
          onSelect: setSelectedKeyId,
        }),
      )}
    </div>
  ))}
</div>
```

```tsx
{activeScreen === "Lighting" ? (
  <LightingInspector
    selectedKey={selectedLightingKey}
    stagedCount={Object.keys(stagedLightingEdits).length}
    onColorChange={handleLightingColorChange}
    onApply={handleApplyLighting}
    onReset={handleResetLighting}
  />
) : (
  <DefaultInspector />
)}
```

- [ ] **Step 4: Run frontend verification**

Run:
- `cd frontend && bun test`
- `cd frontend && bun run typecheck`
- `cd frontend && bun run build`

Expected: PASS

- [ ] **Step 5: Run backend verification**

Run:
- `uv run --group dev pytest`
- `uv run --group dev ruff check .`
- `uv run --group dev ty check`

Expected: PASS

- [ ] **Step 6: Hardware sanity check**

Run:

```bash
uv run kreo-kontrol
```

Expected:
- opening `Lighting` shows current per-key colors immediately
- selecting a key reveals the color picker in the right inspector
- staged edits recolor keycaps before apply
- apply changes the physical keyboard

- [ ] **Step 7: Commit**

```bash
git add frontend/src/App.tsx frontend/src/styles.css frontend/src/lib/api.ts
git commit -m "feat: add per-key lighting editor"
```
