import pytest

from kreo_kontrol.device.domains.lighting import (
    LightingApplyRequest,
    LightingVerificationStatus,
)


def test_lighting_apply_request_requires_static_mode_for_color() -> None:
    with pytest.raises(ValueError):
        LightingApplyRequest(mode="wave", color="#00ffaa")


def test_lighting_apply_request_allows_static_color() -> None:
    request = LightingApplyRequest(mode="static", color="#00ffaa", brightness=40)

    assert request.color == "#00ffaa"
    assert request.brightness == 40
    assert LightingVerificationStatus.UNVERIFIED.value == "unverified"
