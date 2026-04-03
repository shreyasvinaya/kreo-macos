# Kreo Bytech Configurator Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working milestone of the Kreo Swarm configurator: packaged Python app shell, embedded webview, local API, typed Bytech HID foundation, and a modern diagnostics UI.

**Architecture:** A Python desktop process owns HID access, state, and protocol logic. It starts a loopback-only FastAPI server that serves a built React frontend into a PySide6 webview. The frontend talks only to typed backend endpoints; the backend owns all raw HID details.

**Tech Stack:** Python 3.12+, uv, FastAPI, Uvicorn, PySide6, hidapi, pydantic, React, TypeScript, Vite, bun, pytest, ruff, ty

---

### Task 1: Bootstrap The Monorepo Layout

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `src/kreo_kontrol/__init__.py`
- Create: `src/kreo_kontrol/main.py`
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `tests/test_smoke.py`

- [ ] **Step 1: Write the failing backend smoke test**

```python
from importlib import import_module


def test_package_imports() -> None:
    module = import_module("kreo_kontrol")
    assert module.__name__ == "kreo_kontrol"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_smoke.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'kreo_kontrol'`

- [ ] **Step 3: Add the minimal Python package scaffold**

```toml
[project]
name = "kreo-kontrol"
version = "0.1.0"
description = "Local macOS configurator for the Kreo Swarm Bytech keyboard"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115",
  "hidapi>=0.14",
  "pydantic>=2.11",
  "pyside6>=6.9",
  "uvicorn>=0.34",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3",
  "ruff>=0.11",
  "ty>=0.0.1a16",
]

[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

```python
# src/kreo_kontrol/__init__.py
"""Kreo Swarm Bytech configurator."""
```

- [ ] **Step 4: Add the frontend scaffold**

```json
{
  "name": "frontend",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build"
  },
  "dependencies": {
    "react": "^19.1.0",
    "react-dom": "^19.1.0"
  },
  "devDependencies": {
    "@types/react": "^19.1.2",
    "@types/react-dom": "^19.1.2",
    "@vitejs/plugin-react": "^4.4.1",
    "typescript": "^5.8.3",
    "vite": "^6.3.0"
  }
}
```

```tsx
// frontend/src/App.tsx
export function App(): JSX.Element {
  return <main>Kreo Kontrol</main>;
}
```

- [ ] **Step 5: Add a practical `.gitignore`**

```gitignore
.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
.cache/
.config/
.local/
frontend/node_modules/
frontend/dist/
dist/
build/
```

- [ ] **Step 6: Run the smoke test**

Run: `uv run pytest tests/test_smoke.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .gitignore src frontend tests
git commit -m "chore: bootstrap configurator workspace"
```

### Task 2: Add Typed Device Models And Discovery

**Files:**
- Create: `src/kreo_kontrol/device/models.py`
- Create: `src/kreo_kontrol/device/discovery.py`
- Create: `tests/device/test_discovery.py`

- [ ] **Step 1: Write the failing discovery tests**

```python
from kreo_kontrol.device.discovery import find_supported_devices


def test_find_supported_devices_filters_kreo_swarm() -> None:
    devices = [
        {"vendor_id": 0x258A, "product_id": 0x010C, "usage_page": 0xFF00, "usage": 0x01},
        {"vendor_id": 0x1234, "product_id": 0x5678, "usage_page": 0x0001, "usage": 0x06},
    ]
    result = find_supported_devices(devices)
    assert len(result) == 1
    assert result[0].product_name == "Kreo Swarm"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/device/test_discovery.py -v`
Expected: FAIL because `kreo_kontrol.device.discovery` does not exist

- [ ] **Step 3: Implement the supported-device registry and models**

```python
# src/kreo_kontrol/device/models.py
from pydantic import BaseModel


class SupportedDevice(BaseModel):
    vendor_id: int
    product_id: int
    usage_page: int
    usage: int
    product_name: str
    protocol: str
```

```python
# src/kreo_kontrol/device/discovery.py
from kreo_kontrol.device.models import SupportedDevice

SUPPORTED_DEVICES = [
    SupportedDevice(
        vendor_id=0x258A,
        product_id=0x010C,
        usage_page=0xFF00,
        usage=0x01,
        product_name="Kreo Swarm",
        protocol="bytech",
    )
]


def find_supported_devices(raw_devices: list[dict[str, int]]) -> list[SupportedDevice]:
    matches: list[SupportedDevice] = []
    for raw in raw_devices:
        for device in SUPPORTED_DEVICES:
            if (
                raw["vendor_id"] == device.vendor_id
                and raw["product_id"] == device.product_id
                and raw["usage_page"] == device.usage_page
                and raw["usage"] == device.usage
            ):
                matches.append(device)
    return matches
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/device/test_discovery.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/kreo_kontrol/device tests/device
git commit -m "feat: add supported device discovery"
```

### Task 3: Implement HID Transport And Diagnostics Trace Model

**Files:**
- Create: `src/kreo_kontrol/device/transport.py`
- Create: `src/kreo_kontrol/device/trace.py`
- Create: `tests/device/test_transport.py`

- [ ] **Step 1: Write the failing transport tests**

```python
from kreo_kontrol.device.transport import pad_output_report


def test_pad_output_report_respects_report_size() -> None:
    assert pad_output_report(b"\x05\x01", 8) == b"\x05\x01\x00\x00\x00\x00\x00\x00"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/device/test_transport.py -v`
Expected: FAIL because `pad_output_report` is undefined

- [ ] **Step 3: Implement the minimal transport helpers**

```python
# src/kreo_kontrol/device/transport.py
def pad_output_report(data: bytes, report_size: int) -> bytes:
    if len(data) > report_size:
        raise ValueError("report larger than HID output report size")
    return data.ljust(report_size, b"\x00")
