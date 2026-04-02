from kreo_kontrol.device.domains.macros import MacroSlot


def test_macro_slot_tracks_bound_key() -> None:
    slot = MacroSlot(slot_id=1, name="Launchpad", bound_key="f13")
    assert slot.bound_key == "f13"

