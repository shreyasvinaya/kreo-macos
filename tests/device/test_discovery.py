from types import SimpleNamespace

from kreo_kontrol.device.discovery import find_supported_devices, wireless_receiver_present


def test_find_supported_devices_recognizes_wireless_receiver() -> None:
    devices = [
        {"vendor_id": 0x3554, "product_id": 0xFA09, "usage_page": 0xFF02, "usage": 0x02},
    ]

    result = find_supported_devices(devices)

    assert len(result) == 1
    assert result[0].product_name == "Kreo Swarm"
    assert result[0].protocol == "bytech"


def test_find_supported_devices_accepts_keyboard_receiver_fallback_interface() -> None:
    devices = [
        {"vendor_id": 0x3554, "product_id": 0xFA09, "usage_page": 0x0001, "usage": 0x06},
    ]

    result = find_supported_devices(devices)

    assert len(result) == 1
    assert result[0].product_name == "Kreo Swarm"
    assert result[0].protocol == "bytech"


def test_find_supported_devices_filters_kreo_swarm() -> None:
    devices = [
        {"vendor_id": 0x258A, "product_id": 0x010C, "usage_page": 0xFF00, "usage": 0x01},
        {"vendor_id": 0x1234, "product_id": 0x5678, "usage_page": 0x0001, "usage": 0x06},
    ]

    result = find_supported_devices(devices)

    assert len(result) == 1
    assert result[0].product_name == "Kreo Swarm"


def test_wireless_receiver_present_uses_hid_enumeration(monkeypatch) -> None:
    fake_hid = SimpleNamespace(
        enumerate=lambda: [
            {
                "vendor_id": 0x3554,
                "product_id": 0xFA09,
                "usage_page": 0xFF02,
                "usage": 0x02,
            }
        ]
    )

    monkeypatch.setattr(
        "kreo_kontrol.device.discovery.import_module",
        lambda _name: fake_hid,
    )

    assert wireless_receiver_present() is True
