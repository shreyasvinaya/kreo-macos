# Kreo Website Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the synthetic keyboard editor with the real `swarm75` asset surface, then build website-parity lighting, remap, saved-profile, and macro workflows on top of that shared surface.

**Architecture:** Vendor the website keyboard assets into the app, expose normalized keyboard metadata from the backend, and make the frontend treat the SVG surface as the source of truth for both lighting and keymap. Keep device-backed features honest, and implement profiles as app-side snapshots because this keyboard family does not expose real hardware profile slots.

**Tech Stack:** FastAPI, Pydantic, PySide6, React 19, Vite, Bun, pytest, Ruff, ty

---

## File Map

- Create: `src/kreo_kontrol/api/keyboard_assets.py`
- Modify: `src/kreo_kontrol/api/app.py`
- Modify: `src/kreo_kontrol/api/models.py`
- Create: `tests/api/test_keyboard_assets.py`
- Create: `frontend/public/keyboard/swarm75/base/default.webp`
- Create: `frontend/public/keyboard/swarm75/letters/default.webp`
- Create: `frontend/public/keyboard/swarm75/overlay/interactive.svg`
- Create: `frontend/public/keyboard/swarm75/meta/manifest.json`
- Create: `frontend/public/keyboard/swarm75/meta/led-map.json`
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/keyboard-assets.ts`
- Create: `frontend/src/lib/keyboard-assets.test.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`
- Later modify: `src/kreo_kontrol/device/domains/keymap.py`
- Later modify: `src/kreo_kontrol/api/models.py`
- Later modify: `src/kreo_kontrol/api/app.py`
- Later create: `tests/api/test_keymap_endpoint.py`
- Later create: `frontend/src/lib/keymap.ts`
- Later create: `frontend/src/lib/keymap.test.ts`

### Task 1: Vendored Keyboard Asset Metadata Endpoint

**Files:**
- Create: `src/kreo_kontrol/api/keyboard_assets.py`
- Modify: `src/kreo_kontrol/api/models.py`
- Modify: `src/kreo_kontrol/api/app.py`
- Test: `tests/api/test_keyboard_assets.py`

- [ ] **Step 1: Write the failing backend asset metadata tests**

```python
from fastapi.testclient import TestClient

from kreo_kontrol.api.app import create_app


def test_keyboard_asset_endpoint_returns_swarm75_metadata() -> None:
    client = TestClient(create_app())

    response = client.get("/api/keyboard-assets/swarm75")

    assert response.status_code == 200
    payload = response.json()
    assert payload["asset_name"] == "swarm75"
    assert payload["base_image_url"].endswith("/keyboard/swarm75/base/default.webp")
    assert payload["letters_image_url"].endswith("/keyboard/swarm75/letters/default.webp")
    assert payload["interactive_svg_url"].endswith("/keyboard/swarm75/overlay/interactive.svg")
    assert len(payload["keys"]) >= 80
    assert payload["keys"][0]["svg_id"].startswith("key_")


def test_keyboard_asset_endpoint_returns_404_for_unknown_asset() -> None:
    client = TestClient(create_app())

    response = client.get("/api/keyboard-assets/unknown")

    assert response.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/api/test_keyboard_assets.py -v`
Expected: FAIL because `/api/keyboard-assets/swarm75` does not exist yet.

- [ ] **Step 3: Write minimal backend asset loader and response models**

```python
class KeyboardAssetKey(BaseModel):
    logical_id: str
    svg_id: str
    ui_key: str
    label: str
    protocol_pos: int
    led_index: int


class KeyboardAssetResponse(BaseModel):
    asset_name: str
    base_image_url: str
    letters_image_url: str
    interactive_svg_url: str
    keys: list[KeyboardAssetKey]
```

```python
def load_keyboard_asset(asset_name: str) -> KeyboardAssetResponse:
    ...
