"""Tests for the Samsung preflight probe.

The AT replies below are verbatim captures from a locked SM-A165F (Galaxy A16
4G, MediaTek Helio G99), which refuses protected AT commands and reports Knox
Guard on its download-mode screen.
"""

from unittest.mock import patch

from src.core import samsung_device_state as state
from src.core.samsung_device_state import DeviceState

DEVCONINFO_A165F = (
    "+DEVCONINFO: MN(SM-A165F);BASE(UNKNOWN);"
    "VER(A165FXXSBDZH6/A165FOJMBDZH6/A165FXXSBDZH3/A165FXXSBDZH6);"
    "MNC(02,);MCC(616,);PRD(XSG);AID(XSG);CC(AE);OMCCODE();SN(R58Y50DA8XW);"
    "UN(CE0225929CDD20BE3B7E);PN();CON(AT,MTP);LOCK(NONE);LIMIT(FALSE);"
    "SDP(RUNTIME)"
)

PROTECTED_REFUSAL = "+CME Error:PACM(AP),PROTECTED_NO_TOK\nOK"


def test_devconinfo_parsing_reads_identity_and_usb_config():
    device = DeviceState()
    state._parse_devconinfo(DEVCONINFO_A165F, device)

    assert device.model == "SM-A165F"
    assert device.firmware == "A165FXXSBDZH6"
    assert device.region == "XSG"
    assert device.serial_number == "R58Y50DA8XW"
    assert device.usb_config == ["AT", "MTP"]
    assert device.sim_lock == "NONE"


def test_usb_config_without_adb_is_reported_as_such():
    device = DeviceState()
    state._parse_devconinfo(DEVCONINFO_A165F, device)
    assert device.adb_in_usb_config is False


def test_usb_config_with_adb_is_detected():
    device = DeviceState()
    state._parse_devconinfo("+DEVCONINFO: MN(SM-X);CON(MTP,ADB);", device)
    assert device.adb_in_usb_config is True


def test_token_refusal_blocks_the_attempt():
    device = DeviceState(
        at_reachable=True,
        at_token_required=True,
        at_refusals={"AT+DEBUGLVC=0,5": PROTECTED_REFUSAL},
        model="SM-A165F",
        usb_config=["AT", "MTP"],
    )
    verdict = state.verdict(device)

    assert verdict.feasible is False
    assert verdict.blocker == "protected_no_token"
    assert "PROTECTED_NO_TOK" in verdict.summary


def test_already_enabled_is_not_an_error():
    device = DeviceState(at_reachable=True, usb_config=["MTP", "ADB"])
    verdict = state.verdict(device)

    assert verdict.feasible is False
    assert verdict.blocker == "already_enabled"


def test_download_mode_is_distinguished_from_a_missing_port():
    in_download = state.verdict(DeviceState(at_reachable=False, usb_modes=["download"]))
    assert in_download.blocker == "in_download_mode"

    nothing = state.verdict(DeviceState(at_reachable=False, usb_modes=[]))
    assert nothing.blocker == "no_at_port"


def test_accepted_protected_commands_allow_the_attempt():
    device = DeviceState(at_reachable=True, usb_config=["AT", "MTP"], model="SM-A165F")
    verdict = state.verdict(device)

    assert verdict.feasible is True
    assert verdict.blocker is None


def test_knox_guard_prenormal_outranks_everything_else():
    verdict = state.assess_download_mode_fields(
        {
            "Current Binary": "Samsung Official",
            "KG Status": "PRENORMAL (00)",
            "Secure Download": "ENABLE",
        }
    )

    assert verdict.feasible is False
    assert verdict.blocker == "knox_guard"
    assert any("Knox Guard console" in step for step in verdict.next_steps)


def test_knox_guard_field_name_variants_are_matched():
    for key in ("KG Status", "KG STATE", "kg_status"):
        verdict = state.assess_download_mode_fields({key: "LOCKED"})
        assert verdict.blocker == "knox_guard", key


def test_secure_download_blocks_flashing_when_knox_guard_is_clear():
    verdict = state.assess_download_mode_fields(
        {"KG Status": "NORMAL", "Secure Download": "ENABLE"}
    )

    assert verdict.feasible is False
    assert verdict.blocker == "secure_download"


def test_clear_download_mode_fields_are_not_flagged():
    verdict = state.assess_download_mode_fields(
        {"KG Status": "NORMAL", "Secure Download": "DISABLE", "OEM LOCK": "OFF"}
    )

    assert verdict.feasible is True
    assert verdict.blocker is None


def test_samsung_download_mode_is_not_mistaken_for_a_mediatek_port():
    """mtkclient needs 0e8d:xxxx; Samsung's own download mode is not that."""
    device = DeviceState(usb_modes=["download"])
    assert device.mediatek_port_exposed is False
    assert device.in_download_mode is True

    device = DeviceState(usb_modes=["brom"])
    assert device.mediatek_port_exposed is True


def test_detect_usb_modes_falls_back_to_lsusb_without_pyusb():
    lsusb_output = (
        "Bus 001 Device 008: ID 04e8:685d Samsung Electronics Co., Ltd "
        "GT-I9100 Phone [Galaxy S II] (Download mode)\n"
    )

    class FakeCompleted:
        stdout = lsusb_output

    with patch.dict("sys.modules", {"usb.core": None, "usb": None}):
        with patch("subprocess.run", return_value=FakeCompleted()):
            assert state.detect_usb_modes() == ["download"]


def test_refusals_are_flattened_for_display():
    """A refusal arrives as an error line plus a bare OK on the next line."""
    assert state._condense(PROTECTED_REFUSAL) == "+CME Error:PACM(AP),PROTECTED_NO_TOK"
    assert state._condense("+CME Error:A\n+CME Error:B\nOK") == "+CME Error:A; +CME Error:B"
    assert state._condense("OK") == ""


def test_token_refusal_summary_stays_on_one_line():
    device = DeviceState(
        at_reachable=True,
        at_token_required=True,
        at_refusals={"AT+DEBUGLVC=0,5": PROTECTED_REFUSAL},
    )
    assert "\n" not in state.verdict(device).summary
