"""
Preflight state probing for Samsung devices.

Reads what the device actually reports about itself *before* any exploit
sequence runs, so that a device whose locks make ADB enablement impossible is
reported as such instead of being hammered with AT commands that cannot work.

Three independent locks matter, and each one closes a different route:

* ``PROTECTED_NO_TOK`` on the AT port -- the protected AT commands that switch
  the USB configuration need a Samsung-signed token. Without it, no amount of
  repeating the sequence helps: the first refusal is the final one.
* ``Secure Download: ENABLE`` on the download-mode screen -- Odin verifies the
  signature of every flashed image, so no unsigned partition can be written.
* ``KG Status: PRENORMAL`` / ``LOCKED`` -- Knox Guard, a remote carrier or
  enterprise lock that is not FRP at all. It is cleared by the party that
  enrolled the device, through Samsung's console, and survives any local
  bypass.
"""

import logging
import re
import subprocess
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import serial

SAMSUNG_VID = 0x04E8
MEDIATEK_VID = 0x0E8D

USB_MODES = {
    (SAMSUNG_VID, 0x6860): "mtp",
    (SAMSUNG_VID, 0x685D): "download",
    (SAMSUNG_VID, 0x685E): "download",
    (MEDIATEK_VID, 0x0003): "brom",
    (MEDIATEK_VID, 0x2000): "preloader",
}

# Fields shown on the download-mode screen. They cannot be read over USB -- the
# Odin protocol does not expose them -- so the operator has to read them off the
# phone. assess_download_mode_fields() interprets them once collected.
DOWNLOAD_MODE_FIELDS = (
    "CURRENT BINARY",
    "KG STATUS",
    "SECURE DOWNLOAD",
    "MTK SECURE BOOT",
    "OEM LOCK",
    "AP SWREV",
    "WARRANTY VOID",
)

# AT error fragments that mean "this firmware will not run protected commands".
_TOKEN_REFUSALS = ("PROTECTED_NO_TOK", "NOT_ALLOWED_CRO", "PACM")


@dataclass
class DeviceState:
    """What the device reports about itself before any exploit runs."""

    model: Optional[str] = None
    firmware: Optional[str] = None
    region: Optional[str] = None
    serial_number: Optional[str] = None
    usb_config: List[str] = field(default_factory=list)
    sim_lock: Optional[str] = None
    at_reachable: bool = False
    at_token_required: bool = False
    at_refusals: Dict[str, str] = field(default_factory=dict)
    usb_modes: List[str] = field(default_factory=list)

    @property
    def adb_in_usb_config(self) -> bool:
        """True when the USB configuration already exposes an ADB interface."""
        return any(entry.upper() == "ADB" for entry in self.usb_config)

    @property
    def in_download_mode(self) -> bool:
        return "download" in self.usb_modes

    @property
    def mediatek_port_exposed(self) -> bool:
        """True when a MediaTek BROM or preloader port is reachable.

        Samsung replaces the MediaTek download port with its own download mode,
        so this is normally False and mtkclient has nothing to talk to.
        """
        return any(mode in self.usb_modes for mode in ("brom", "preloader"))


@dataclass
class Verdict:
    """Whether to proceed, and what to tell the operator if not."""

    feasible: bool
    blocker: Optional[str]
    summary: str
    next_steps: List[str] = field(default_factory=list)


def detect_usb_modes() -> List[str]:
    """Return the Samsung/MediaTek USB modes currently enumerated."""
    logger = logging.getLogger(__name__)
    modes: List[str] = []
    try:
        import usb.core

        for dev in usb.core.find(find_all=True):
            mode = USB_MODES.get((dev.idVendor, dev.idProduct))
            if mode and mode not in modes:
                modes.append(mode)
    except Exception as exc:  # pyusb missing, or no permission to enumerate
        logger.debug(f"pyusb enumeration unavailable ({exc}); falling back to lsusb")
        try:
            out = subprocess.run(
                ["lsusb"], capture_output=True, text=True, timeout=10
            ).stdout
            for (vid, pid), mode in USB_MODES.items():
                if f"{vid:04x}:{pid:04x}" in out.lower() and mode not in modes:
                    modes.append(mode)
        except Exception as fallback_exc:
            logger.debug(f"lsusb fallback failed: {fallback_exc}")
    return modes


