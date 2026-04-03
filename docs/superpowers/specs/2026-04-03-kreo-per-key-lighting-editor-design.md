# Kreo Per-Key Lighting Editor Design

## Goal

Turn the `Lighting` screen into the first real device-backed editor in the app by exposing live per-key RGB state from the Kreo Swarm, rendering those colors directly on the keyboard visual, allowing staged single-key color edits, and applying the staged diff back to the keyboard through the existing Bytech custom-lighting path.

## Scope

This slice is intentionally narrow.

Included:
- real `Lighting` screen data load on entry
- live per-key color rendering on the keyboard visual
- single-key selection
- right-side color picker inspector for the selected key
- staged local edits across multiple individually selected keys
- explicit `Apply staged edits`
- explicit `Reset`
- backend per-key read/apply endpoints

Excluded:
- multi-key brush painting
- drag selection
- lighting effect editor beyond current global endpoint
- profile-aware per-key snapshots
- non-lighting screen refactors

## Existing Context

The backend already supports:
- global brightness writes
- global static color writes
- custom per-key RGB writes through the Bytech custom frame path
- key table reads from the keyboard using the same HID interface

The frontend currently has:
- a dashboard-style shell
- a realistic keyboard visual
- sidebar navigation
- a fake Lighting screen with shared shell content

The missing layer is the device-backed per-key editor flow between those two halves.

## Architecture

This feature should be built as one vertical slice with a narrow API boundary.

Backend responsibilities:
- read the keyboard key table and current custom-light frame
- normalize that into a UI-safe per-key model
- accept staged color diffs keyed by UI key identity or `light_pos`
- merge diffs into one custom frame and send a single Bytech custom-light write

Frontend responsibilities:
- load per-key lighting state automatically when the `Lighting` screen opens
- render all current key colors immediately on the keyboard visual
- track selected key
- stage color edits locally without writing on every picker change
- render staged colors immediately on the relevant keycaps
- send only staged diffs when `Apply` is pressed

The frontend must not assemble raw custom-light frames. That remains backend-only.

## Backend Contract

### `GET /api/lighting/per-key`

Returns:
- current mode
- current brightness
- `per_key_rgb_supported`
- `verification_status`
- per-key color entries for the current keyboard

Each per-key entry should include:
- `ui_key`
- `label`
- `light_pos`
- `color`

`ui_key` is the stable frontend identifier used by the keyboard component.
`light_pos` is retained for backend traceability and future debugging.

### `POST /api/lighting/per-key/apply`

Accepts:
- a list or map of staged edits only
- each edit contains:
  - `ui_key`
  - `color`

Backend flow:
1. resolve current keyboard key metadata
2. resolve current custom-light frame
3. map incoming `ui_key` values to `light_pos`
4. merge staged colors into one updated frame
5. send the custom-light write
6. return refreshed per-key state plus verification result

This endpoint is diff-based. The browser does not submit a full frame.

## UI Model

The `Lighting` screen has three state layers.

### Device state

The last successfully loaded per-key state from the keyboard.

### Staged state

Local edits not yet written to hardware.

### Rendered state

Device state overlaid with staged edits. This is what the keyboard visual shows.

This allows:
- full keyboard color rendering immediately on screen load
- immediate visual feedback when a selected key color changes
- safe local staging before apply

## UI Structure

### Keyboard canvas

The main keyboard visual remains the primary canvas.

Requirements:
- render all current per-key colors directly on keycaps
- preserve the existing realistic keyboard presentation
- selected key gets a clear outline or accent ring
- staged colors appear immediately on keycaps

### Right inspector

The inspector becomes selection-driven.

When no key is selected:
- show a prompt telling the user to select a key

When a key is selected:
- show selected key label
- show color swatch
- show hex field
- show native color picker
- show staged state for that key if present

Global actions in the inspector:
- `Apply staged edits`
- `Reset`
- staged edit count
- last verification result

### Status treatment

Keep the status treatment quiet.

Include:
- connection state
- last apply result
- verification status

Do not reintroduce a noisy trace-first layout for this editor.

## Interaction Flow

1. user opens `Lighting`
2. app automatically requests current per-key lighting state
3. keyboard visual renders all current colors immediately
4. user clicks a key
5. inspector reveals that key’s editable color controls
6. user changes the color
7. staged state updates locally
8. keyboard visual updates that key immediately using rendered state
9. user may repeat steps 4-8 for additional keys
10. user presses `Apply staged edits`
11. backend writes the merged diff to the keyboard
12. response refreshes device state and clears staged edits on success

`Reset` clears staged edits and restores rendered state from last loaded device state.

## Key Identity Strategy

The frontend needs stable key ids that match the keyboard visual.

For this slice:
- define a stable `ui_key` mapping for the visual keys already rendered in `frontend/src/App.tsx`
- backend returns `ui_key -> light_pos -> color`
- staged edits are stored by `ui_key`

This is sufficient for the first real lighting screen.

If some visible keys do not yet have a trustworthy `light_pos` mapping, they should render as non-editable rather than pretending to work.

## Failure Handling

The screen must distinguish:
- `clean`
- `dirty`
- `verified`
- `unverified`
- `failed`

Rules:
- failed initial read disables editing and shows a real error
- failed apply keeps staged edits intact
- unverified apply keeps the new rendered state visible but marks the result honestly
- reset always drops staged edits and restores last known device state

## Testing

### Backend

Add tests for:
- per-key response model generation
- `ui_key` to `light_pos` resolution
- staged diff merge into custom frame
- per-key apply endpoint success path
- per-key apply endpoint invalid key failure path

### Frontend

Add tests for:
- Lighting screen load from API
- rendered-state overlay logic
- selection-driven inspector behavior
- staging multiple single-key edits locally
- apply action payload shape
- reset behavior

### Manual hardware

After implementation:
- load Lighting screen and confirm current key colors appear automatically
- select a key and stage a new color
- confirm that key changes visually before apply
- apply staged edits
- confirm physical keyboard matches the staged keys

## Acceptance Criteria

This slice is done when:
- the Lighting screen loads real per-key colors automatically
- selecting a key reveals a real color editor in the inspector
- staged edits are visible directly on the keyboard visual before apply
- applying staged edits changes the physical keyboard
- reset discards staged edits cleanly
- unsupported/unmapped keys are clearly non-editable instead of silently failing
