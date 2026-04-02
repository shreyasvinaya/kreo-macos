from kreo_kontrol.device.domains.keymap import KeyAssignment


def test_key_assignment_supports_fn_action() -> None:
    assignment = KeyAssignment(
        position="ralt",
        action="right_option",
        fn_action="mission_control",
    )
    assert assignment.fn_action == "mission_control"

