from kreo_kontrol.device.discovery import find_supported_devices


def test_find_supported_devices_filters_kreo_swarm() -> None:
    devices = [
        {"vendor_id": 0x258A, "product_id": 0x010C, "usage_page": 0xFF00, "usage": 0x01},
        {"vendor_id": 0x1234, "product_id": 0x5678, "usage_page": 0x0001, "usage": 0x06},
    ]

    result = find_supported_devices(devices)

    assert len(result) == 1
    assert result[0].product_name == "Kreo Swarm"
