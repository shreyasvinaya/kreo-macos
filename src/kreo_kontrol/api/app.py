"""FastAPI application factory for the local configurator backend."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from kreo_kontrol.api.keyboard_assets import load_keyboard_asset
from kreo_kontrol.api.models import (
    CreateProfilePayload,
    DeviceSummary,
    HealthStatus,
    KeyboardAssetResponse,
    KeymapApplyPayload,
    KeymapResponse,
    LightingApplyPayload,
    LightingApplyResponse,
    LightingResponse,
    MacrosResponse,
    MacroUpsertPayload,
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
from kreo_kontrol.profiles.store import SavedProfilesStore, default_saved_profiles_path


def resolve_frontend_dist(frontend_dist: Path | None = None) -> Path:
    """Resolve the built frontend directory used by the embedded shell."""

    if frontend_dist is not None:
        return frontend_dist

    return Path(__file__).resolve().parents[3] / "frontend" / "dist"


def create_app(
    frontend_dist: Path | None = None,
    lighting_controller: LightingController | None = None,
    saved_profiles_path: Path | None = None,
) -> FastAPI:
    """Build the loopback API application."""

    app = FastAPI(title="Kreo Kontrol API")
    dist_path = resolve_frontend_dist(frontend_dist)
    controller = lighting_controller or StubLightingController()
    profiles_store = SavedProfilesStore(saved_profiles_path or default_saved_profiles_path())

    @app.get("/api/health", response_model=HealthStatus)
    def health() -> HealthStatus:
        return HealthStatus(status="ok")

    @app.get("/api/device", response_model=DeviceSummary)
    def device() -> DeviceSummary:
        return DeviceSummary(
            connected=controller.is_connected(),
            configurable=controller.configurable(),
            supported_devices=controller.supported_devices(),
            supports_profiles=controller.supports_profiles(),
            transport_kind=controller.transport_kind(),
        )

    @app.get("/api/keyboard-assets/{asset_name}", response_model=KeyboardAssetResponse)
    def keyboard_assets(asset_name: str) -> KeyboardAssetResponse:
        return load_keyboard_asset(asset_name)

    @app.get("/api/profiles", response_model=ProfilesResponse)
    def profiles() -> ProfilesResponse:
        return profiles_store.to_response()

    @app.post("/api/profiles", response_model=ProfilesResponse)
    def create_profile(payload: CreateProfilePayload) -> ProfilesResponse:
        return profiles_store.capture_current(controller, payload.name)

    @app.post("/api/profiles/{snapshot_id}/apply", response_model=ProfilesResponse)
    def apply_profile(snapshot_id: str) -> ProfilesResponse:
        try:
            return profiles_store.apply_snapshot(controller, snapshot_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/keymap", response_model=KeymapResponse)
    def keymap() -> KeymapResponse:
        return KeymapResponse.model_validate(controller.read_keymap())

    @app.post("/api/keymap/apply", response_model=KeymapResponse)
    def apply_keymap(payload: KeymapApplyPayload) -> KeymapResponse:
        result = controller.apply_keymap(
            {
                ui_key: {
                    "base_raw_value": edit.base_raw_value,
                    "fn_raw_value": edit.fn_raw_value,
                }
                for ui_key, edit in payload.edits.items()
            }
        )
        return KeymapResponse.model_validate(result)

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
        return MacrosResponse.model_validate(controller.read_macros())

    @app.put("/api/macros/{slot_id}", response_model=MacrosResponse)
    def upsert_macro(slot_id: int, payload: MacroUpsertPayload) -> MacrosResponse:
        try:
            result = controller.apply_macro(
                slot_id=slot_id,
                request={
                    "name": payload.name,
                    "bound_ui_key": payload.bound_ui_key,
                    "execution_type": payload.execution_type,
                    "cycle_times": payload.cycle_times,
                    "actions": [
                        {
                            "key": action.key,
                            "event_type": action.event_type,
                            "delay_ms": action.delay_ms,
                        }
                        for action in payload.actions
                    ],
                },
            )
        except LightingHardwareUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except LightingProtocolError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return MacrosResponse.model_validate(result)

    @app.delete("/api/macros/{slot_id}", response_model=MacrosResponse)
    def delete_macro(slot_id: int) -> MacrosResponse:
        try:
            result = controller.delete_macro(slot_id)
        except LightingHardwareUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except LightingProtocolError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return MacrosResponse.model_validate(result)

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
