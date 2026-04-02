from kreo_kontrol.device.protocol.models import CommandConfidence, ProtocolDomain
from kreo_kontrol.device.protocol.registry import get_command, list_commands_for_domain


def test_list_commands_for_domain_returns_profiles_commands() -> None:
    commands = list_commands_for_domain(ProtocolDomain.PROFILES)
    assert [command.name for command in commands] == [
        "profiles.read_slots",
        "profiles.activate",
    ]


def test_get_command_marks_activate_as_inferred() -> None:
    command = get_command("profiles.activate")
    assert command.confidence is CommandConfidence.INFERRED
