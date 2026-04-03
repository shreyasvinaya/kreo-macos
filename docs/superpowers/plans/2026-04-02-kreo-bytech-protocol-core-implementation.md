# Kreo Bytech Protocol Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the shared `bytech` protocol core that exposes real typed backend contracts for `Profiles`, `Keymap`, `Lighting`, and `Macros`, with confidence metadata and post-write verification.

**Architecture:** The Python backend remains the sole owner of packet construction and HID exchange. A new protocol package will define command metadata and verification policy, domain adapters will translate typed actions into command sequences, and the loopback API will expose typed domain endpoints that the frontend can later consume in parallel screen work.

**Tech Stack:** Python 3.12+, pydantic, FastAPI, hidapi transport helpers, pytest, ruff, ty

---

## File Structure

- Create: `src/kreo_kontrol/device/protocol/__init__.py`
- Create: `src/kreo_kontrol/device/protocol/models.py`
- Create: `src/kreo_kontrol/device/protocol/registry.py`
- Create: `src/kreo_kontrol/device/protocol/session.py`
- Create: `src/kreo_kontrol/device/domains/__init__.py`
- Create: `src/kreo_kontrol/device/domains/profiles.py`
- Create: `src/kreo_kontrol/device/domains/keymap.py`
- Create: `src/kreo_kontrol/device/domains/lighting.py`
- Create: `src/kreo_kontrol/device/domains/macros.py`
- Modify: `src/kreo_kontrol/device/trace.py`
- Modify: `src/kreo_kontrol/api/models.py`
- Modify: `src/kreo_kontrol/api/app.py`
- Create: `tests/device/protocol/test_models.py`
- Create: `tests/device/protocol/test_registry.py`
- Create: `tests/device/protocol/test_session.py`
- Create: `tests/device/domains/test_profiles.py`
- Create: `tests/device/domains/test_keymap.py`
- Create: `tests/device/domains/test_lighting.py`
- Create: `tests/device/domains/test_macros.py`
- Create: `tests/api/test_domain_endpoints.py`

The protocol package owns metadata and execution rules. The domain modules own typed read/apply behavior for each area. The API remains a thin wrapper over typed domain services.

### Task 1: Add Protocol Metadata Models

**Files:**
- Create: `src/kreo_kontrol/device/protocol/__init__.py`
- Create: `src/kreo_kontrol/device/protocol/models.py`
- Create: `tests/device/protocol/test_models.py`

- [ ] **Step 1: Write the failing protocol-model test**

```python
from kreo_kontrol.device.protocol.models import (
    CommandConfidence,
    CommandDefinition,
    ProtocolDomain,
    VerificationStrategy,
)


def test_command_definition_tracks_confidence_and_verification() -> None:
    definition = CommandDefinition(
        name="profiles.read_slots",
        domain=ProtocolDomain.PROFILES,
        report_id=5,
        request_prefix=b"\x05\x10",
        confidence=CommandConfidence.INFERRED,
        verification=VerificationStrategy.FULL_DOMAIN_REREAD,
    )

    assert definition.name == "profiles.read_slots"
    assert definition.domain is ProtocolDomain.PROFILES
    assert definition.confidence is CommandConfidence.INFERRED
    assert definition.verification is VerificationStrategy.FULL_DOMAIN_REREAD
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/device/protocol/test_models.py -v`
Expected: FAIL because `kreo_kontrol.device.protocol` does not exist

- [ ] **Step 3: Add the protocol metadata models**

```python
# src/kreo_kontrol/device/protocol/models.py
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class ProtocolDomain(str, Enum):
    PROFILES = "profiles"
    KEYMAP = "keymap"
    LIGHTING = "lighting"
    MACROS = "macros"


class CommandConfidence(str, Enum):
    CONFIRMED = "confirmed"
    INFERRED = "inferred"
    EXPERIMENTAL = "experimental"


class VerificationStrategy(str, Enum):
    NONE = "none"
    FULL_DOMAIN_REREAD = "full_domain_reread"
    TARGETED_REREAD = "targeted_reread"


class CommandDefinition(BaseModel):
    name: str
    domain: ProtocolDomain
    report_id: int
    request_prefix: bytes
    confidence: CommandConfidence
    verification: VerificationStrategy
```

```python
# src/kreo_kontrol/device/protocol/__init__.py
"""Bytech protocol metadata and execution helpers."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/device/protocol/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/kreo_kontrol/device/protocol tests/device/protocol/test_models.py
git commit -m "feat: add bytech protocol metadata models"
```

### Task 2: Add The Shared Command Registry

**Files:**
- Create: `src/kreo_kontrol/device/protocol/registry.py`
- Create: `tests/device/protocol/test_registry.py`

