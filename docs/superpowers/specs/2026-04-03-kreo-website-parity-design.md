# Kreo Website Parity Design

## Goal

Bring the local Kreo Kontrol app to functional parity with the Kreo website experience for the Kreo Swarm by implementing:
- website-style keyboard rendering using the real keyboard assets
- device-backed lighting controls, including per-key RGB
- device-backed key remapping
- app-side saved profiles that package lighting, remaps, and macros
- macro editing where the Bytech protocol surface is verified

## Scope

Included:
- copy the `swarm75` keyboard assets from the local website dump into a real app asset directory
- serve those assets from the local app
- replace the custom keyboard renderer with the website asset model:
  - base image
  - letters image
  - interactive SVG
  - RGB mask SVG
- expose normalized keyboard asset metadata for the frontend
- implement full lighting workflows on top of the asset-based surface
- implement real keymap read/write workflows on top of the same surface
- implement app-side saved profiles/snapshots
- implement macro editing on verified protocol paths

Excluded:
- firmware flashing
- bootloader or recovery tooling
- pretending the keyboard supports onboard hardware profiles when the protocol does not expose them
- knob interaction unless the dumped protocol later proves it is configurable

## Existing Context

The current app already has:
- a local FastAPI backend
- a PySide desktop shell
- working device-backed Bytech lighting writes
- working device-backed per-key RGB writes
- receiver-path reverse engineering based on the Kreo website dump

The current gaps are:
- the keyboard UI is still a custom-rendered approximation instead of the website asset surface
- global lighting parity is incomplete
- key remapping is still mostly stubbed
- profiles are still modeled as hardware slots even though the dumped Bytech website logic says `supportsProfiles: false`
- macros are still stubbed

## Product Truth

The dumped website code establishes an important product boundary for this keyboard family:
- the Bytech keyboard path reports `supportsProfiles: false`
- true onboard profile slots are not available through the exposed protocol surface

The local app should therefore be explicit about the difference between:
- device-backed configuration:
  - lighting
  - per-key RGB
  - key remaps
  - macros where verified
- app-side saved profiles:
  - named local snapshots of keymap, lighting, and macros

The app must not market local snapshots as hardware profiles.

## Architecture

The parity build should be done in four phases.

### Phase 1: Asset-Based Keyboard Surface

Replace the current keyboard layout model with a data-driven keyboard surface based on the website assets.

Required assets:
- `base/default.png`
- `letters/default.png`
- `overlay/interactive.svg`
- `overlay/rgb-mask.svg`
- `meta/manifest.json`
- `meta/led-map.json`

These should be copied from `kreo_website_dump/` into a real app-owned asset directory so the app does not depend on ignored dump files at runtime.

The backend should expose a normalized keyboard metadata payload that includes:
- asset URLs
- key metadata from `led-map.json`
- mapping between `logicalId`, `svgId`, protocol positions, labels, and any UI key ids used by the app

The frontend should treat the SVG overlay as the source of truth for hit testing and selection.

### Phase 2: Lighting Parity

The Lighting screen should move onto the asset-based keyboard surface and support:
- current global lighting read
- mode selection
- brightness
- speed and direction where supported by the protocol
- static color
- preset lighting modes
- per-key RGB read
- staged per-key RGB editing on the SVG surface
- apply/reset behavior with explicit verification reporting

The board should remain image-based at all times. RGB state should be painted through the mask/overlay rather than through a synthetic key grid.

### Phase 3: Key Remap Parity

The Keymap screen should use the same SVG hit targets and support:
- live keymap read
- key selection from the actual board image
- base action editing
- FN action editing
- verified keymap writes

The first action library should be curated and device-relevant rather than exposing raw protocol bytes directly in the UI.

The UI should present macOS-friendly labels where appropriate, but the underlying device action model should remain protocol-accurate.

### Phase 4: Saved Profiles And Macros

Profiles should be implemented as local snapshots, not onboard slots.

Saved profiles should store:
- lighting state
- per-key RGB state
- keymap state
- macro assignments

The user should be able to:
- save
- rename
- duplicate
- delete
- import
- export
- apply

Macros should be device-backed if the verified protocol surface supports them cleanly on this board. If any macro write remains structurally inferred but not hardware-verified, it should be surfaced as experimental.

## Data Model Direction

The app should maintain a normalized keyboard identity model shared across Lighting and Keymap:
- `logicalId`
- `svgId`
- label
- protocol position
- optional UI-facing aliases

That shared model should become the canonical way to map:
- asset hit targets
- lighting entries
- keymap entries
- macro bindings

This removes the current duplication between custom lighting layout code and backend protocol mapping.

## UI Direction

The website asset surface should become the primary editor surface for both Lighting and Keymap.

Lighting:
- actual keyboard image with live/staged RGB rendering
- side inspector for selected key
- separate controls for global lighting and presets

Keymap:
- actual keyboard image with selected-key highlight
- side inspector for current action, FN action, and macro binding

Profiles:
- dedicated page for local snapshots

Macros:
- dedicated page for slot editing and binding

Device and Events should remain separate pages so editor screens stay focused.

## Verification Model

Every device-backed write should report one of:
- `verified`
- `unverified`
- `failed`

The app should never claim success when it only knows that a packet was sent.

If the dongle path is blocked by another WebHID client, the backend and UI should report that honestly instead of falling back to fake connected state or fake device data.

## Execution Order

Build order:
1. copy and serve website assets from a real app asset directory
2. add keyboard asset metadata endpoint
3. replace the Lighting keyboard renderer with the website asset surface
4. complete lighting parity on that surface
5. implement real keymap read/write backend
6. build the remap UI on the same surface
7. add app-side saved profiles
8. add macro read/write and editor UI

This order minimizes rework by establishing the shared keyboard surface first.

## Acceptance Criteria

This project is done when:
- the app uses the actual `swarm75` keyboard assets instead of the custom synthetic layout
- Lighting supports global effects and per-key RGB on the real board surface
- Keymap supports live read/write remapping on the real board surface
- Profiles are available as honest app-side saved snapshots
- Macros are editable and device-backed where verified
- all supported writes are verified or explicitly marked unverified
- the app no longer depends on `kreo_website_dump/` at runtime
