"""Keyboard asset metadata loaders for the local configurator API."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import HTTPException

from kreo_kontrol.api.models import KeyboardAssetKey, KeyboardAssetResponse
from kreo_kontrol.device.bytech_lighting import map_logical_id_to_ui_key


def resolve_keyboard_assets_root() -> Path:
    """Return the vendored keyboard asset root."""

    return Path(__file__).resolve().parents[3] / "frontend" / "public" / "keyboard"


def resolve_existing_asset_url(asset_root: Path, relative_path: str) -> str:
    """Resolve a vendored asset path, tolerating manifest extension mismatches."""

    candidate = asset_root / relative_path
    if candidate.exists():
        return f"/keyboard/{asset_root.name}/{relative_path}"

    stem = candidate.with_suffix("")
    for suffix in (".webp", ".png", ".svg"):
        alternate = stem.with_suffix(suffix)
        if alternate.exists():
            relative = alternate.relative_to(asset_root).as_posix()
            return f"/keyboard/{asset_root.name}/{relative}"

    raise HTTPException(status_code=404, detail=f"missing asset file for {relative_path}")


def load_keyboard_asset(asset_name: str) -> KeyboardAssetResponse:
    """Load normalized keyboard asset metadata for the requested board."""

    asset_root = resolve_keyboard_assets_root() / asset_name
    manifest_path = asset_root / "meta" / "manifest.json"
    led_map_path = asset_root / "meta" / "led-map.json"
    if not manifest_path.exists() or not led_map_path.exists():
        raise HTTPException(status_code=404, detail=f"unknown keyboard asset {asset_name}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    led_map = json.loads(led_map_path.read_text(encoding="utf-8"))

    default_variant = manifest.get("defaultVariant", "default")
    variant_map = {
        variant["id"]: variant["baseImage"]
        for variant in manifest.get("variants", [])
        if isinstance(variant, dict)
        and isinstance(variant.get("id"), str)
        and isinstance(variant.get("baseImage"), str)
    }
    base_image = variant_map.get(default_variant, "default.webp")
    base_image_url = resolve_existing_asset_url(
        asset_root,
        f"{manifest.get('baseImagePath', 'base')}/{base_image}",
    )
    letters_image_url = resolve_existing_asset_url(
        asset_root,
        manifest.get("letters", {}).get("default", "letters/default.webp"),
    )
    interactive_svg_url = resolve_existing_asset_url(
        asset_root,
        manifest.get("overlay", {}).get("interactiveSvg", "overlay/interactive.svg"),
    )

    keys: list[KeyboardAssetKey] = []
    for raw_key in led_map.get("keys", []):
        if not isinstance(raw_key, dict):
            continue
        logical_id = raw_key.get("logicalId")
        svg_id = raw_key.get("svgId")
        protocol_pos = raw_key.get("protocolPos")
        led_index = raw_key.get("ledIndex")
        if not all(
            [
                isinstance(logical_id, str),
                isinstance(svg_id, str),
                isinstance(protocol_pos, int),
                isinstance(led_index, int),
            ]
        ):
            continue
        ui_key, label = map_logical_id_to_ui_key(logical_id.upper())
        keys.append(
            KeyboardAssetKey(
                logical_id=logical_id.upper(),
                svg_id=svg_id,
                ui_key=ui_key,
                label=label,
                protocol_pos=protocol_pos,
                led_index=led_index,
            )
        )

    return KeyboardAssetResponse(
        asset_name=asset_name,
        base_image_url=base_image_url,
        letters_image_url=letters_image_url,
        interactive_svg_url=interactive_svg_url,
        keys=keys,
    )
