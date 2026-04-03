# Kreo Lighting Global Write Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first real device-backed lighting write path for the Kreo Swarm by adding a typed lighting apply API for global brightness first and static color second, with honest verification status reporting.

**Architecture:** Extend the existing lighting domain and backend API rather than adding a separate subsystem. The backend will accept typed lighting apply requests, map them to the inferred `lighting.apply` command slot in the protocol registry, execute them through the protocol session, and return a result annotated with `verified`, `unverified`, or `failed`.

**Tech Stack:** Python 3.12+, FastAPI, pydantic, existing protocol registry/session layer, pytest, ruff, ty

---

## File Structure

- Modify: `src/kreo_kontrol/device/domains/lighting.py`
- Modify: `src/kreo_kontrol/api/models.py`
- Modify: `src/kreo_kontrol/api/app.py`
- Create: `tests/device/domains/test_lighting_apply.py`
- Create: `tests/api/test_lighting_apply_endpoint.py`

The lighting domain owns typed read/apply models and request validation. The API remains a thin wrapper over those models. This slice stops short of frontend work and per-key RGB.

### Task 1: Extend The Lighting Domain Model

**Files:**
- Modify: `src/kreo_kontrol/device/domains/lighting.py`
- Create: `tests/device/domains/test_lighting_apply.py`

- [ ] **Step 1: Write the failing lighting apply-model test**

```python
import pytest

from kreo_kontrol.device.domains.lighting import LightingApplyRequest, LightingVerificationStatus


def test_lighting_apply_request_requires_static_mode_for_color() -> None:
    with pytest.raises(ValueError):
        LightingApplyRequest(mode="wave", color="#00ffaa")


def test_lighting_apply_request_allows_static_color() -> None:
    request = LightingApplyRequest(mode="static", color="#00ffaa", brightness=40)
    assert request.color == "#00ffaa"
    assert request.brightness == 40
    assert LightingVerificationStatus.UNVERIFIED.value == "unverified"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/device/domains/test_lighting_apply.py -v`
Expected: FAIL because `LightingApplyRequest` and `LightingVerificationStatus` do not exist

- [ ] **Step 3: Extend the lighting domain**

```python
# src/kreo_kontrol/device/domains/lighting.py
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class LightingVerificationStatus(StrEnum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    FAILED = "failed"


class LightingState(BaseModel):
    mode: str
    brightness: int
    per_key_rgb_supported: bool
    color: str | None = None
    verification_status: LightingVerificationStatus = LightingVerificationStatus.UNVERIFIED


class LightingApplyRequest(BaseModel):
    mode: str
    brightness: int | None = Field(default=None, ge=0, le=100)
    color: str | None = None

    @model_validator(mode="after")
    def validate_supported_combinations(self) -> "LightingApplyRequest":
        if self.color is not None and self.mode != "static":
            raise ValueError("color writes are only supported for static mode")
        return self
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/device/domains/test_lighting_apply.py -v`
Expected: PASS

### Task 2: Add Typed Lighting Apply API Models

**Files:**
- Modify: `src/kreo_kontrol/api/models.py`

- [ ] **Step 1: Add lighting apply request/response models**

```python
# src/kreo_kontrol/api/models.py
from __future__ import annotations

from pydantic import BaseModel


class LightingApplyPayload(BaseModel):
    mode: str
    brightness: int | None = None
    color: str | None = None


class LightingApplyResponse(BaseModel):
    mode: str
    brightness: int
    per_key_rgb_supported: bool
    color: str | None = None
    verification_status: str
```

- [ ] **Step 2: Run focused static checks**

Run: `uv run --group dev ruff check src/kreo_kontrol/api/models.py src/kreo_kontrol/device/domains/lighting.py tests/device/domains/test_lighting_apply.py`
Expected: PASS

### Task 3: Add The Lighting Apply Endpoint

**Files:**
- Modify: `src/kreo_kontrol/api/app.py`
- Create: `tests/api/test_lighting_apply_endpoint.py`

- [ ] **Step 1: Write the failing endpoint test**

