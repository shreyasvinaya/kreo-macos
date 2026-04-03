# Kreo Lighting Global Write Design

Date: 2026-04-03

## Goal

Implement the first real device-backed lighting write path for the Kreo Swarm configurator.

This slice covers:

- global brightness writes
- static global color writes
- typed backend lighting apply contract
- verification status reporting for inferred lighting commands

This slice explicitly does not include per-key RGB yet. Per-key RGB follows only after global brightness and static color are working on real hardware.

## Scope

This subproject includes:

- extending the lighting domain model with writable state
- adding `POST /api/lighting/apply`
- mapping lighting apply requests to the inferred `lighting.apply` command family
- trace recording for lighting writes
- verification status reporting: `verified`, `unverified`, `failed`

This subproject does not include:

- per-key RGB writes
- non-static advanced lighting modes beyond what is needed for the first global write path
- pretending unsupported lighting features work

## Product Direction

The first lighting hardware write should be conservative and narrow.

The correct sequence is:

1. implement global brightness write
2. verify it on hardware
3. extend the same path to static color
4. verify that on hardware
5. only then start per-key RGB

This keeps the first confirmed write debuggable and avoids mixing scalar brightness and color payload problems in one opaque change.

## Backend Contract

The backend lighting contract should expose:

- `GET /api/lighting`
- `POST /api/lighting/apply`

### Read Contract

The read contract should return:

- `mode`
- `brightness`
- optional `color`
- `per_key_rgb_supported`
- `verification_status`

### Apply Contract

The apply contract should accept a typed payload containing:

- `mode`
- optional `brightness`
- optional `color`

For this slice, only these writes are honored:

- `brightness`
- `color` when `mode == "static"`

If the payload requests unsupported combinations, the backend must reject them instead of silently ignoring them.

## Lighting Domain Model

The lighting domain should be extended to carry:

- current `mode`
- current `brightness`
- optional `color`
- `per_key_rgb_supported`
- `verification_status`

Suggested verification status values:

- `verified`
- `unverified`
- `failed`

## Execution Flow

For a lighting apply request:

1. frontend sends a typed lighting update
2. backend validates the request
3. backend maps the request to the inferred `lighting.apply` command family
4. backend executes the write through the protocol session
5. backend records trace metadata, including confidence level
6. backend attempts verification
7. backend returns the resulting lighting state plus verification status

## Verification Model

Because `lighting.apply` is currently inferred, the app must not collapse “write sent” into “write confirmed.”

### Verified

Use `verified` only when the backend can confirm the intended post-write state through deterministic re-read or equivalent state reconciliation.

### Unverified

Use `unverified` when:

- the write appears transport-successful
- but the backend cannot yet prove the final device state

This is an acceptable interim state for the first hardware write slice.

### Failed

Use `failed` when:

- transport fails
- validation fails
- the device contradicts the intended state
- verification detects a mismatch

## User Feedback

The Lighting screen should eventually show:

- global brightness control
- static color control
- apply action
- last-write verification status
- recent trace information for the lighting command

For this backend slice, the important requirement is that the API response supports that UI honestly.

The app must never report a write as fully successful if it is only `unverified`.

## Expected Hardware Behavior

The first two hardware checks should be:

### Brightness

When brightness write works, the entire keyboard should visibly dim or brighten.

### Static Color

When static color write works, the entire keyboard should visibly shift to the selected color.

If the keyboard visibly changes but backend verification remains incomplete, the response should still say `unverified`.

## Safety Rules

- no per-key RGB in this slice
- no firmware flashing
- no bootloader/update commands
- reject unsupported payload combinations explicitly
- do not report fake success

## Testing Strategy

Testing should cover:

### Backend

- typed apply request validation
- brightness apply request behavior
- static color apply request behavior
- unsupported payload rejection
- verification status propagation

### Manual Hardware Verification

Run in order:

1. apply a brightness decrease
2. observe whether the full board dims
3. apply a brightness increase
4. observe whether the full board brightens
5. apply a static color change
6. observe whether the full board changes color

## Acceptance Criteria

This slice is complete when:

- `POST /api/lighting/apply` exists
- brightness writes can be sent through the backend
- static color writes can be sent through the backend
- the response clearly distinguishes `verified`, `unverified`, and `failed`
- the app does not claim certainty it does not have
- backend tests cover the new lighting write contract

## Future Follow-On

After this slice succeeds on hardware, the next lighting subproject is:

- per-key RGB editing and write verification