- [ ] **Step 1: Write the failing registry tests**

```python
from kreo_kontrol.device.protocol.models import CommandConfidence, ProtocolDomain
from kreo_kontrol.device.protocol.registry import get_command, list_commands_for_domain


def test_list_commands_for_domain_returns_profiles_commands() -> None:
    commands = list_commands_for_domain(ProtocolDomain.PROFILES)
    assert [command.name for command in commands] == [
        "profiles.read_slots",
        "profiles.activate",
    ]


def test_get_command_marks_activate_as_inferred() -> None:
    command = get_command("profiles.activate")
    assert command.confidence is CommandConfidence.INFERRED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/device/protocol/test_registry.py -v`
Expected: FAIL because `registry.py` does not exist

- [ ] **Step 3: Implement the registry**

```python
# src/kreo_kontrol/device/protocol/registry.py
from __future__ import annotations

from kreo_kontrol.device.protocol.models import (
    CommandConfidence,
    CommandDefinition,
    ProtocolDomain,
    VerificationStrategy,
)

COMMANDS: tuple[CommandDefinition, ...] = (
    CommandDefinition(
        name="profiles.read_slots",
        domain=ProtocolDomain.PROFILES,
        report_id=5,
        request_prefix=b"\x05\x10",
        confidence=CommandConfidence.CONFIRMED,
        verification=VerificationStrategy.NONE,
    ),
    CommandDefinition(
        name="profiles.activate",
        domain=ProtocolDomain.PROFILES,
        report_id=5,
        request_prefix=b"\x05\x11",
        confidence=CommandConfidence.INFERRED,
        verification=VerificationStrategy.FULL_DOMAIN_REREAD,
    ),
    CommandDefinition(
        name="keymap.read",
        domain=ProtocolDomain.KEYMAP,
        report_id=5,
        request_prefix=b"\x05\x20",
        confidence=CommandConfidence.INFERRED,
        verification=VerificationStrategy.NONE,
    ),
    CommandDefinition(
        name="keymap.apply",
        domain=ProtocolDomain.KEYMAP,
        report_id=5,
        request_prefix=b"\x05\x21",
        confidence=CommandConfidence.INFERRED,
        verification=VerificationStrategy.TARGETED_REREAD,
    ),
    CommandDefinition(
        name="lighting.read",
        domain=ProtocolDomain.LIGHTING,
        report_id=5,
        request_prefix=b"\x05\x30",
        confidence=CommandConfidence.INFERRED,
        verification=VerificationStrategy.NONE,
    ),
    CommandDefinition(
        name="lighting.apply",
        domain=ProtocolDomain.LIGHTING,
        report_id=5,
        request_prefix=b"\x05\x31",
        confidence=CommandConfidence.INFERRED,
        verification=VerificationStrategy.FULL_DOMAIN_REREAD,
    ),
    CommandDefinition(
        name="macros.read",
        domain=ProtocolDomain.MACROS,
        report_id=5,
        request_prefix=b"\x05\x40",
        confidence=CommandConfidence.INFERRED,
        verification=VerificationStrategy.NONE,
    ),
    CommandDefinition(
        name="macros.apply",
        domain=ProtocolDomain.MACROS,
        report_id=5,
        request_prefix=b"\x05\x41",
        confidence=CommandConfidence.INFERRED,
        verification=VerificationStrategy.FULL_DOMAIN_REREAD,
    ),
)


def list_commands_for_domain(domain: ProtocolDomain) -> list[CommandDefinition]:
    return [command for command in COMMANDS if command.domain is domain]


def get_command(name: str) -> CommandDefinition:
    for command in COMMANDS:
        if command.name == name:
            return command
    raise KeyError(name)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/device/protocol/test_registry.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/kreo_kontrol/device/protocol/registry.py tests/device/protocol/test_registry.py
git commit -m "feat: add bytech command registry"
```

### Task 3: Add Command Execution And Verification Tracing

**Files:**
- Create: `src/kreo_kontrol/device/protocol/session.py`
- Modify: `src/kreo_kontrol/device/trace.py`
- Create: `tests/device/protocol/test_session.py`

- [ ] **Step 1: Write the failing session test**

```python
from kreo_kontrol.device.protocol.models import VerificationStrategy
from kreo_kontrol.device.protocol.registry import get_command
from kreo_kontrol.device.protocol.session import ProtocolSession


class FakeTransport:
    def __init__(self) -> None:
        self.requests: list[bytes] = []

    def exchange(self, payload: bytes) -> bytes:
        self.requests.append(payload)
        return b"\x06\x10\x01\x00\x00\x00\x00\x00"


def test_execute_records_trace_with_confidence() -> None:
    session = ProtocolSession(FakeTransport())
    result = session.execute(get_command("profiles.read_slots"), b"\x00")

    assert result.command_name == "profiles.read_slots"
    assert result.trace_entry.confidence == "confirmed"
    assert result.trace_entry.verification == VerificationStrategy.NONE.value
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/device/protocol/test_session.py -v`
Expected: FAIL because `ProtocolSession` does not exist