```

```python
@app.get("/api/keyboard-assets/{asset_name}", response_model=KeyboardAssetResponse)
def keyboard_assets(asset_name: str) -> KeyboardAssetResponse:
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/api/test_keyboard_assets.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/api/test_keyboard_assets.py src/kreo_kontrol/api/models.py src/kreo_kontrol/api/keyboard_assets.py src/kreo_kontrol/api/app.py
git commit -m "feat: expose vendored keyboard asset metadata"
```

### Task 2: Vendor The Swarm75 Assets Into The App

**Files:**
- Create: `frontend/public/keyboard/swarm75/base/default.webp`
- Create: `frontend/public/keyboard/swarm75/letters/default.webp`
- Create: `frontend/public/keyboard/swarm75/overlay/interactive.svg`
- Create: `frontend/public/keyboard/swarm75/meta/manifest.json`
- Create: `frontend/public/keyboard/swarm75/meta/led-map.json`

- [ ] **Step 1: Copy the approved runtime assets from the dump**

```bash
mkdir -p frontend/public/keyboard/swarm75/base frontend/public/keyboard/swarm75/letters frontend/public/keyboard/swarm75/overlay frontend/public/keyboard/swarm75/meta
cp kreo_website_dump/kontrol.kreo-tech.com/assets/keyboard/swarm75/base/default.webp frontend/public/keyboard/swarm75/base/default.webp
cp kreo_website_dump/kontrol.kreo-tech.com/assets/keyboard/swarm75/letters/default.webp frontend/public/keyboard/swarm75/letters/default.webp
cp kreo_website_dump/kontrol.kreo-tech.com/assets/keyboard/swarm75/overlay/interactive.svg frontend/public/keyboard/swarm75/overlay/interactive.svg
cp kreo_website_dump/kontrol.kreo-tech.com/assets/keyboard/swarm75/meta/manifest.json frontend/public/keyboard/swarm75/meta/manifest.json
cp kreo_website_dump/kontrol.kreo-tech.com/assets/keyboard/swarm75/meta/led-map.json frontend/public/keyboard/swarm75/meta/led-map.json
```

- [ ] **Step 2: Verify the files exist in the app-owned asset tree**

Run: `find frontend/public/keyboard/swarm75 -maxdepth 3 -type f | sort`
Expected:
- `frontend/public/keyboard/swarm75/base/default.webp`
- `frontend/public/keyboard/swarm75/letters/default.webp`
- `frontend/public/keyboard/swarm75/overlay/interactive.svg`
- `frontend/public/keyboard/swarm75/meta/manifest.json`
- `frontend/public/keyboard/swarm75/meta/led-map.json`

- [ ] **Step 3: Commit**

```bash
git add frontend/public/keyboard/swarm75
git commit -m "feat: vendor swarm75 keyboard assets"
```

### Task 3: Frontend Asset Loader And Metadata Normalization

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/keyboard-assets.ts`
- Create: `frontend/src/lib/keyboard-assets.test.ts`

- [ ] **Step 1: Write the failing frontend normalization tests**

```ts
import { expect, test } from "bun:test";

import { normalizeKeyboardAsset } from "./keyboard-assets";

test("normalizeKeyboardAsset maps backend keys by svg id and ui key", () => {
  const asset = normalizeKeyboardAsset({
    asset_name: "swarm75",
    base_image_url: "/keyboard/swarm75/base/default.webp",
    letters_image_url: "/keyboard/swarm75/letters/default.webp",
    interactive_svg_url: "/keyboard/swarm75/overlay/interactive.svg",
    keys: [
      {
        logical_id: "ESC",
        svg_id: "key_ESC",
        ui_key: "esc",
        label: "Esc",
        protocol_pos: 8,
        led_index: 0,
      },
    ],
  });

  expect(asset.keysBySvgId.get("key_ESC")?.uiKey).toBe("esc");
  expect(asset.keysByUiKey.get("esc")?.label).toBe("Esc");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && bun test src/lib/keyboard-assets.test.ts`
Expected: FAIL because `keyboard-assets.ts` does not exist yet.

- [ ] **Step 3: Write the minimal asset loader and API call**

```ts
export interface KeyboardAssetModel {
  assetName: string;
  baseImageUrl: string;
  lettersImageUrl: string;
  interactiveSvgUrl: string;
  keys: KeyboardAssetKey[];
  keysBySvgId: Map<string, KeyboardAssetKey>;
  keysByUiKey: Map<string, KeyboardAssetKey>;
}
```

