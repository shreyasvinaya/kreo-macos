"""HID transport helpers for Bytech report exchange."""

from __future__ import annotations


def pad_output_report(data: bytes, report_size: int) -> bytes:
    """Right-pad an output report to the device's fixed report length."""

    if len(data) > report_size:
        raise ValueError("report larger than HID output report size")

    return data.ljust(report_size, b"\x00")

