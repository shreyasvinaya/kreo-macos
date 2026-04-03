from fastapi.testclient import TestClient

from kreo_kontrol.api.app import create_app


def test_keyboard_asset_endpoint_returns_swarm75_metadata() -> None:
    client = TestClient(create_app())

    response = client.get("/api/keyboard-assets/swarm75")

    assert response.status_code == 200
    payload = response.json()
    assert payload["asset_name"] == "swarm75"
    assert payload["base_image_url"].endswith("/keyboard/swarm75/base/default.webp")
    assert payload["letters_image_url"].endswith("/keyboard/swarm75/letters/default.webp")
    assert payload["interactive_svg_url"].endswith("/keyboard/swarm75/overlay/interactive.svg")
    assert len(payload["keys"]) >= 80
    assert payload["keys"][0]["svg_id"].startswith("key_")


def test_keyboard_asset_endpoint_returns_404_for_unknown_asset() -> None:
    client = TestClient(create_app())

    response = client.get("/api/keyboard-assets/unknown")

    assert response.status_code == 404
