"""Tests for ADB-enable outcome reporting.

The point of these is that a refused sequence must not be reported as a
success. Previously _execute_sequence returned True as soon as the serial port
opened, so a device that refused every command still produced a "sequence
completed" dialog telling the user to look for a USB debugging prompt that was
never going to appear.
"""

from unittest.mock import MagicMock, patch

from src.core import samsung_device_state as state
from src.core.samsung_adb_enabler import SamsungADBEnabler

REFUSAL = "+CME Error:PACM(AP),PROTECTED_NO_TOK\nOK"


def _enabler_with_replies(replies):
    """Build an enabler whose AT exchanges return canned replies in order."""
    enabler = SamsungADBEnabler()
    sent = []

    def fake_exchange(ser, command):
        sent.append(command)
        if callable(replies):
            return replies(command)
        return replies[min(len(sent) - 1, len(replies) - 1)]

    enabler.exchange = fake_exchange  # type: ignore[method-assign]
    return enabler, sent


def test_sequence_refused_for_want_of_a_token_is_a_failure():
    enabler, sent = _enabler_with_replies(lambda cmd: REFUSAL)

    with patch("serial.Serial", return_value=MagicMock()):
        result = enabler._execute_sequence(
            "/dev/ttyACM0", ["AT+DEBUGLVC=0,5", "AT+KSTRINGB=0,3"], "T", None
        )

    assert result is False


def test_token_refusal_stops_the_sequence_instead_of_grinding_through_it():
    """A token refusal is final, so the remaining commands are pointless."""
    long_sequence = ["AT+DEBUGLVC=0,5"] * 80
    enabler, sent = _enabler_with_replies(lambda cmd: REFUSAL)

    with patch("serial.Serial", return_value=MagicMock()):
        enabler._execute_sequence("/dev/ttyACM0", long_sequence, "T", None)

    # One ATD dial plus the single refused command, not all eighty.
    assert len(sent) == 2


def test_sequence_is_a_success_when_commands_are_accepted():
    enabler, _ = _enabler_with_replies(lambda cmd: "OK")

    with patch("serial.Serial", return_value=MagicMock()):
        result = enabler._execute_sequence("/dev/ttyACM0", ["AT+SWATD=0"], "T", None)

    assert result is True


def test_enable_adb_sends_nothing_when_the_firmware_refuses_protected_commands():
    enabler = SamsungADBEnabler()
    probed = state.DeviceState(
        at_reachable=True,
        at_token_required=True,
        at_refusals={"AT+DEBUGLVC=0,5": REFUSAL},
        usb_config=["AT", "MTP"],
    )

    with patch.object(state, "probe", return_value=probed):
        with patch.object(enabler, "_execute_sequence") as sequence:
            result = enabler.enable_adb("/dev/ttyACM0")

    assert result is False
    sequence.assert_not_called()
    assert enabler.last_verdict.blocker == "protected_no_token"


def test_enable_adb_reports_failure_when_adb_never_appears():
    enabler = SamsungADBEnabler()
    probed = state.DeviceState(at_reachable=True, usb_config=["AT", "MTP"])

    with patch.object(state, "probe", return_value=probed):
        with patch.object(enabler, "_execute_sequence", return_value=True):
            with patch.object(enabler, "_adb_devices", return_value=[]):
                with patch("time.sleep"):
                    result = enabler.enable_adb("/dev/ttyACM0")

    assert result is False
    assert enabler.last_verdict.blocker == "no_adb_after_sequences"


def test_enable_adb_succeeds_only_once_a_new_adb_device_shows_up():
    enabler = SamsungADBEnabler()
    probed = state.DeviceState(at_reachable=True, usb_config=["AT", "MTP"])
    seen = [[], [], ["R58Y50DA8XW"]]

    with patch.object(state, "probe", return_value=probed):
        with patch.object(enabler, "_execute_sequence", return_value=True):
            with patch.object(enabler, "_adb_devices", side_effect=lambda: seen.pop(0) if seen else ["R58Y50DA8XW"]):
                with patch("time.sleep"):
                    result = enabler.enable_adb("/dev/ttyACM0")

    assert result is True


def test_already_enabled_device_reports_success_without_a_sequence():
    enabler = SamsungADBEnabler()
    probed = state.DeviceState(at_reachable=True, usb_config=["MTP", "ADB"])

    with patch.object(state, "probe", return_value=probed):
        with patch.object(enabler, "_execute_sequence") as sequence:
            result = enabler.enable_adb("/dev/ttyACM0")

    assert result is True
    sequence.assert_not_called()


def test_verizon_preconfig_is_no_longer_sent():
    enabler, sent = _enabler_with_replies(lambda cmd: "OK")

    with patch("serial.Serial", return_value=MagicMock()):
        enabler._method_2024("/dev/ttyACM0", None)

    assert not any("PRECONFIG" in cmd for cmd in sent)
