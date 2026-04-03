from kreo_kontrol.device.transport import pad_output_report


def test_pad_output_report_respects_report_size() -> None:
    assert pad_output_report(b"\x05\x01", 8) == b"\x05\x01\x00\x00\x00\x00\x00\x00"
