#!/usr/bin/env python3
"""Operational device-protocol adapters built on ``protocol_tools``.

The discovery layer in ``protocol_tools`` locates and probes external tools.
This module adds the partition-level operations the hardware bypass methods
need (partition read/write/erase, Heimdall flashing) with honest failure
reporting: when a tool or device is missing, operations fail explicitly
instead of simulating success.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .protocol_tools import (
    BinaryResolver,
    CommandResult,
    HeimdallTool,
    MediaTekTool,
    ProtocolTool,
    QualcommEDLTool,
    USBModeProbe,
)


class FlashError(RuntimeError):
    """A flash/erase operation could not be carried out."""


class DeviceNotDetectedError(RuntimeError):
    """No device present in the required low-level mode."""


def _serial_ports():
    try:
        import serial.tools.list_ports
        return list(serial.tools.list_ports.comports())
    except Exception:
        return []


def find_port_for_vid_pid(vendor_id: int, product_ids) -> str:
    """Best-effort serial port path for a USB VID/PID pair."""
    try:
        for port in _serial_ports():
            if port.vid == vendor_id and port.pid in product_ids:
                return port.device or ""
    except Exception:
        pass
    return ""


class HeimdallOperations(HeimdallTool):
    """Samsung download-mode operations: PIT reads and partition flashing."""

    def detect_device(self) -> bool:
        if not self.discover().available:
            return False
        result = self.detect()
        return result.ok and "detected" in (result.stdout + result.stderr).lower()

    def ensure_detected(self):
        if not self.detect_device():
            raise DeviceNotDetectedError(
                "No Samsung device in download mode. Enter download mode "
                "(usually Volume Down + Power/Home) and reconnect."
            )

    def print_pit(self) -> CommandResult:
        return self.run(("print-pit", "--no-reboot"), timeout=60)

    def flash_partition(self, partition: str, image, reboot: bool = False) -> CommandResult:
        image = Path(image)
        if not image.is_file():
            raise FlashError(f"Firmware image not found: {image}")
        args = ["flash", f"--{partition}", str(image)]
        if not reboot:
            args.append("--no-reboot")
        result = self.run(tuple(args), timeout=300)
        if not result.ok:
            raise FlashError(
                f"Heimdall flash of {partition} failed: "
                f"{result.error or result.stderr.strip()}"
            )
        return result


class EdlOperations(QualcommEDLTool):
    """Qualcomm EDL (Sahara/Firehose) partition operations."""

    EDL_VID = 0x05C6
    EDL_PIDS = {0x9008}

    def edl_ports(self) -> List:
        matches = []
        for port in _serial_ports():
            if port.vid == self.EDL_VID and port.pid in self.EDL_PIDS:
                matches.append(port)
                continue
            desc = (getattr(port, "description", "") or "").lower()
            if "qdloader" in desc or "9008" in desc:
                matches.append(port)
        return matches

    def detect_device(self) -> bool:
        return len(self.edl_ports()) > 0

    def ensure_detected(self):
        if not self.detect_device():
            raise DeviceNotDetectedError(
                "No Qualcomm EDL (9008) device detected. Enter EDL mode via "
                "test point, 'adb reboot edl', or 'fastboot oem edl'."
            )

    def is_available(self) -> bool:
        return self.discover().available

    def _loader(self) -> Optional[str]:
        if self.config is not None and hasattr(self.config, "get"):
            loader = self.config.get("tools.edl.loader")
            if loader:
                path = Path(loader)
                if not path.is_file():
                    raise FlashError(f"Firehose programmer not found: {path}")
                return str(path)
        return None

    def _run_edl(self, sub_args, timeout: Optional[float] = None) -> CommandResult:
        args = []
        loader = self._loader()
        if loader:
            args += ["--loader", loader]
        args += list(sub_args)
        return self.run(tuple(args), timeout=timeout)

    def print_gpt(self) -> CommandResult:
        return self._run_edl(["printgpt"], timeout=60)

    def read_partition(self, partition: str, output) -> CommandResult:
        return self._run_edl(["r", partition, str(output)], timeout=300)

    def write_partition(self, partition: str, image) -> CommandResult:
        image = Path(image)
        if not image.is_file():
            raise FlashError(f"Image not found: {image}")
        result = self._run_edl(["w", partition, str(image)], timeout=300)
        if not result.ok:
            raise FlashError(f"EDL write to {partition} failed: {result.error}")
        return result

    def erase_partition(self, partition: str) -> CommandResult:
        result = self._run_edl(["e", partition], timeout=120)
        if not result.ok:
            raise FlashError(f"EDL erase of {partition} failed: {result.error}")
        return result

    def reset(self) -> CommandResult:
        return self._run_edl(["reset"], timeout=30)


class MtkOperations(MediaTekTool):
    """MediaTek preloader/BROM operations via mtkclient.

    SP Flash Tool variants expose incompatible command lines, so partition
    operations deliberately resolve only the mtkclient CLI.
    """

    candidates = ("mtk", "mtkclient")

    MTK_VID = 0x0E8D
    MTK_PIDS = {0x0003, 0x2000, 0x2001, 0x3000, 0x6000}

    def mtk_ports(self) -> List:
        matches = []
        for port in _serial_ports():
            if port.vid == self.MTK_VID and (
                port.pid in self.MTK_PIDS or port.pid is None
            ):
                matches.append(port)
                continue
            desc = (getattr(port, "description", "") or "").lower()
            if "mediatek" in desc or "preloader" in desc:
                matches.append(port)
        return matches

    def detect_device(self) -> bool:
        return len(self.mtk_ports()) > 0

    def ensure_detected(self):
        if not self.detect_device():
            raise DeviceNotDetectedError(
                "No MediaTek preloader device detected. Power off the device "
                "and connect while holding the boot key (usually Volume Down)."
            )

    def is_available(self) -> bool:
        return self.discover().available

    def print_gpt(self) -> CommandResult:
        return self.run(("printgpt",), timeout=60)

    def read_partition(self, partition: str, output) -> CommandResult:
        return self.run(("r", partition, str(output)), timeout=300)

    def write_partition(self, partition: str, image) -> CommandResult:
        image = Path(image)
        if not image.is_file():
            raise FlashError(f"Image not found: {image}")
        result = self.run(("w", partition, str(image)), timeout=300)
        if not result.ok:
            raise FlashError(f"MTK write to {partition} failed: {result.error}")
        return result

    def erase_partition(self, partition: str) -> CommandResult:
        result = self.run(("e", partition), timeout=120)
        if not result.ok:
            raise FlashError(f"MTK erase of {partition} failed: {result.error}")
        return result

    def reset(self) -> CommandResult:
        return self.run(("reset",), timeout=30)


@dataclass
class SpecialModeDevice:
    """A device detected in a low-level (non-ADB) mode."""
    mode: str        # 'samsung_download' | 'edl' | 'mtk_preloader'
    protocol: str    # 'heimdall' | 'edl' | 'mtk'
    port: str
    detail: str


class DeviceProtocolOperations:
    """Facade bundling the operational adapters plus special-mode scanning."""

    def __init__(self, config=None, resolver: Optional[BinaryResolver] = None,
                 usb_probe: Optional[USBModeProbe] = None,
                 logger: Optional[logging.Logger] = None):
        self.config = config
        self.resolver = resolver or BinaryResolver(config)
        self.logger = logger or logging.getLogger(__name__)
        self.heimdall = HeimdallOperations(config, self.resolver)
        self.edl = EdlOperations(config, self.resolver)
        self.mtk = MtkOperations(config, self.resolver)
        self.usb_probe = usb_probe or USBModeProbe()

    def scan_special_modes(self) -> List[SpecialModeDevice]:
        """Scan all low-level modes; one protocol failing never hides others."""
        found: List[SpecialModeDevice] = []

        try:
            usb_devices, usb_error = self.usb_probe.scan()
            if usb_error:
                self.logger.debug(f"USB mode probe failed: {usb_error}")
            for device in usb_devices:
                if device.mode == "qualcomm_edl":
                    found.append(SpecialModeDevice(
                        mode="edl",
                        protocol="edl",
                        port=find_port_for_vid_pid(
                            EdlOperations.EDL_VID, EdlOperations.EDL_PIDS
                        ),
                        detail="Qualcomm EDL (9008) download interface",
                    ))
                elif device.mode == "mediatek_bootrom":
                    found.append(SpecialModeDevice(
                        mode="mtk_preloader",
                        protocol="mtk",
                        port=find_port_for_vid_pid(
                            MtkOperations.MTK_VID, MtkOperations.MTK_PIDS
                        ),
                        detail="MediaTek preloader/bootrom interface",
                    ))
        except Exception as exc:
            self.logger.debug(f"USB special-mode scan failed: {exc}")

        # Fallback: serial-port based detection when pyusb is unavailable
        modes_seen = {device.mode for device in found}
        if "edl" not in modes_seen and self.edl.detect_device():
            port = self.edl.edl_ports()[0]
            found.append(SpecialModeDevice(
                mode="edl",
                protocol="edl",
                port=getattr(port, "device", "") or "",
                detail="Qualcomm EDL (9008) download interface",
            ))
        if "mtk_preloader" not in modes_seen and self.mtk.detect_device():
            port = self.mtk.mtk_ports()[0]
            found.append(SpecialModeDevice(
                mode="mtk_preloader",
                protocol="mtk",
                port=getattr(port, "device", "") or "",
                detail="MediaTek preloader/bootrom interface",
            ))

        try:
            if self.heimdall.detect_device():
                found.append(SpecialModeDevice(
                    mode="samsung_download",
                    protocol="heimdall",
                    port="",
                    detail="Samsung download (Odin) mode",
                ))
        except Exception as exc:
            self.logger.debug(f"Heimdall detection failed: {exc}")

        return found