```

```python
# src/kreo_kontrol/device/trace.py
from pydantic import BaseModel


class HidTraceEntry(BaseModel):
    direction: str
    report_id: int
    payload_hex: str
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/device/test_transport.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/kreo_kontrol/device/transport.py src/kreo_kontrol/device/trace.py tests/device/test_transport.py
git commit -m "feat: add hid transport helpers"
```

### Task 4: Add The Local API Skeleton

**Files:**
- Create: `src/kreo_kontrol/api/app.py`
- Create: `src/kreo_kontrol/api/models.py`
- Create: `tests/api/test_app.py`

- [ ] **Step 1: Write the failing API test**

```python
from fastapi.testclient import TestClient

from kreo_kontrol.api.app import create_app


def test_health_endpoint() -> None:
    client = TestClient(create_app())
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/api/test_app.py -v`
Expected: FAIL because the API app does not exist

- [ ] **Step 3: Implement the minimal API**

```python
# src/kreo_kontrol/api/app.py
from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI()

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/device")
    def device() -> dict[str, object]:
        return {"connected": False, "supported_devices": []}

    return app
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/api/test_app.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/kreo_kontrol/api tests/api
git commit -m "feat: add local api skeleton"
```

### Task 5: Add The PySide6 Desktop Shell

**Files:**
- Create: `src/kreo_kontrol/shell/window.py`
- Modify: `src/kreo_kontrol/main.py`
- Create: `tests/shell/test_main.py`

- [ ] **Step 1: Write the failing shell test**

```python
from kreo_kontrol.main import build_app_url


def test_build_app_url_uses_loopback() -> None:
    assert build_app_url(8123) == "http://127.0.0.1:8123"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/shell/test_main.py -v`
Expected: FAIL because `build_app_url` does not exist

- [ ] **Step 3: Implement the shell entrypoint**

```python
# src/kreo_kontrol/main.py
def build_app_url(port: int) -> str:
    return f"http://127.0.0.1:{port}"
```

```python
# src/kreo_kontrol/shell/window.py
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QMainWindow


class MainWindow(QMainWindow):
    def __init__(self, url: str) -> None:
        super().__init__()
        self.setWindowTitle("Kreo Kontrol")
        self.resize(1480, 980)
        view = QWebEngineView(self)
        view.setUrl(url)
        self.setCentralWidget(view)
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/shell/test_main.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/kreo_kontrol/main.py src/kreo_kontrol/shell tests/shell
git commit -m "feat: add desktop shell entrypoint"
```

### Task 6: Build A Modern Diagnostics UI

**Files:**
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/styles.css`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/components/device-card.tsx`
- Create: `frontend/src/components/trace-panel.tsx`

- [ ] **Step 1: Add a failing frontend smoke test placeholder**

```ts
export function renderStatus(status: "connected" | "disconnected"): string {
  return status === "connected" ? "Connected" : "Disconnected";
}
```

- [ ] **Step 2: Build the diagnostics UI**

```tsx
// frontend/src/App.tsx
import "./styles.css";

export function App(): JSX.Element {
  return (
    <main className="app-shell">
      <section className="hero-panel">
        <p className="eyebrow">Bytech Configurator</p>
        <h1>Kreo Kontrol</h1>
        <p className="lede">
          Local-first configurator for the Kreo Swarm. This build focuses on transport,
          protocol visibility, and a hardware-centric editor foundation.
        </p>
      </section>
      <section className="workspace-grid">
        <article className="device-card">No device connected</article>
        <article className="trace-panel">No trace entries yet</article>
      </section>
    </main>
  );
}
```

- [ ] **Step 3: Add intentional visual styling**

```css
/* frontend/src/styles.css */
:root {
  --bg: #0a0d12;
  --panel: #111722;
  --panel-2: #182131;
  --text: #edf3ff;
  --muted: #8ea1bd;
  --accent: #6ee7b7;
  --accent-2: #7dd3fc;
}

body {
  margin: 0;
  background:
    radial-gradient(circle at top right, rgba(125, 211, 252, 0.18), transparent 24rem),
    radial-gradient(circle at bottom left, rgba(110, 231, 183, 0.14), transparent 22rem),
    var(--bg);
  color: var(--text);
  font-family: "Jost", "Avenir Next", sans-serif;
}
```

- [ ] **Step 4: Build the frontend**

Run: `cd frontend && bun install && bun run build`
Expected: build output in `frontend/dist`

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "feat: add diagnostics web ui"
```

### Task 7: Verify The Foundation End To End

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document the new app workflow**

```md
## Configurator Foundation

Run backend checks:

```sh
uv run pytest
uv run ruff check .
uv run ty check
```

Run the frontend:

```sh
cd frontend
bun install
bun run build
```
```

- [ ] **Step 2: Run backend verification**

Run: `uv run pytest`
Expected: PASS

Run: `uv run ruff check .`
Expected: PASS

Run: `uv run ty check`
Expected: PASS

- [ ] **Step 3: Run frontend build verification**

Run: `cd frontend && bun run build`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add foundation workflow"
```

## Self-Review

### Spec Coverage

- desktop shell: Task 5
- local API boundary: Task 4
- typed HID foundation: Tasks 2 and 3
- modern diagnostics UI: Task 6
- verification workflow: Task 7

### Placeholder Scan

- No `TODO` or `TBD` markers remain in the tasks.
- Each task names concrete files and commands.

### Type Consistency

- `SupportedDevice` is the typed device model used by discovery.
- `pad_output_report` is the initial transport helper referenced by tests.
- `create_app` is the API entrypoint consumed by the tests.
- `build_app_url` is the shell utility referenced by the shell test.
