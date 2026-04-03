from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class LightingVerificationStatus(StrEnum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    FAILED = "failed"


class LightingState(BaseModel):
    mode: str
    brightness: int
    per_key_rgb_supported: bool
    color: str | None = None
    verification_status: LightingVerificationStatus = LightingVerificationStatus.UNVERIFIED


class LightingApplyRequest(BaseModel):
    mode: str
    brightness: int | None = Field(default=None, ge=0, le=100)
    color: str | None = None

    @model_validator(mode="after")
    def validate_supported_combinations(self) -> LightingApplyRequest:
        if self.color is not None and self.mode != "static":
            raise ValueError("color writes are only supported for static mode")
        return self
