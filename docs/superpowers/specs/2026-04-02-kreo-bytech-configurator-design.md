# Kreo Swarm Bytech Configurator Design

Date: 2026-04-02

## Goal

Build a local macOS desktop app for the Kreo Swarm keyboard that configures the existing onboard firmware over the keyboard's `bytech` HID protocol.

The app's v1 scope is:

- profiles
- onboard key remapping
- FN-layer remapping
- lighting modes
- per-key RGB
- macros and macro binding

The app is not a firmware replacement project and does not attempt to add QMK support.

## Non-Goals

- flashing firmware
- entering bootloader/update modes
- macOS host-side remapping in the style of Karabiner
- generic support for unrelated keyboards in v1
- reverse-engineering commands outside the configuration surface already used by Kreo's web app

## Context

The connected keyboard is identified locally as:

- product: `Kreo Swarm`
- vendor: `BY Tech`
- vendor ID: `0x258A`
- product ID: `0x010C`

Kreo's web app at `https://kontrol.kreo-tech.com/` contains a `bytech` device entry for this exact keyboard family and uses WebHID against a vendor-defined interface with:

- usage page `0xFF00`
- usage `0x01`

The app bundle also exposes concepts for:

- profile selection
- key-function remapping
- macro storage
- lighting mode and color control
- flash read/write
- per-key LED maps

This is sufficient evidence to design the configurator around the existing vendor protocol rather than QMK/VIA.

## Product Direction

Use a packaged local desktop app with:

- a Python backend for HID/protocol work
- an embedded webview frontend for the editor UI

This is preferred over a fully native widget UI because the keyboard visualizer, per-key RGB editor, and macro tooling are materially easier to build and iterate in a web-style interface.

## Selected Tech Direction

The implementation should use:

- Python `3.12+`
- `uv` for Python environment and dependency management
- `hidapi` for HID transport
- `pydantic` models for typed protocol/domain data
- `PySide6` for the macOS desktop shell and embedded webview
- `React + TypeScript + Vite` for the frontend
- `bun` for frontend package management and script execution
- `pytest`, `ruff`, and `ty` for backend verification

The app should run as a single local desktop application:

- the Python process owns HID access and app lifecycle
- a loopback-only local API serves the built frontend and typed app endpoints
- the embedded webview loads that local app surface

This gives a clean boundary between UI and protocol logic without coupling the frontend to Python-only bridge mechanics.

## Architecture

The app is split into four layers.

### 1. macOS Shell

Responsibilities:

- launch the application
- host the embedded webview
- manage app lifecycle

This layer does not contain protocol logic.

### 2. Python Service

Responsibilities:

- device discovery
- HID connection lifecycle
- loopback-only local API lifecycle
- command execution and serialization
- normalized state model
- config/profile persistence on disk
- safety checks and logging

This is the main application backend.

### 3. Bytech Protocol Adapter

Responsibilities:

- packet encoding and decoding
- mapping high-level app actions to vendor HID commands
- read/write helpers for profiles, keymap, macros, and lighting
- command acknowledgement and verification

This layer hides raw packet details from the rest of the app.

### 4. UI

Responsibilities:

- device dashboard
- profile manager
- keymap editor
- FN editor
- macro editor
- lighting mode editor
- per-key RGB editor
- pending changes / apply flow

## Frontend Design Direction

The UI must look intentional and hardware-centric, not like a generic admin panel.

Requirements:

- the main interaction surface should center around the keyboard, not tables-first navigation
- use a distinct visual identity with custom design tokens instead of default component-library styling
- favor dense, tool-like editing layouts over oversized marketing-style cards
- make profile state, dirty state, and device sync state visually prominent
- support fast keyboard selection, color editing, and macro inspection without deep modal stacks

The visual reference can borrow the clarity of Keychron Launcher, but the final result should feel more specialized to one device family and less like a white-label web dashboard.

## Core Model

The keyboard is treated as a small onboard configuration database with five editable domains.

### Device Session

- connected/disconnected state
- device identity
- protocol capability flags
- firmware/version information if readable
- busy/error state

### Profiles

- hardware profile slots
- active profile
- app-side exported snapshots

### Keymap

- base layer key assignments
- FN-layer assignments
- special key functions

### Macros

- macro definitions
- key bindings to macro slots
- validation against device limits

### Lighting

- global lighting mode
- speed/brightness/direction/color settings where supported
- per-key RGB payloads for custom lighting

