from pathlib import Path

from fastapi.testclient import TestClient

from kreo_kontrol.api.app import create_app


def test_profiles_endpoint_returns_typed_payload(tmp_path: Path) -> None:
    client = TestClient(create_app(saved_profiles_path=tmp_path / "profiles.json"))

    response = client.get("/api/profiles")

    assert response.status_code == 200
    payload = response.json()
    assert payload["supported"] is True
    assert payload["active_profile"] is None
    assert payload["available_profiles"] == []
    assert payload["storage_kind"] == "saved_snapshots"
