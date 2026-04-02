from fastapi.testclient import TestClient

from kreo_kontrol.api.app import create_app


def test_profiles_endpoint_returns_typed_payload() -> None:
    client = TestClient(create_app())

    response = client.get("/api/profiles")

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_profile"] == 1
    assert payload["available_profiles"] == [1, 2, 3]
