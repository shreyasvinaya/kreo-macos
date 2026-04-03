# Kreo Bytech Protocol Core And Domain Expansion Design

Date: 2026-04-02

## Goal

Expand the Kreo Swarm configurator from a validated shell into a real device-backed configurator by:

- implementing a shared `bytech` protocol core
- exposing typed backend domain APIs for `Profiles`, `Keymap`, `Lighting`, and `Macros`
- enabling those four screens to become genuinely functional against the live keyboard

This subproject builds on the existing desktop shell, loopback API, frontend workspace, and diagnostics foundation already present in the repository.

## Scope

This subproject includes:

- shared packet/command metadata for the Kreo `bytech` protocol
- typed read/write methods for profile, keymap, lighting, and macro domains
- confidence tracking for `confirmed`, `inferred`, and `experimental` commands
- re-read verification after writes
- API surfaces for `Profiles`, `Keymap`, `Lighting`, and `Macros`
- screen-specific frontend behavior for all four domains

This subproject does not include:

- firmware flashing
- bootloader/update paths
- host-side remapping outside onboard device configuration
- support for unrelated keyboards

## Future Scope

The user wants `actuation point customization` in v2 if the hardware/controller exposes a safe configurable surface for it.

That is explicitly out of scope for this subproject because:

- it is not yet confirmed that the Kreo Swarm firmware exposes an actuation-control protocol
- the current protocol-first effort is focused on `Profiles`, `Keymap`, `Lighting`, and `Macros`

If actuation control is later found in the `bytech` command surface, it should be treated as a separate follow-on subproject with its own safety review and hardware validation.

## Product Direction

The implementation should be protocol-first, then domain-parallel.

The shared protocol layer is the dependency bottleneck for all four domain screens. Because of that, the correct sequence is:

1. implement the protocol core locally
2. stabilize typed contracts for all four domains
3. execute `Profiles`, `Keymap`, `Lighting`, and `Macros` as separate workers against that shared contract

This avoids duplicated packet logic and conflicting command assumptions.

## Protocol Confidence Model

The protocol core must classify commands into three confidence levels:

### Confirmed

Commands directly validated from:

- observed Kreo app behavior
- existing hardware interaction already reproduced locally
- successful request/response verification on the keyboard

These commands are safe to expose in the normal UI.

### Inferred

Commands whose structure is strongly implied by:

- the minified Kreo bundle
- adjacent packet families
- naming, payload shape, or table structure patterns

These commands may be used in normal flows only if they also require post-write verification. The UI must not report success until the relevant domain is re-read and reconciled.

### Experimental

Commands with insufficient confidence for normal use.

These remain hidden from the standard UI and may only be used behind a developer-only flag or omitted entirely from this subproject.

## Architecture

The subproject adds four new layers of responsibility on top of the existing foundation.

### 1. Protocol Registry

Responsibilities:

- define command names
- define payload/report metadata
- define domain ownership
- define confidence level
- define verification strategy

This becomes the single source of truth for what the backend believes the device supports.

### 2. Domain Adapters

Responsibilities:

- translate typed domain actions into command sequences
- assemble domain reads from one or more packet exchanges
- perform writes and immediate verification reads
- normalize raw device responses into typed domain models

There should be one adapter per domain:

- `profiles`
- `keymap`
- `lighting`
- `macros`

### 3. Typed Backend APIs

The frontend must never construct raw HID packets.

The backend should expose typed endpoints such as:

- `GET /api/profiles`
- `POST /api/profiles/activate`
- `POST /api/profiles/import`
- `GET /api/keymap`
- `POST /api/keymap/apply`
- `GET /api/lighting`
- `POST /api/lighting/apply`
- `GET /api/macros`
- `POST /api/macros/apply`

These endpoints should return:

- typed domain data
- confidence metadata where relevant
- verification status for the last write
- user-facing errors when a write cannot be confirmed

### 4. Screen Implementations

Once the typed APIs exist, each screen can own:

- screen layout
- local editing state
- dirty/apply/reset flow
- inline validation
- success/error rendering

without knowledge of packet structure.

## Domain Contracts

### Profiles

The `Profiles` domain must support:

- reading hardware profile slots
- identifying the active profile
- switching the active profile
- cloning or copying state between slots if protocol support exists
- exporting and importing app-side snapshots independently of onboard slot count

If copy/clone is not safely supported by the verified protocol, the UI must disable that action instead of faking it.

### Keymap

The `Keymap` domain must support:

