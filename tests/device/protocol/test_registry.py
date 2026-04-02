import pytest

from kreo_kontrol.device.protocol.models import (
    CommandConfidence,
    CommandDefinition,
    ProtocolDomain,
    VerificationStrategy,
)
from kreo_kontrol.device.protocol.registry import (
    _validate_commands,
    get_command,
    list_commands_for_domain,
)


def test_list_commands_for_domain_returns_profiles_commands() -> None:
    commands = list_commands_for_domain(ProtocolDomain.PROFILES)
    assert [command.name for command in commands] == [
        "profiles.read_slots",
        "profiles.activate",
    ]


def test_get_command_marks_activate_as_inferred() -> None:
    command = get_command("profiles.activate")
    assert command.confidence is CommandConfidence.INFERRED


def test_validate_commands_rejects_duplicate_command_names() -> None:
    commands = (
        get_command("profiles.read_slots"),
        get_command("profiles.read_slots"),
    )

    with pytest.raises(ValueError, match="duplicate command name: profiles.read_slots"):
        _validate_commands(commands)


def test_validate_commands_rejects_duplicate_request_prefixes() -> None:
    commands = (
        CommandDefinition(
            name="profiles.read_slots",
            domain=ProtocolDomain.PROFILES,
            report_id=5,
            request_prefix=b"\x05\x10",
            confidence=CommandConfidence.CONFIRMED,
            verification=VerificationStrategy.NONE,
        ),
        CommandDefinition(
            name="profiles.alias_read_slots",
            domain=ProtocolDomain.PROFILES,
            report_id=5,
            request_prefix=b"\x05\x10",
            confidence=CommandConfidence.INFERRED,
            verification=VerificationStrategy.NONE,
        ),
    )

    with pytest.raises(
        ValueError,
        match=r"duplicate command request prefix: 5, b'\\x05\\x10'",
    ):
        _validate_commands(commands)
