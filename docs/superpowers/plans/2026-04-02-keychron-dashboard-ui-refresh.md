# Keychron-Style Dashboard UI Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current concept-heavy editor stage with a familiar Keychron Launcher style dashboard: left sidebar, dashboard-first landing screen, realistic keyboard visual, and a clean inspector panel.

**Architecture:** Keep the existing data model and loopback API, but reshape the frontend into a three-column application shell. The sidebar owns navigation state, the center pane owns the realistic keyboard canvas and top summary, and the right pane owns the selected-key inspector and quieter activity details.

**Tech Stack:** React 19, TypeScript, Vite, Bun test, existing local API model

---

### Task 1: Lock The Navigation Model

**Files:**
- Create: `frontend/src/lib/navigation.ts`
- Create: `frontend/src/lib/navigation.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, expect, test } from "bun:test";

import { defaultScreen, primaryNavigation } from "./navigation";

describe("navigation model", () => {
  test("defaults to the dashboard screen", () => {
    expect(defaultScreen).toBe("Dashboard");
  });

  test("matches the familiar launcher section order", () => {
    expect(primaryNavigation).toEqual([
      "Dashboard",
      "Keymap",
      "Lighting",
      "Macros",
      "Profiles",
      "Settings",
    ]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && bun test src/lib/navigation.test.ts`
Expected: FAIL because `./navigation` does not exist

- [ ] **Step 3: Add the navigation model**

```ts
export const primaryNavigation = [
  "Dashboard",
  "Keymap",
  "Lighting",
  "Macros",
  "Profiles",
  "Settings",
] as const;

export type PrimaryScreen = (typeof primaryNavigation)[number];

export const defaultScreen: PrimaryScreen = "Dashboard";
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && bun test src/lib/navigation.test.ts`
Expected: PASS

### Task 2: Replace The Dashboard Layout

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/device-card.tsx`
- Modify: `frontend/src/components/trace-panel.tsx`

- [ ] **Step 1: Rebuild the app shell**

Implement:
- left sidebar with the navigation model from Task 1
- dashboard header with device status and summary actions
- central realistic keyboard workspace
- right inspector for selected key plus activity details

- [ ] **Step 2: Keep the keyboard visual realistic and familiar**

Implement:
- restrained legends and labels
- selected key emphasis on the right-side Option key
- no oversized hero marketing section
- no speculative editing chips inside the main keyboard panel

- [ ] **Step 3: Keep data flow simple**

Implement:
- preserve `loadDashboardModel`
- preserve dashboard-first launch
- keep the inspector data derived from local constants plus the fetched device state

### Task 3: Restyle To Match The New Structure

**Files:**
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Replace the current concept styling**

Implement:
- muted, familiar Keychron-like application chrome
- left sidebar layout
- cleaner panels with lower visual noise
- realistic keyboard casing and key styling

- [ ] **Step 2: Verify the frontend**

Run:
- `cd frontend && bun test`
- `cd frontend && bun run typecheck`
- `cd frontend && bun run build`

Expected:
- all tests PASS
- TypeScript PASS
- Vite build PASS

## Self-Review

### Spec Coverage

- dashboard-first landing screen: Task 2
- left sidebar navigation: Task 1 and Task 2
- realistic keyboard visual with editable focus: Task 2 and Task 3
- familiar Keychron-style layout: Task 2 and Task 3

### Placeholder Scan

- No `TODO` or `TBD` markers remain.
- The tasks call out the exact files and verification commands.

### Type Consistency

- `PrimaryScreen` is derived from `primaryNavigation`.
- `defaultScreen` is `Dashboard`.
- `loadDashboardModel` remains the source of fetched dashboard data.
