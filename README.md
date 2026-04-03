# Kreo Keyboard Lab

This workspace contains a local-first configurator foundation for the `Kreo Swarm` keyboard over the existing `bytech` HID protocol.

## Configurator Foundation

The Python side owns HID access, supported-device discovery, transport helpers, and a loopback-only FastAPI app. The frontend is a Bun + React + Vite UI with a hardware-centric diagnostics surface that can grow into profile, macro, keymap, and RGB editors.

### Launch the desktop shell

```sh
uv run kreo-kontrol
```

### Capture modifier evidence

Run:

```sh
uv run kreo-kontrol-capture-modifiers
```

The script guides you through the confusing modifier/remap keys and writes a JSON results file under `captures/`.

### Saved profiles

Saved profiles are app-side snapshots. They currently replay:

- lighting state
- base-layer key remaps

FN-layer remap replay remains disabled until that protocol path is verified on this keyboard.

### Backend verification

```sh
uv run --group dev pytest
uv run --group dev ruff check .
uv run --group dev ty check
```

### Frontend verification

```sh
cd frontend
bun install
bun test
bun run typecheck
bun run build
```

### Current source layout

- `src/kreo_kontrol/` Python package scaffold for the desktop app, API, and device protocol layers
- `tests/` backend tests for package import, device discovery, transport helpers, API health, and shell URL building
- `frontend/` web UI, Bun test, and Vite build output
- `docs/superpowers/specs/` approved design spec
- `docs/superpowers/plans/` implementation plan for the current foundation milestone
