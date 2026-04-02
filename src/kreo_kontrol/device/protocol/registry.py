from __future__ import annotations

from kreo_kontrol.device.protocol.models import (
    CommandConfidence,
    CommandDefinition,
    ProtocolDomain,
    VerificationStrategy,
)

COMMANDS: tuple[CommandDefinition, ...] = (
    CommandDefinition(
        name="profiles.read_slots",
        domain=ProtocolDomain.PROFILES,
        report_id=5,
        request_prefix=b"\x05\x10",
        confidence=CommandConfidence.CONFIRMED,
        verification=VerificationStrategy.NONE,
    ),
    CommandDefinition(
        name="profiles.activate",
        domain=ProtocolDomain.PROFILES,
        report_id=5,
        request_prefix=b"\x05\x11",
        confidence=CommandConfidence.INFERRED,
        verification=VerificationStrategy.FULL_DOMAIN_REREAD,
    ),
    CommandDefinition(
        name="keymap.read",
        domain=ProtocolDomain.KEYMAP,
        report_id=5,
        request_prefix=b"\x05\x20",
        confidence=CommandConfidence.INFERRED,
        verification=VerificationStrategy.NONE,
    ),
    CommandDefinition(
        name="keymap.apply",
        domain=ProtocolDomain.KEYMAP,
        report_id=5,
        request_prefix=b"\x05\x21",
        confidence=CommandConfidence.INFERRED,
        verification=VerificationStrategy.TARGETED_REREAD,
    ),
    CommandDefinition(
        name="lighting.read",
        domain=ProtocolDomain.LIGHTING,
        report_id=5,
        request_prefix=b"\x05\x30",
        confidence=CommandConfidence.INFERRED,
        verification=VerificationStrategy.NONE,
    ),
    CommandDefinition(
        name="lighting.apply",
        domain=ProtocolDomain.LIGHTING,
        report_id=5,
        request_prefix=b"\x05\x31",
        confidence=CommandConfidence.INFERRED,
        verification=VerificationStrategy.FULL_DOMAIN_REREAD,
    ),
    CommandDefinition(
        name="macros.read",
        domain=ProtocolDomain.MACROS,
        report_id=5,
        request_prefix=b"\x05\x40",
        confidence=CommandConfidence.INFERRED,
        verification=VerificationStrategy.NONE,
    ),
    CommandDefinition(
        name="macros.apply",
        domain=ProtocolDomain.MACROS,
        report_id=5,
        request_prefix=b"\x05\x41",
        confidence=CommandConfidence.INFERRED,
        verification=VerificationStrategy.FULL_DOMAIN_REREAD,
    ),
)


def _validate_commands(commands: tuple[CommandDefinition, ...]) -> None:
    command_names: set[str] = set()
    request_signatures: set[tuple[int, bytes]] = set()

    for command in commands:
        if command.name in command_names:
            raise ValueError(f"duplicate command name: {command.name}")
        command_names.add(command.name)

        signature = (command.report_id, command.request_prefix)
        if signature in request_signatures:
            raise ValueError(
                "duplicate command request prefix: "
                f"{command.report_id!r}, {command.request_prefix!r}"
            )
        request_signatures.add(signature)


_validate_commands(COMMANDS)


def list_commands_for_domain(domain: ProtocolDomain) -> list[CommandDefinition]:
    return [command for command in COMMANDS if command.domain == domain]


def get_command(name: str) -> CommandDefinition:
    for command in COMMANDS:
        if command.name == name:
            return command
    raise KeyError(name)
