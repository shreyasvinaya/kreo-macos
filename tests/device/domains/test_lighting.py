from kreo_kontrol.device.domains.lighting import LightingState


def test_lighting_state_tracks_per_key_support() -> None:
    state = LightingState(mode="static", brightness=80, per_key_rgb_supported=False)
    assert state.per_key_rgb_supported is False

