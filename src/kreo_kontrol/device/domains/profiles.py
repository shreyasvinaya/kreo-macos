from __future__ import annotations

from typing import TypedDict

from pydantic import BaseModel


class ProfilesState(BaseModel):
    active_profile: int
    available_profiles: list[int]


class ProfilesPayload(TypedDict):
    supported: bool
    active_profile: int | None
    available_profiles: list[int]
    reason: str | None


def parse_profiles_state(response: bytes) -> ProfilesState:
    active_profile = int(response[2])
    profile_count = int(response[3])
    return ProfilesState(
        active_profile=active_profile,
        available_profiles=list(range(1, profile_count + 1)),
    )


def unsupported_profiles_payload(reason: str) -> ProfilesPayload:
    return {
        "supported": False,
        "active_profile": None,
        "available_profiles": [],
        "reason": reason,
    }


def supported_profiles_payload(state: ProfilesState) -> ProfilesPayload:
    return {
        "supported": True,
        "active_profile": state.active_profile,
        "available_profiles": state.available_profiles,
        "reason": None,
    }