def _converse(ser: serial.Serial, command: str, deadline: float = 2.5) -> str:
    """Send one AT command and read the whole reply.

    Reads until the port has been idle for a moment rather than sampling
    ``in_waiting`` once, because Samsung's AT handler can take over a second to
    answer and a single immediate read usually returns nothing.
    """
    ser.reset_input_buffer()
    ser.write((command.strip() + "\r").encode())

    chunks: List[bytes] = []
    end = time.time() + deadline
    idle_since: Optional[float] = None
    while time.time() < end:
        waiting = ser.in_waiting
        if waiting:
            chunks.append(ser.read(waiting))
            idle_since = None
        elif chunks:
            if idle_since is None:
                idle_since = time.time()
            elif time.time() - idle_since > 0.35:
                break
        time.sleep(0.05)

    reply = b"".join(chunks).decode(errors="replace")
    # Drop the command echo, keep everything else including error lines.
    lines = [
        line.strip()
        for line in reply.splitlines()
        if line.strip() and line.strip() != command.strip()
    ]
    return "\n".join(lines)


def _condense(reply: str) -> str:
    """Flatten a multi-line AT reply for embedding in a sentence.

    A refusal arrives as the error line followed by a bare "OK" on its own
    line, which reads as a broken sentence inside an error dialog.
    """
    lines = [line.strip() for line in reply.splitlines() if line.strip()]
    while lines and lines[-1].upper() == "OK":
        lines.pop()
    return "; ".join(lines)


def _parse_devconinfo(reply: str, state: DeviceState) -> None:
    """Fill ``state`` from an ``AT+DEVCONINFO`` reply.

    The reply is a flat ``KEY(value);KEY(value);...`` string. Only the fields
    that affect the decision are read; the rest is left alone.
    """
    fields = dict(re.findall(r"([A-Z_]+)\(([^)]*)\)", reply))
    state.model = fields.get("MN") or state.model
    state.firmware = (fields.get("VER") or "").split("/")[0] or state.firmware
    state.region = fields.get("PRD") or state.region
    state.serial_number = fields.get("SN") or state.serial_number
    state.sim_lock = fields.get("LOCK") or state.sim_lock
    if "CON" in fields:
        state.usb_config = [p.strip() for p in fields["CON"].split(",") if p.strip()]


def probe(port_device: str, baudrate: int = 115200) -> DeviceState:
    """Probe a Samsung AT port and the USB bus for current device state.

    Sends two commands only: ``AT+DEVCONINFO`` to read the identity and USB
    configuration, and one protected command to learn whether this firmware
    will run protected commands at all. The protected probe is one of the
    commands the exploit sequences would send anyway, so probing is strictly
    less invasive than running a sequence blind.
    """
    logger = logging.getLogger(__name__)
    state = DeviceState(usb_modes=detect_usb_modes())

    ser = None
    try:
        ser = serial.Serial(port_device, baudrate, timeout=2)
        time.sleep(0.3)

        if "OK" not in _converse(ser, "AT").upper():
            logger.warning(f"{port_device} did not answer a bare AT")
            return state
        state.at_reachable = True

        _parse_devconinfo(_converse(ser, "AT+DEVCONINFO", deadline=3.5), state)

        probe_cmd = "AT+DEBUGLVC=0,5"
        reply = _converse(ser, probe_cmd)
        if any(token in reply.upper() for token in _TOKEN_REFUSALS):
            state.at_token_required = True
            state.at_refusals[probe_cmd] = reply
            logger.warning(f"Protected AT commands refused: {_condense(reply)}")
    except Exception as exc:
        logger.error(f"Could not probe {port_device}: {exc}")
    finally:
        if ser is not None and ser.is_open:
            ser.close()

    return state


