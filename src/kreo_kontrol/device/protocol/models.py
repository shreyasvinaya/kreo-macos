from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ProtocolDomain(StrEnum):
    PROFILES = "profiles"
    KEYMAP = "keymap"
    LIGHTING = "lighting"
    MACROS = "macros"


class CommandConfidence(StrEnum):
    CONFIRMED = "confirmed"
    INFERRED = "inferred"
    EXPERIMENTAL = "experimental"


class VerificationStrategy(StrEnum):
    NONE = "none"
    FULL_DOMAIN_REREAD = "full_domain_reread"
    TARGETED_REREAD = "targeted_reread"


class CommandDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    domain: ProtocolDomain
    report_id: int = Field(ge=0, le=255)
    request_prefix: bytes = Field(min_length=1)
    confidence: CommandConfidence
    verification: VerificationStrategy
