"""Device discovery helpers for supported Bytech keyboards."""

from __future__ import annotations

from kreo_kontrol.device.models import SupportedDevice

SUPPORTED_DEVICES: tuple[SupportedDevice, ...] = (
    SupportedDevice(
        vendor_id=0x258A,
        product_id=0x010C,
        usage_page=0xFF00,
        usage=0x01,
        product_name="Kreo Swarm",
        protocol="bytech",
    ),
)


def find_supported_devices(raw_devices: list[dict[str, int]]) -> list[SupportedDevice]:
    """Filter raw HID descriptors down to supported keyboards."""

    matches: list[SupportedDevice] = []

    for raw in raw_devices:
        for device in SUPPORTED_DEVICES:
            if (
                raw["vendor_id"] == device.vendor_id
                and raw["product_id"] == device.product_id
                and raw["usage_page"] == device.usage_page
                and raw["usage"] == device.usage
            ):
                matches.append(device)

    return matches
