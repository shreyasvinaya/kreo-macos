# Kreo Layout Shell And Navigation Cleanup

**Goal:** Replace the row-based Lighting keyboard renderer with a true physical-position map, give the selected-key editor enough space, and move device details and recent events into their own dedicated pages.

## File Structure

- Modify: `frontend/src/lib/navigation.ts`
  - add `Device` and `Events` sections
- Modify: `frontend/src/lib/navigation.test.ts`
  - lock the new navigation order
- Modify: `frontend/src/lib/workspace.ts`
  - define page titles and inspector labels for `Device` and `Events`
- Modify: `frontend/src/lib/screen-chrome.ts`
  - only keep compact top-bar chips appropriate for each page
- Modify: `frontend/src/lib/lighting-layout.ts`
  - replace row/gap metadata with explicit `x/y/width/height` physical positions
  - preserve deterministic preset ordering based on position
- Modify: `frontend/src/lib/lighting-layout.test.ts`
  - verify the physical map order and a few critical anchor positions
- Modify: `frontend/src/App.tsx`
  - render the board from explicit positioned items
  - make Lighting a wide keyboard canvas plus a wider right-side editor column
  - remove device card from all pages except `Device`
  - move trace panel to `Events`
- Modify: `frontend/src/styles.css`
  - add absolute-position board styling
  - widen the Lighting editor column
  - support dedicated `Device` and `Events` pages

## Task 1: Lock The New Shell Behavior

- [ ] Add failing frontend tests for:
  - navigation order including `Device` and `Events`
  - screen chrome rules keeping Lighting top bar compact
- [ ] Run:
  - `cd frontend && bun test src/lib/navigation.test.ts src/lib/screen-chrome.test.ts`
- [ ] Update the navigation and chrome helpers until the tests pass.

## Task 2: Replace The Board Renderer With Physical Positions

- [ ] Update `frontend/src/lib/lighting-layout.test.ts` with failing assertions for:
  - deterministic visual ordering from `x/y` positions
  - anchor geometry for `print_screen`, `volume_knob`, `up`, `down`, `right`, and `end`
- [ ] Run:
  - `cd frontend && bun test src/lib/lighting-layout.test.ts`
- [ ] Replace the row-based model in `frontend/src/lib/lighting-layout.ts` with explicit physical positions.
- [ ] Keep preset generation based on sorted rendered order so staged fills still behave deterministically.
- [ ] Re-run:
  - `cd frontend && bun test src/lib/lighting-layout.test.ts`

## Task 3: Rebuild The Frontend Shell

- [ ] Update `frontend/src/App.tsx` so:
  - `DeviceCard` only appears on the new `Device` page
  - `TracePanel` only appears on the new `Events` page
  - Lighting shows a wide keyboard canvas and a wider right editor column with separate `Selected Key` and `Board Actions` panels
  - the board is rendered from explicit item positions rather than row loops
- [ ] Update `frontend/src/styles.css` to support:
  - positioned board rendering
  - wider Lighting inspector column
  - page-specific layouts for `Device` and `Events`

## Task 4: Verify The Full App

- [ ] Run:
  - `cd frontend && bun test`
  - `cd frontend && bun run typecheck`
  - `cd frontend && bun run build`
  - `uv run --group dev pytest -q`
  - `uv run --group dev ruff check .`
  - `uv run --group dev ty check`
- [ ] Relaunch:
  - `uv run kreo-kontrol`