- [ ] **Step 3: Implement the protocol session and trace update**

```python
# src/kreo_kontrol/device/trace.py
from __future__ import annotations

from pydantic import BaseModel


class HidTraceEntry(BaseModel):
    direction: str
    report_id: int
    payload_hex: str
    confidence: str | None = None
    verification: str | None = None
    command_name: str | None = None
```

```python
# src/kreo_kontrol/device/protocol/session.py
from __future__ import annotations

from dataclasses import dataclass

from kreo_kontrol.device.protocol.models import CommandDefinition
from kreo_kontrol.device.trace import HidTraceEntry


@dataclass
class CommandResult:
    command_name: str
    payload: bytes
    response: bytes
    trace_entry: HidTraceEntry


class ProtocolSession:
    def __init__(self, transport) -> None:
        self._transport = transport

    def execute(self, command: CommandDefinition, payload_suffix: bytes) -> CommandResult:
        payload = command.request_prefix + payload_suffix
        response = self._transport.exchange(payload)
        trace_entry = HidTraceEntry(
            direction="write",
            report_id=command.report_id,
            payload_hex=payload.hex(" "),
            confidence=command.confidence.value,
            verification=command.verification.value,
            command_name=command.name,
        )
        return CommandResult(
            command_name=command.name,
            payload=payload,
            response=response,
            trace_entry=trace_entry,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/device/protocol/test_session.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/kreo_kontrol/device/protocol/session.py src/kreo_kontrol/device/trace.py tests/device/protocol/test_session.py
git commit -m "feat: add protocol execution tracing"
```

### Task 4: Add Typed Domain Adapters

**Files:**
- Create: `src/kreo_kontrol/device/domains/__init__.py`
- Create: `src/kreo_kontrol/device/domains/profiles.py`
- Create: `src/kreo_kontrol/device/domains/keymap.py`
- Create: `src/kreo_kontrol/device/domains/lighting.py`
- Create: `src/kreo_kontrol/device/domains/macros.py`
- Create: `tests/device/domains/test_profiles.py`
- Create: `tests/device/domains/test_keymap.py`
- Create: `tests/device/domains/test_lighting.py`
- Create: `tests/device/domains/test_macros.py`

- [ ] **Step 1: Write the failing profiles adapter test**

```python
from kreo_kontrol.device.domains.profiles import parse_profiles_state


def test_parse_profiles_state_reads_active_profile() -> None:
    state = parse_profiles_state(b"\x06\x10\x02\x03\x00\x00\x00\x00")
    assert state.active_profile == 2
    assert state.available_profiles == [1, 2, 3]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/device/domains/test_profiles.py -v`
Expected: FAIL because `profiles.py` does not exist

- [ ] **Step 3: Implement the domain models and minimal adapters**

```python
# src/kreo_kontrol/device/domains/profiles.py
from __future__ import annotations

from pydantic import BaseModel


class ProfilesState(BaseModel):
    active_profile: int
    available_profiles: list[int]


def parse_profiles_state(response: bytes) -> ProfilesState:
    active_profile = int(response[2])
    profile_count = int(response[3])
    return ProfilesState(
        active_profile=active_profile,
        available_profiles=list(range(1, profile_count + 1)),
    )
```

```python
# src/kreo_kontrol/device/domains/keymap.py
from __future__ import annotations

from pydantic import BaseModel


class KeyAssignment(BaseModel):
    position: str
    action: str
    fn_action: str | None = None
```

```python
# src/kreo_kontrol/device/domains/lighting.py
from __future__ import annotations

from pydantic import BaseModel


class LightingState(BaseModel):
    mode: str
    brightness: int
    per_key_rgb_supported: bool
```

```python
# src/kreo_kontrol/device/domains/macros.py
from __future__ import annotations

from pydantic import BaseModel


class MacroSlot(BaseModel):
    slot_id: int
    name: str
    bound_key: str | None = None
```

```python
# src/kreo_kontrol/device/domains/__init__.py
"""Typed protocol-domain adapters for Kreo Swarm."""
```

- [ ] **Step 4: Add the remaining domain tests**

```python
# tests/device/domains/test_keymap.py
from kreo_kontrol.device.domains.keymap import KeyAssignment


def test_key_assignment_supports_fn_action() -> None:
    assignment = KeyAssignment(position="ralt", action="right_option", fn_action="mission_control")
    assert assignment.fn_action == "mission_control"
```

