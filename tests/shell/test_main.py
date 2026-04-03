from kreo_kontrol.main import build_app_url, build_server_config


def test_build_app_url_uses_loopback() -> None:
    assert build_app_url(8123) == "http://127.0.0.1:8123"


def test_build_server_config_uses_loopback_host() -> None:
    config = build_server_config(8123)

    assert config.host == "127.0.0.1"
    assert config.port == 8123