- reading base-layer assignments
- reading FN-layer assignments
- selecting a physical key from the visual layout
- assigning supported actions to a key
- applying one or more remap changes
- re-reading affected state after apply

The UI should present unsupported actions as unavailable, not silently accepted.

### Lighting

The `Lighting` domain must support:

- reading global lighting mode
- reading editable lighting parameters where supported
- applying global lighting changes
- enabling per-key RGB editing only if the relevant commands verify successfully on this keyboard

Per-key RGB is explicitly in scope, but only as verified device behavior. If verification fails, the UI must keep the control disabled or mark it unsupported.

### Macros

The `Macros` domain must support:

- reading available macro slots
- reading macro bindings
- editing macro event sequences
- validating storage limits before apply
- writing macro data
- binding a macro to a key

The macro editor must reject invalid writes before they reach the device where possible.

## Data Flow

The data flow for each editable domain should be:

1. read the current device state into a typed domain model
2. allow local edits in the frontend
3. mark the domain dirty
4. submit a typed apply request to the backend
5. execute the required protocol writes
6. immediately re-read the relevant domain or affected subset
7. compare the verified device state against the intended write
8. report success only if the verification result matches

If verification fails:

- the UI must remain dirty or enter an error state
- the user must see that the write was not confirmed
- the trace should record the failed verification

## UX Structure

The overall application shell remains the current Keychron-style left-sidebar workspace, but each domain screen must become functionally distinct.

### Dashboard

Dashboard remains a summary screen, not the main editing surface. It shows:

- connected device
- active profile
- protocol/domain capability summary
- recent verified writes
- last sync status

### Profiles Screen

The screen should show:

- profile slots
- active slot
- slot actions
- app-side snapshot import/export

### Keymap Screen

The screen should show:

- keyboard visual
- base/FN layer toggle
- selected key details
- assignment picker
- apply/reset controls

### Lighting Screen

The screen should show:

- lighting mode selector
- global controls for supported parameters
- per-key visual editor if verified
- apply/reset controls

### Macros Screen

The screen should show:

- macro slot list
- event timeline/editor
- binding target
- validation and apply/reset controls

## Safety Rules

The following rules are mandatory:

- no firmware flashing
- no bootloader/update commands
- no destructive protocol surfaces outside the intended configuration domain
- inferred commands require verification reads before success is reported
- unsupported features must be shown as unavailable
- failed verification must never be rendered as success

## Testing Strategy

Testing should be split across four layers.

### Protocol Tests

- registry tests for command metadata
- encoder/decoder tests from fixtures
- verification-path tests for confirmed and inferred writes

### Backend API Tests

- domain read endpoint tests
- domain apply endpoint tests
- error-path tests for failed verification

### Frontend Tests

- per-screen state tests
- apply/reset behavior
- unsupported/disabled control rendering
- navigation to distinct real screens

### Manual Hardware Verification

After each domain lands:

- read real device state
- perform one minimal edit
- apply
- re-read
- unplug/replug if needed to verify persistence

## Execution Strategy

The implementation should proceed in two phases.

### Phase 1: Protocol Core

Build:

- protocol registry
- domain models
- domain adapters
- typed backend endpoints
- verification and trace support

This phase is not parallelized across screens because it is shared infrastructure.

### Phase 2: Parallel Domain Screens

After the protocol core stabilizes, run four disjoint workers:

- `Profiles` worker
- `Keymap` worker
- `Lighting` worker
- `Macros` worker

Each worker owns its screen plus the frontend/backend integration specific to that domain, but does not redefine protocol semantics.

## Acceptance Criteria

This subproject is successful when:

- the backend exposes real typed domain APIs for all four domains
- each of the four domain screens is materially distinct and device-backed
- writes use verification and do not report fake success
- unsupported features are explicit in the UI
- inferred commands are contained behind the verification model
- the repository has automated tests covering protocol, backend, and frontend behavior for the new work

## Self-Review

### Placeholder Scan

No `TODO`, `TBD`, or intentionally vague “handle appropriately” style requirements remain.

### Internal Consistency

The architecture keeps raw packet handling in Python, typed APIs at the boundary, and distinct frontend domain screens on top of that boundary.

### Scope Check

This is scoped as one subproject with two phases:

- one shared protocol phase
- one parallel domain phase

This is the largest shape that still has a coherent dependency chain.

### Ambiguity Check

The treatment of inferred commands is explicit:

- they are allowed
- they require verification
- they are not reported as successful without verified re-read results
