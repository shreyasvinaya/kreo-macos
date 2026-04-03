"""Device discovery helpers for supported Bytech keyboards."""

from __future__ import annotations

from importlib import import_module

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
    SupportedDevice(
        vendor_id=0x3554,
        product_id=0xFA09,
        usage_page=0xFF02,
        usage=0x02,
        product_name="Kreo Swarm",
        protocol="bytech",
    ),
    SupportedDevice(
        vendor_id=0x3554,
        product_id=0xFA09,
        usage_page=0x0001,
        usage=0x06,
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


def wireless_receiver_present() -> bool:
    """Check whether the Kreo/CX 2.4G receiver is exposed through HID."""

    hid_module = import_module("hid")
    descriptors = [
        {
            "vendor_id": int(device.get("vendor_id", 0)),
            "product_id": int(device.get("product_id", 0)),
            "usage_page": int(device.get("usage_page", 0)),
            "usage": int(device.get("usage", 0)),
        }
        for device in hid_module.enumerate()
    ]
    return any(
        device.vendor_id == 0x3554 and device.product_id == 0xFA09
        for device in find_supported_devices(descriptors)
    )