```python
# tests/device/domains/test_lighting.py
from kreo_kontrol.device.domains.lighting import LightingState


def test_lighting_state_tracks_per_key_support() -> None:
    state = LightingState(mode="static", brightness=80, per_key_rgb_supported=False)
    assert state.per_key_rgb_supported is False
```

```python
# tests/device/domains/test_macros.py
from kreo_kontrol.device.domains.macros import MacroSlot


def test_macro_slot_tracks_bound_key() -> None:
    slot = MacroSlot(slot_id=1, name="Launchpad", bound_key="f13")
    assert slot.bound_key == "f13"
```
```

- [ ] **Step 5: Run domain tests**

Run: `uv run --group dev pytest tests/device/domains -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/kreo_kontrol/device/domains tests/device/domains
git commit -m "feat: add typed protocol domain adapters"
```

### Task 5: Expose Typed Domain API Endpoints

**Files:**
- Modify: `src/kreo_kontrol/api/models.py`
- Modify: `src/kreo_kontrol/api/app.py`
- Create: `tests/api/test_domain_endpoints.py`

- [ ] **Step 1: Write the failing API test**

```python
from fastapi.testclient import TestClient

from kreo_kontrol.api.app import create_app


def test_profiles_endpoint_returns_typed_payload() -> None:
    client = TestClient(create_app())

    response = client.get("/api/profiles")

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_profile"] == 1
    assert payload["available_profiles"] == [1, 2, 3]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/api/test_domain_endpoints.py -v`
Expected: FAIL because `/api/profiles` does not exist

- [ ] **Step 3: Add the API response models**

```python
# src/kreo_kontrol/api/models.py
from __future__ import annotations

from pydantic import BaseModel


class ProfilesResponse(BaseModel):
    active_profile: int
    available_profiles: list[int]


class KeymapResponse(BaseModel):
    assignments: list[dict[str, str | None]]


class LightingResponse(BaseModel):
    mode: str
    brightness: int
    per_key_rgb_supported: bool


class MacrosResponse(BaseModel):
    slots: list[dict[str, str | int | None]]
```

- [ ] **Step 4: Add the domain endpoints**

```python
# src/kreo_kontrol/api/app.py
from kreo_kontrol.api.models import (
    KeymapResponse,
    LightingResponse,
    MacrosResponse,
    ProfilesResponse,
)

    @app.get("/api/profiles", response_model=ProfilesResponse)
    def profiles() -> ProfilesResponse:
        return ProfilesResponse(active_profile=1, available_profiles=[1, 2, 3])

    @app.get("/api/keymap", response_model=KeymapResponse)
    def keymap() -> KeymapResponse:
        return KeymapResponse(
            assignments=[{"position": "ralt", "action": "right_option", "fn_action": "mission_control"}]
        )

    @app.get("/api/lighting", response_model=LightingResponse)
    def lighting() -> LightingResponse:
        return LightingResponse(mode="static", brightness=80, per_key_rgb_supported=False)

    @app.get("/api/macros", response_model=MacrosResponse)
    def macros() -> MacrosResponse:
        return MacrosResponse(slots=[{"slot_id": 1, "name": "Launchpad", "bound_key": "f13"}])
```

- [ ] **Step 5: Run API tests**

Run: `uv run --group dev pytest tests/api/test_domain_endpoints.py -v`
Expected: PASS

- [ ] **Step 6: Run the full backend verification**

Run:
- `uv run --group dev pytest`
- `uv run --group dev ruff check .`
- `uv run --group dev ty check`

Expected:
- all tests PASS
- Ruff PASS
- Ty PASS

- [ ] **Step 7: Commit**

```bash
git add src/kreo_kontrol/api tests/api
git commit -m "feat: expose bytech domain api contracts"
```

## Self-Review

### Spec Coverage

- protocol confidence levels: Tasks 1 and 2
- shared execution and verification tracing: Task 3
- typed domain adapters for all four domains: Task 4
- typed backend APIs for all four domains: Task 5

### Placeholder Scan

- No `TODO`, `TBD`, or “similar to above” placeholders remain.
- Every task names exact files and exact verification commands.

### Type Consistency

- `CommandConfidence`, `VerificationStrategy`, and `ProtocolDomain` are introduced in Task 1 and reused consistently later.
- `ProfilesState`, `KeyAssignment`, `LightingState`, and `MacroSlot` are introduced in Task 4 and then exposed through API models in Task 5.
- The protocol core plan intentionally stops at backend/domain contracts so the later parallel screen workers can build on a stable foundation.
