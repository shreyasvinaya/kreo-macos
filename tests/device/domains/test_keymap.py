from kreo_kontrol.device.domains.keymap import KeyAction, KeyAssignment


def test_key_assignment_supports_fn_action() -> None:
    assignment = KeyAssignment(
        ui_key="right_opt",
        logical_id="RALT",
        svg_id="key_RALT",
        label="Command",
        protocol_pos=220,
        base_action=KeyAction(
            action_id="basic:right_opt",
            label="Command",
            category="Modifiers",
            raw_value=0x00400000,
        ),
        fn_action=KeyAction(
            action_id="media_play_pause",
            label="Play / Pause",
            category="Media",
            raw_value=0x020000CD,
        ),
    )
    assert assignment.fn_action.action_id == "media_play_pause"
