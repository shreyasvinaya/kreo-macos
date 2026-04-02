from __future__ import annotations

from pydantic import BaseModel


class ProfilesState(BaseModel):
    active_profile: int
    available_profiles: list[int]


def parse_profiles_state(response: bytes) -> ProfilesState:
    active_profile = int(response[2])
    profile_count = int(response[3])
    return ProfilesState(
        active_profile=active_profile,
        available_profiles=list(range(1, profile_count + 1)),
    )