def assess_download_mode_fields(fields: Dict[str, str]) -> Verdict:
    """Interpret fields read off the download-mode screen.

    Keys are matched case-insensitively and loosely, so "KG Status" and
    "KG STATE" both work.
    """
    norm = {k.strip().upper().replace("_", " "): (v or "").strip().upper()
            for k, v in fields.items()}

    def get(*names: str) -> str:
        for name in names:
            for key, value in norm.items():
                if name in key:
                    return value
        return ""

    kg = get("KG")
    if "PRENORMAL" in kg or "LOCK" in kg:
        return Verdict(
            feasible=False,
            blocker="knox_guard",
            summary=(
                f"Knox Guard is armed (KG Status: {kg}). This is a remote carrier "
                "or enterprise lock, not FRP. It survives any local bypass and "
                "re-locks the device on its next network contact."
            ),
            next_steps=[
                "Only the party that enrolled the device can release it, in "
                "Samsung's Knox Guard console.",
                "Take the IMEI and proof of purchase to the seller or carrier "
                "and ask them to release that IMEI.",
                "PRENORMAL is not yet LOCKED -- releasing it now returns the "
                "device to NORMAL, so acting early is worthwhile.",
                "Tools advertising 'KG removal' only defer the check-in; the "
                "lock returns.",
            ],
        )

    if "ENABLE" in get("SECURE DOWNLOAD"):
        return Verdict(
            feasible=False,
            blocker="secure_download",
            summary=(
                "Secure Download is enabled: Odin verifies the signature of "
                "every flashed image, so no unsigned partition can be written."
            ),
            next_steps=[
                "Reading the PIT table still works, but flashing does not.",
                "A signed stock firmware at or above the AP SWREV is the only "
                "thing this device will accept.",
            ],
        )

    return Verdict(
        feasible=True,
        blocker=None,
        summary="No hard lock found in the download-mode fields provided.",
    )


def verdict(state: DeviceState) -> Verdict:
    """Decide whether running an ADB-enable sequence can possibly work."""
    if state.adb_in_usb_config:
        return Verdict(
            feasible=False,
            blocker="already_enabled",
            summary=(
                f"The USB configuration already exposes ADB (CON={','.join(state.usb_config)}). "
                "No sequence is needed."
            ),
            next_steps=["Run 'adb devices' and accept the authorisation prompt on the phone."],
        )

    if not state.at_reachable:
        if state.in_download_mode:
            return Verdict(
                feasible=False,
                blocker="in_download_mode",
                summary=(
                    "The device is in download mode, which has no AT port. "
                    "Nothing can be sent until it boots back to Android."
                ),
                next_steps=[
                    "Read these fields off the download-mode screen and pass them "
                    f"to assess_download_mode_fields(): {', '.join(DOWNLOAD_MODE_FIELDS)}.",
                    "Note that one Odin session consumes the handshake: re-enter "
                    "download mode before each new command.",
                ],
            )
        return Verdict(
            feasible=False,
            blocker="no_at_port",
            summary="No Samsung AT port answered. The modem interface is not exposed.",
            next_steps=[
                "Check that the USB configuration includes AT (see AT+DEVCONINFO).",
                "On Linux, make sure ModemManager is not holding the port.",
            ],
        )

    if state.at_token_required:
        refusal = _condense(
            next(iter(state.at_refusals.values()), "protected command refused")
        )
        return Verdict(
            feasible=False,
            blocker="protected_no_token",
            summary=(
                f"This firmware refuses protected AT commands ({refusal}). They need a "
                "Samsung-signed token, so the USB configuration cannot be changed from "
                "here. Repeating the sequence cannot help -- the first refusal is final."
            ),
            next_steps=[
                "If the device also reports Knox Guard or Secure Download on its "
                "download-mode screen, no client-side route is open at all.",
                f"Device: {state.model or 'unknown'} / {state.firmware or 'unknown'}, "
                f"USB config CON={','.join(state.usb_config) or 'unknown'}.",
            ],
        )

    return Verdict(
        feasible=True,
        blocker=None,
        summary=(
            f"Protected AT commands are accepted on {state.model or 'this device'}; "
            "an ADB-enable sequence can be attempted."
        ),
    )
