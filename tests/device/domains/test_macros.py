from kreo_kontrol.device.domains.macros import MacroSlot


def test_macro_slot_tracks_bound_key() -> None:
    slot = MacroSlot(
        slot_id=1,
        name="Launchpad",
        execution_type="FIXED_COUNT",
        cycle_times=1,
        bound_ui_keys=["f13"],
        actions=[],
    )
    assert slot.bound_ui_keys == ["f13"]
