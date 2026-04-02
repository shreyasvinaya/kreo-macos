from kreo_kontrol.device.protocol.models import VerificationStrategy
from kreo_kontrol.device.protocol.registry import get_command
from kreo_kontrol.device.protocol.session import ProtocolSession


class FakeTransport:
    def __init__(self) -> None:
        self.requests: list[bytes] = []

    def exchange(self, payload: bytes) -> bytes:
        self.requests.append(payload)
        return b"\x06\x10\x01\x00\x00\x00\x00\x00"


def test_execute_records_trace_with_confidence() -> None:
    session = ProtocolSession(FakeTransport())
    result = session.execute(get_command("profiles.read_slots"), b"\x00")

    assert result.command_name == "profiles.read_slots"
    assert result.trace_entry.confidence == "confirmed"
    assert result.trace_entry.verification == VerificationStrategy.NONE.value
