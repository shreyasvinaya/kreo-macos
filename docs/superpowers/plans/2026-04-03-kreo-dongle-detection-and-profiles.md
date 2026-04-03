# Kreo Dongle Detection And Profiles

**Goal:** Detect both wired and wireless receiver connections honestly, make the UI reflect real connection/configurability state, and implement live profiles support on the configurable path.

## File Structure

- Modify: `src/kreo_kontrol/device/discovery.py`
  - add session-level detection for wired vendor HID and wireless receiver HID
- Modify: `src/kreo_kontrol/device/bytech_lighting.py`
  - expose a real session summary
  - keep configurability tied to the wired/vendor-HID path
  - add profile read/activate support if the configurable path is present
- Modify: `src/kreo_kontrol/api/models.py`
  - expand device and profiles response types to include transport/configurable status
- Modify: `src/kreo_kontrol/api/app.py`
  - wire `/api/device` and `/api/profiles` to live controller-backed session/profile state
- Modify: `tests/api/test_app.py`
  - lock live device session response shape
- Modify: `tests/api/test_domain_endpoints.py`
  - lock live profile response shape
- Modify: `tests/device/test_discovery.py`
  - add detection coverage for wired vendor HID and wireless receiver HID
- Modify: `tests/device/test_bytech_lighting.py`
  - add controller session/profile tests
- Modify: `frontend/src/lib/api.ts`
  - normalize richer device/profile payloads
- Modify: `frontend/src/App.tsx`
  - render truthful connection/configurability state
  - make the Profiles page live

## Task 1: Lock Detection And Device Session Behavior

- [ ] Add failing tests for:
  - wired vendor HID detection
  - wireless receiver detection
  - `/api/device` returning live `connected`, `configurable`, and transport details
- [ ] Run:
  - `uv run --group dev pytest tests/device/test_discovery.py tests/api/test_app.py -q`
- [ ] Implement the minimal discovery/session code to make those tests pass.

## Task 2: Lock Live Profiles Behavior

- [ ] Add failing tests for:
  - `/api/profiles` returning live active profile, available profiles, and configurability
  - controller-backed profile read on the configurable path
- [ ] Run:
  - `uv run --group dev pytest tests/api/test_domain_endpoints.py tests/device/test_bytech_lighting.py -q`
- [ ] Implement the minimal profile read/activate code to make those tests pass.

## Task 3: Wire The Frontend

- [ ] Add or update frontend tests for:
  - truthful connection status copy
  - profiles page consuming live payloads
- [ ] Run:
  - `cd frontend && bun test`
- [ ] Update the frontend API normalization and the `Profiles` page rendering so:
  - wireless shows connected but not fully configurable
  - wired shows connected and configurable
  - disconnected shows disconnected
  - the Profiles page uses the live profile payload

## Task 4: Verify End To End

- [ ] Run:
  - `cd frontend && bun test`
  - `cd frontend && bun run typecheck`
  - `cd frontend && bun run build`
  - `uv run --group dev pytest -q`
  - `uv run --group dev ruff check .`
  - `uv run --group dev ty check`
- [ ] Relaunch:
  - `uv run kreo-kontrol`
