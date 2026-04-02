from kreo_kontrol.device.domains.profiles import parse_profiles_state


def test_parse_profiles_state_reads_active_profile() -> None:
    state = parse_profiles_state(b"\x06\x10\x02\x03\x00\x00\x00\x00")
    assert state.active_profile == 2
    assert state.available_profiles == [1, 2, 3]
