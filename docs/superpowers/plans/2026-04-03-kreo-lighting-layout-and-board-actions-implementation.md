# Kreo Lighting Layout And Board Actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Lighting screen match the physical Kreo Swarm layout, add staged whole-board color actions, and auto-refresh live colors while the screen is clean.

**Architecture:** Keep the existing per-key backend contract unchanged and move this slice into the frontend. Add a small lighting utility module for board layout metadata and preset generation, then rebuild the Lighting canvas and inspector around that data while preserving staged diff apply/reset behavior.

**Tech Stack:** React 19, TypeScript, Bun test runner, Vite, FastAPI loopback API.

---

## File Structure

- Create: `frontend/src/lib/lighting-layout.ts`
  - physical board layout metadata
  - mapped/unmapped key grouping
  - preset generation helpers
- Create: `frontend/src/lib/lighting-layout.test.ts`
  - tests for preset generation and mapped-key ordering
- Modify: `frontend/src/App.tsx`
  - physical board rendering
  - board action controls
  - clean-state auto-refresh
- Modify: `frontend/src/styles.css`
  - board silhouette styling
  - knob module
  - dimmed unmapped keys
  - board action controls
- Optionally modify: `frontend/src/lib/lighting.ts`
  - only if minor helper reuse is needed

## Task 1: Layout And Preset Utilities

**Files:**
- Create: `frontend/src/lib/lighting-layout.ts`
- Create: `frontend/src/lib/lighting-layout.test.ts`

- [ ] **Step 1: Write the failing preset/layout tests**

```ts
import { expect, test } from "bun:test";

import {
  applySolidFill,
  applyTwoColorSplit,
  buildEditableVisualOrder,
  physicalKeyboardLayout,
} from "./lighting-layout";

const keys = [
  { uiKey: "esc", label: "Esc", lightPos: 8, color: "#111111" },
  { uiKey: "f6", label: "F6", lightPos: 50, color: "#222222" },
  { uiKey: "right", label: "Right", lightPos: 103, color: "#333333" },
];

test("buildEditableVisualOrder follows the rendered board order", () => {
  expect(buildEditableVisualOrder(physicalKeyboardLayout, keys)).toEqual(["esc", "f6", "right"]);
});

test("solid fill stages every mapped key", () => {
  expect(applySolidFill(keys, "#00ffaa")).toEqual({
    esc: "#00ffaa",
    f6: "#00ffaa",
    right: "#00ffaa",
  });
});

test("two-color split assigns left and right board groups deterministically", () => {
  expect(applyTwoColorSplit(keys, "#ff0000", "#0000ff")).toEqual({
    esc: "#ff0000",
    f6: "#0000ff",
    right: "#0000ff",
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && bun test src/lib/lighting-layout.test.ts`
Expected: FAIL because the layout/preset module does not exist yet.

- [ ] **Step 3: Write the minimal layout and preset implementation**

```ts
export interface PhysicalKey {
  id: string;
  label: string;
  section: "main" | "nav" | "arrows" | "knob";
  width?: "standard" | "wide" | "space" | "knob";
  editable: boolean;
}

export const physicalKeyboardLayout: PhysicalKey[][] = [
  // exact board rows with main block, nav column, arrows, knob placeholder
];

export function buildEditableVisualOrder(
  layout: PhysicalKey[][],
  keys: { uiKey: string }[],
): string[] {
  const available = new Set(keys.map((key) => key.uiKey));
  return layout.flat().filter((key) => key.editable && available.has(key.id)).map((key) => key.id);
}

export function applySolidFill(
  keys: { uiKey: string }[],
  color: string,
): Record<string, string> {
  return Object.fromEntries(keys.map((key) => [key.uiKey, color]));
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && bun test src/lib/lighting-layout.test.ts`
Expected: PASS

## Task 2: Physical Lighting Screen

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Write the failing UI-state test**

```ts
import { expect, test } from "bun:test";

import { buildRenderedLightingState } from "./lighting";
import { applySolidFill } from "./lighting-layout";

test("whole-board actions produce staged colors visible in rendered state", () => {
  const keys = [
    { uiKey: "esc", label: "Esc", lightPos: 8, color: "#111111" },
    { uiKey: "f6", label: "F6", lightPos: 50, color: "#222222" },
  ];
  const staged = applySolidFill(keys, "#00ffaa");
  const rendered = buildRenderedLightingState(keys, staged);

  expect(rendered.map((key) => key.color)).toEqual(["#00ffaa", "#00ffaa"]);
});
```

- [ ] **Step 2: Run test to verify it fails if helpers are not wired**

Run: `cd frontend && bun test`
Expected: FAIL until the screen uses the new layout helpers correctly.

- [ ] **Step 3: Rebuild the Lighting screen around the physical layout**

```tsx
const isLightingScreen = activeScreen === "Lighting";
const visualOrder = buildEditableVisualOrder(physicalKeyboardLayout, renderedLightingKeys);
```

```tsx
<div className="board-shell">
  <div className="board-main">
    {physicalKeyboardLayout.map((row) => (
      <div className="board-row">{row.map(renderPhysicalKey)}</div>
    ))}
  </div>
</div>
```

Requirements:
- mirror the physical board silhouette
- render a non-editable knob module
- show unmapped keys dimmed but visible
- keep mapped keys selectable
- keep selected-key color picker in the inspector
- add `Board actions` with solid fill, two-color split, three-color split, checker, and rainbow
- presets only mutate staged state

- [ ] **Step 4: Add clean-state auto-refresh**

```tsx
useEffect(() => {
  if (activeScreen !== "Lighting" || Object.keys(stagedLightingEdits).length > 0) {
    return;
  }

  const intervalId = window.setInterval(() => {
    void hydrateLighting();
  }, 3000);

  return () => window.clearInterval(intervalId);
}, [activeScreen, stagedLightingEdits, hydrateLighting]);
```

Behavior:
- refresh only while clean
- pause while dirty
- refresh immediately after apply/reset
- preserve selected key if still present

- [ ] **Step 5: Run frontend verification**

Run:
- `cd frontend && bun test`
- `cd frontend && bun run typecheck`
- `cd frontend && bun run build`

Expected: PASS

## Task 3: End-To-End Verification

**Files:**
- Modify if needed: `frontend/src/App.tsx`
- Modify if needed: `frontend/src/styles.css`

- [ ] **Step 1: Run full project verification**

Run:
- `uv run --group dev pytest -q`
- `uv run --group dev ruff check .`
- `uv run --group dev ty check`

Expected: PASS

- [ ] **Step 2: Launch the app and verify on hardware**

Run:

```bash
uv run kreo-kontrol
```

Expected:
- Lighting canvas matches the physical keyboard more closely
- unmapped keys are dimmed but visible
- knob block is visible and non-clickable
- whole-board actions recolor the board in staged state immediately
- idle clean state refreshes from hardware
- dirty state does not get overwritten

