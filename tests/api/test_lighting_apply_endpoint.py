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


def test_lighting_apply_endpoint_rejects_non_static_color() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/lighting/apply",
        json={"mode": "wave", "color": "#ff0000"},
    )

    assert response.status_code == 422


def test_lighting_apply_endpoint_accepts_effect_modes_without_color() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/lighting/apply",
        json={"mode": "wave", "brightness": 50},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "wave"
    assert payload["brightness"] == 50