```ts
export async function loadKeyboardAsset(assetName: string): Promise<KeyboardAssetModel> {
  ...
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && bun test src/lib/keyboard-assets.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/lib/keyboard-assets.ts frontend/src/lib/keyboard-assets.test.ts
git commit -m "feat: add frontend keyboard asset loader"
```

### Task 4: Replace The Lighting Board With The SVG/Image Surface

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`
- Test: `frontend/src/lib/api.test.ts`

- [ ] **Step 1: Write the failing frontend API test for keyboard asset loading**

```ts
import { afterEach, describe, expect, mock, test } from "bun:test";

import { loadKeyboardAsset } from "./api";

test("loadKeyboardAsset fetches the swarm75 asset payload", async () => {
  globalThis.fetch = mock(async () =>
    new Response(
      JSON.stringify({
        asset_name: "swarm75",
        base_image_url: "/keyboard/swarm75/base/default.webp",
        letters_image_url: "/keyboard/swarm75/letters/default.webp",
        interactive_svg_url: "/keyboard/swarm75/overlay/interactive.svg",
        keys: [],
      }),
      { status: 200 },
    ),
  ) as unknown as typeof fetch;

  const asset = await loadKeyboardAsset("swarm75");

  expect(asset.assetName).toBe("swarm75");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && bun test src/lib/api.test.ts`
Expected: FAIL because `loadKeyboardAsset` is not exported yet.

- [ ] **Step 3: Implement the layered keyboard surface**

```tsx
<div className="asset-keyboard">
  <img alt="" className="asset-layer asset-base" src={asset.baseImageUrl} />
  <div className="asset-rgb-layer" dangerouslySetInnerHTML={{ __html: interactiveSvgMarkup }} />
  <img alt="" className="asset-layer asset-letters" src={asset.lettersImageUrl} />
</div>
```

```ts
function colorizeInteractiveSvg(svgMarkup: string, renderedKeys: Map<string, string>): string {
  ...
}
```

- [ ] **Step 4: Run the focused frontend checks**

Run:
- `cd frontend && bun test src/lib/api.test.ts src/lib/keyboard-assets.test.ts`
- `cd frontend && bun run typecheck`
- `cd frontend && bun run build`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/styles.css frontend/src/lib/api.test.ts frontend/src/lib/api.ts frontend/src/lib/keyboard-assets.ts frontend/src/lib/keyboard-assets.test.ts
git commit -m "feat: move lighting to the vendored svg keyboard surface"
```

### Task 5: Continue With Lighting, Keymap, Profiles, And Macros

**Files:**
- Modify: `src/kreo_kontrol/api/app.py`
- Modify: `src/kreo_kontrol/api/models.py`
- Modify: `src/kreo_kontrol/device/domains/keymap.py`
- Modify: `src/kreo_kontrol/device/domains/macros.py`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Use the new shared asset model as the base for lighting parity**

Run:
- `uv run --group dev pytest tests/api -q`
- `cd frontend && bun test`

Expected: green baseline before extending lighting controls.

- [ ] **Step 2: Add real keymap read/write tests and backend implementation**

Run: `uv run --group dev pytest tests/api/test_keymap_endpoint.py -v`
Expected: FAIL first, then PASS after implementing real keymap endpoints.

- [ ] **Step 3: Add app-side saved profile tests and implementation**

Run: `uv run --group dev pytest tests/api -q`
Expected: new snapshot-profile tests fail first, then pass.

- [ ] **Step 4: Add macro endpoint tests and implementation**

Run: `uv run --group dev pytest tests/api -q`
Expected: macro tests fail first, then pass.

- [ ] **Step 5: Run the full verification sweep**

Run:
- `uv run --group dev pytest -q`
- `uv run --group dev ruff check .`
- `uv run --group dev ty check`
- `cd frontend && bun test`
- `cd frontend && bun run typecheck`
- `cd frontend && bun run build`

Expected: PASS
