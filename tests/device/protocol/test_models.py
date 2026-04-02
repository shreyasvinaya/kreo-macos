from kreo_kontrol.device.protocol.models import (
    CommandConfidence,
    CommandDefinition,
    ProtocolDomain,
    VerificationStrategy,
)


def test_command_definition_tracks_confidence_and_verification() -> None:
    definition = CommandDefinition(
        name="profiles.read_slots",
        domain=ProtocolDomain.PROFILES,
        report_id=5,
        request_prefix=b"\x05\x10",
        confidence=CommandConfidence.INFERRED,
        verification=VerificationStrategy.FULL_DOMAIN_REREAD,
    )

    assert definition.name == "profiles.read_slots"
    assert definition.domain is ProtocolDomain.PROFILES
    assert definition.report_id == 5
    assert definition.request_prefix == b"\x05\x10"
    assert definition.confidence is CommandConfidence.INFERRED
    assert definition.verification is VerificationStrategy.FULL_DOMAIN_REREAD
