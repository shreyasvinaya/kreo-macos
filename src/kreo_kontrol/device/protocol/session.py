from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from kreo_kontrol.device.protocol.models import CommandDefinition
from kreo_kontrol.device.trace import HidTraceEntry


class Transport(Protocol):
    def exchange(self, payload: bytes) -> bytes:
        ...


@dataclass
class CommandResult:
    command_name: str
    payload: bytes
    response: bytes
    trace_entry: HidTraceEntry


class ProtocolSession:
    def __init__(self, transport: Transport) -> None:
        self._transport: Transport = transport

    def execute(self, command: CommandDefinition, payload_suffix: bytes) -> CommandResult:
        payload = command.request_prefix + payload_suffix
        response = self._transport.exchange(payload)
        trace_entry = HidTraceEntry(
            direction="write",
            report_id=command.report_id,
            payload_hex=payload.hex(" "),
            confidence=command.confidence.value,
            verification=command.verification.value,
            command_name=command.name,
        )
        return CommandResult(
            command_name=command.name,
            payload=payload,
            response=response,
            trace_entry=trace_entry,
        )
