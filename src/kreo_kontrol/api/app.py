"""FastAPI application factory for the local configurator backend."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from kreo_kontrol.api.models import (
    DeviceSummary,
    HealthStatus,
    KeymapResponse,
    LightingApplyPayload,
    LightingApplyResponse,
    LightingResponse,
    MacrosResponse,
    PerKeyLightingApplyPayload,
    PerKeyLightingResponse,
    ProfilesResponse,
)
from kreo_kontrol.device.bytech_lighting import (
    LightingController,
    LightingHardwareUnavailableError,
    LightingProtocolError,
    StubLightingController,
)
from kreo_kontrol.device.domains.lighting import (
    LightingApplyRequest,
)


def resolve_frontend_dist(frontend_dist: Path | None = None) -> Path:
    """Resolve the built frontend directory used by the embedded shell."""

    if frontend_dist is not None:
        return frontend_dist

    return Path(__file__).resolve().parents[3] / "frontend" / "dist"


def create_app(
    frontend_dist: Path | None = None,
    lighting_controller: LightingController | None = None,
) -> FastAPI:
    """Build the loopback API application."""

    app = FastAPI(title="Kreo Kontrol API")
    dist_path = resolve_frontend_dist(frontend_dist)
    controller = lighting_controller or StubLightingController()

    @app.get("/api/health", response_model=HealthStatus)
    def health() -> HealthStatus:
        return HealthStatus(status="ok")

    @app.get("/api/device", response_model=DeviceSummary)
    def device() -> DeviceSummary:
        return DeviceSummary(
            connected=controller.is_connected(),
            supported_devices=controller.supported_devices(),
        )

    @app.get("/api/profiles", response_model=ProfilesResponse)
    def profiles() -> ProfilesResponse:
        return ProfilesResponse(active_profile=1, available_profiles=[1, 2, 3])

    @app.get("/api/keymap", response_model=KeymapResponse)
    def keymap() -> KeymapResponse:
        return KeymapResponse(
            assignments=[
                {
                    "position": "ralt",
                    "action": "right_option",
                    "fn_action": "mission_control",
                }
            ]
        )

    @app.get("/api/lighting", response_model=LightingResponse)
    def lighting() -> LightingResponse:
        state = controller.read_state()
        return LightingResponse(
            mode=state.mode,
            brightness=state.brightness,
            per_key_rgb_supported=state.per_key_rgb_supported,
            color=state.color,
            verification_status=state.verification_status.value,
        )

    @app.post("/api/lighting/apply", response_model=LightingApplyResponse)
    def apply_lighting(payload: LightingApplyPayload) -> LightingApplyResponse:
        try:
            request = LightingApplyRequest(
                mode=payload.mode,
                brightness=payload.brightness,
                color=payload.color,
            )
        except ValidationError as exc:
            raise HTTPException(
                status_code=422,
                detail=[
                    {
                        "loc": list(error["loc"]),
                        "msg": error["msg"],
                        "type": error["type"],
                    }
                    for error in exc.errors()
                ],
            ) from exc

        try:
            state = controller.apply_global_lighting(request)
        except LightingHardwareUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except LightingProtocolError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        return LightingApplyResponse(
            mode=state.mode,
            brightness=state.brightness,
            per_key_rgb_supported=state.per_key_rgb_supported,
            color=state.color,
            verification_status=state.verification_status.value,
        )

    @app.get("/api/lighting/per-key", response_model=PerKeyLightingResponse)
    def lighting_per_key() -> PerKeyLightingResponse:
        try:
            payload = controller.read_per_key_state()
        except LightingHardwareUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except LightingProtocolError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        return PerKeyLightingResponse.model_validate(payload)

    @app.post("/api/lighting/per-key/apply", response_model=PerKeyLightingResponse)
    def apply_per_key_lighting(payload: PerKeyLightingApplyPayload) -> PerKeyLightingResponse:
        try:
            result = controller.apply_per_key_colors_by_ui_key(payload.edits)
        except LightingHardwareUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except LightingProtocolError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        return PerKeyLightingResponse.model_validate(result)

    @app.get("/api/macros", response_model=MacrosResponse)
    def macros() -> MacrosResponse:
        return MacrosResponse(
            slots=[{"slot_id": 1, "name": "Launchpad", "bound_key": "f13"}]
        )

    if dist_path.exists():
        assets_path = dist_path / "assets"
        if assets_path.exists():
            app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

        @app.get("/", include_in_schema=False)
        def index() -> FileResponse:
            return FileResponse(dist_path / "index.html")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str) -> FileResponse:
            candidate = dist_path / path
            if candidate.is_file():
                return FileResponse(candidate)

            return FileResponse(dist_path / "index.html")
    else:

        @app.get("/", include_in_schema=False)
        def missing_frontend() -> HTMLResponse:
            return HTMLResponse(
                """
                <!doctype html>
                <html lang="en">
                  <head><meta charset="utf-8" /><title>Kreo Kontrol</title></head>
                  <body>
                    <main>
                      <h1>Kreo Kontrol frontend not built</h1>
                      <p>
                        Run <code>bun install</code> and <code>bun run build</code>
                        in <code>frontend/</code>.
                      </p>
                    </main>
                  </body>
                </html>
                """.strip(),
                status_code=503,
            )

    return app