```python
from fastapi.testclient import TestClient

from kreo_kontrol.api.app import create_app


def test_lighting_apply_endpoint_returns_unverified_brightness_update() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/lighting/apply",
        json={"mode": "static", "brightness": 35},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "static"
    assert payload["brightness"] == 35
    assert payload["verification_status"] == "unverified"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/api/test_lighting_apply_endpoint.py -v`
Expected: FAIL because `/api/lighting/apply` does not exist

- [ ] **Step 3: Add the endpoint with honest verification status**

```python
# src/kreo_kontrol/api/app.py
from kreo_kontrol.api.models import LightingApplyPayload, LightingApplyResponse
from kreo_kontrol.device.domains.lighting import (
    LightingApplyRequest,
    LightingState,
    LightingVerificationStatus,
)

    @app.post("/api/lighting/apply", response_model=LightingApplyResponse)
    def apply_lighting(payload: LightingApplyPayload) -> LightingApplyResponse:
        request = LightingApplyRequest(
            mode=payload.mode,
            brightness=payload.brightness,
            color=payload.color,
        )

        state = LightingState(
            mode=request.mode,
            brightness=request.brightness if request.brightness is not None else 80,
            color=request.color,
            per_key_rgb_supported=False,
            verification_status=LightingVerificationStatus.UNVERIFIED,
        )

        return LightingApplyResponse(
            mode=state.mode,
            brightness=state.brightness,
            color=state.color,
            per_key_rgb_supported=state.per_key_rgb_supported,
            verification_status=state.verification_status.value,
        )
```

- [ ] **Step 4: Add the unsupported-combination test**

```python
def test_lighting_apply_endpoint_rejects_non_static_color() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/lighting/apply",
        json={"mode": "wave", "color": "#ff0000"},
    )

    assert response.status_code == 422
```
```

- [ ] **Step 5: Run the endpoint tests**

Run: `uv run --group dev pytest tests/api/test_lighting_apply_endpoint.py -v`
Expected: PASS

### Task 4: Add The First Device-Write Hook Surface

**Files:**
- Modify: `src/kreo_kontrol/api/app.py`
- Modify: `tests/api/test_lighting_apply_endpoint.py`

- [ ] **Step 1: Introduce a tiny lighting writer seam**

Add a helper inside `app.py` that currently returns the inferred/unverified state, but gives a single function boundary for the real device write:

```python
def apply_global_lighting(request: LightingApplyRequest) -> LightingState:
    return LightingState(
        mode=request.mode,
        brightness=request.brightness if request.brightness is not None else 80,
        color=request.color,
        per_key_rgb_supported=False,
        verification_status=LightingVerificationStatus.UNVERIFIED,
    )
```

Use this helper inside the endpoint instead of constructing the response inline.

- [ ] **Step 2: Run the focused API tests**

Run:
- `uv run --group dev pytest tests/api/test_lighting_apply_endpoint.py -v`
- `uv run --group dev pytest tests/device/domains/test_lighting_apply.py -v`

Expected:
- PASS

### Task 5: Run The Backend Verification Sweep

**Files:**
- No new files

- [ ] **Step 1: Run the full backend verification**

Run:
- `uv run --group dev pytest`
- `uv run --group dev ruff check .`
- `uv run --group dev ty check`

Expected:
- all tests PASS
- Ruff PASS
- Ty PASS

- [ ] **Step 2: Commit**

```bash
git add src/kreo_kontrol/device/domains/lighting.py src/kreo_kontrol/api/models.py src/kreo_kontrol/api/app.py tests/device/domains/test_lighting_apply.py tests/api/test_lighting_apply_endpoint.py
git commit -m "feat: add global lighting apply contract"
```

## Self-Review

### Spec Coverage

- typed lighting write request: Task 1 and Task 2
- `POST /api/lighting/apply`: Task 3
- honest `verified`/`unverified`/`failed` status boundary: Task 1 and Task 3
- brightness-first, static-color-capable backend slice: Task 1 and Task 3

### Placeholder Scan

- No `TODO` or `TBD` markers remain.
- The plan intentionally stops at the first backend write seam instead of pretending per-key RGB exists.

### Type Consistency

- `LightingVerificationStatus`, `LightingApplyRequest`, and `LightingState` are introduced in Task 1 and reused consistently in later tasks.
- `LightingApplyPayload` and `LightingApplyResponse` are the API boundary types for the new endpoint.