## Data Flow

The UI edits an in-memory working model, not the keyboard directly.

Flow:

1. Connect to the keyboard over the `bytech` HID interface.
2. Read current state into a normalized model.
3. Let the user edit locally.
4. Mark affected domains as dirty.
5. Apply changes explicitly by domain.
6. Re-read the written domain and reconcile the result.

This staged write model is required for:

- safe multi-step changes
- usable per-key RGB editing
- macro editing without partial corruption
- reliable undo/cancel behavior
- app-side profile export

## UX Structure

The UI should borrow the clarity of tools like Keychron Launcher but stay specific to the Kreo/Bytech protocol.

### Main Sections

- Dashboard
- Profiles
- Keymap
- Macros
- Lighting
- Settings / Diagnostics

### Dashboard

Shows:

- connected device name
- active profile
- dirty/pending change state
- protocol support summary
- last sync time
- recent write verification status

### Profiles

Supports:

- switch active hardware profile
- clone profile to another slot
- export profile snapshot to disk
- import saved snapshot into working state

### Keymap

Supports:

- clickable keyboard visualizer
- base and FN layer switching
- key assignment picker
- conflict/unsupported function validation

### Macros

Supports:

- macro list
- editor for press/release events and delays
- assignment of macros to keys
- validation against device storage limits

### Lighting

Supports:

- built-in effect modes
- speed/brightness/direction settings
- single-color and multi-color modes where supported
- per-key RGB editor using the device LED map

## Safety Boundaries

The app must stay inside the same safe protocol surface Kreo's web app already uses.

Allowed:

- configuration reads
- configuration writes
- profile changes
- macro updates
- lighting updates

Blocked in v1:

- bootloader commands
- firmware update paths
- undocumented destructive commands

Any command not backed by packet evidence is classified as:

- `confirmed`: captured and verified
- `inferred`: structurally consistent but not capture-verified
- `experimental`: hidden behind developer mode

Only `confirmed` commands are exposed in the normal UI.

## Protocol Strategy

The first implementation milestone is protocol-first.

Order:

1. device discovery and connection
2. typed packet transport
3. protocol fixture capture and decoding
4. minimal UI shell
5. profile read/write
6. keymap and FN editing
7. lighting mode control
8. per-key RGB
9. macro editor

This sequencing keeps the reverse-engineering work isolated from the UI.

## API Boundary

The frontend should never construct raw HID packets.

Instead it talks to typed backend endpoints such as:

- `GET /api/device`
- `GET /api/profiles`
- `POST /api/profiles/activate`
- `GET /api/keymap`
- `POST /api/keymap/apply`
- `GET /api/lighting`
- `POST /api/lighting/apply`
- `GET /api/macros`
- `POST /api/macros/apply`

Developer-only diagnostics can expose:

- command trace stream
- decoded packet preview
- last response payload

The transport and protocol adapter remain private to the backend.

## Persistence

The app should keep local state for:

- saved app-side profile snapshots
- macro drafts before apply
- last connected device info
- logs and protocol traces in developer mode

Local snapshots are separate from onboard profiles so the user is not limited by keyboard slot count.

## Error Handling

The app must handle:

- device disconnected during edit
- timeout waiting for response
- partial domain write failures
- unsupported command for current firmware
- verification mismatch after write

Behavior:

- preserve unsaved working edits locally
- surface domain-specific errors
- never silently assume writes succeeded
- require explicit retry for failed writes

## Testing Strategy

Three layers of verification are required.

### Protocol Unit Tests

- packet encoding/decoding
- address and size validation
- macro serialization
- per-key RGB packing

### Integration Tests

- mocked HID transport
- expected response sequences
- retry and timeout behavior

### Manual Hardware Verification

On the real keyboard:

- connect and identify device
- read each editable domain
- write and re-read each domain
- unplug/replug persistence checks
- regression checks after multi-domain updates

## Initial Deliverable

The first shipped milestone is not the full polished configurator. It is:

- working Python app shell
- embedded webview
- HID transport and typed protocol layer
- minimal diagnostics UI
- enough protocol support to prove safe read/write on the keyboard

Full keymap, RGB, and macro tooling are layered on top of that foundation.

## Decision Summary

- build around the existing `bytech` protocol
- package as a local macOS desktop app
- use Python backend plus embedded webview UI
- include profiles, onboard remapping, per-key RGB, and macros in v1 scope
- exclude firmware replacement and host-side remapping from v1
