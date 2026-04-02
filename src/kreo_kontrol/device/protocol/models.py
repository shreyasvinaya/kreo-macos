from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


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
    name: str
    domain: ProtocolDomain
    report_id: int
    request_prefix: bytes
    confidence: CommandConfidence
    verification: VerificationStrategy
