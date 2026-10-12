"""Tests for the operational protocol layer and hardware exploit integration."""

import logging
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.bypass.hardware_exploits import HardwareExploitManager
from src.bypass.types import BypassResult
from src.core.config import Config
from src.core.device_manager import DeviceInfo, DeviceManager
from src.core.protocol_operations import (
    DeviceNotDetectedError,
    DeviceProtocolOperations,
    EdlOperations,
    FlashError,
    HeimdallOperations,
    MtkOperations,
    SpecialModeDevice,
)
from src.core.protocol_tools import BinaryResolver, CommandResult, ToolInfo, USBDevice


class DictConfig:
    def __init__(self, values=None):
        self.values = values or {}

    def get(self, key, default=None):
        return self.values.get(key, default)


def make_resolver():
    return BinaryResolver(DictConfig(), environ={"PATH": ""})


def make_edl(config=None):
    return EdlOperations(config or DictConfig(), make_resolver())


def make_mtk(config=None):
    return MtkOperations(config or DictConfig(), make_resolver())


def make_device(**overrides):
    device = DeviceInfo(
        serial="serial-001",
        model="Galaxy S21",
        manufacturer="Samsung",
        android_version="14",
        sdk_version="34",
        bootloader_version="boot-v1",
        frp_status="locked",
        connection_type="adb",
    )
    for key, value in overrides.items():
        setattr(device, key, value)
    return device


def ok_result(stdout=""):
    return CommandResult(ok=True, command=("tool",), returncode=0, stdout=stdout)


def fail_result(error="boom"):
    return CommandResult(ok=False, command=("tool",), returncode=1, error=error)


# ---------------------------------------------------------------------------
# EDL operations
# ---------------------------------------------------------------------------

def test_edl_erase_partition_builds_expected_command(monkeypatch):
    edl = make_edl()
    calls = []
    monkeypatch.setattr(edl, "run", lambda args, timeout=None: calls.append(args) or ok_result())

    edl.erase_partition("frp")

    assert calls == [("e", "frp")]


def test_edl_erase_partition_raises_flash_error_on_failure(monkeypatch):
    edl = make_edl()
    monkeypatch.setattr(edl, "run", lambda args, timeout=None: fail_result())

    with pytest.raises(FlashError):
        edl.erase_partition("frp")


def test_edl_loader_prepended_when_configured(monkeypatch, tmp_path):
    loader = tmp_path / "prog_firehose.elf"
    loader.write_bytes(b"fake")
    edl = make_edl(DictConfig({"tools.edl.loader": str(loader)}))
    calls = []
    monkeypatch.setattr(edl, "run", lambda args, timeout=None: calls.append(args) or ok_result())

    edl.erase_partition("frp")

    assert calls == [("--loader", str(loader), "e", "frp")]


def test_edl_loader_missing_file_raises_flash_error():
    edl = make_edl(DictConfig({"tools.edl.loader": "/nonexistent/prog.elf"}))

    with pytest.raises(FlashError):
        edl.erase_partition("frp")


def test_edl_write_partition_requires_existing_image():
    edl = make_edl()

    with pytest.raises(FlashError):
        edl.write_partition("frp", "/nonexistent/image.bin")


def test_edl_detect_device_with_fake_serial_ports(monkeypatch):
    ports = [
        SimpleNamespace(vid=0x05C6, pid=0x9008, device="/dev/ttyUSB0", description="QDLoader 9008"),
        SimpleNamespace(vid=0x18D1, pid=0x4EE7, device="/dev/ttyUSB1", description="Android"),
    ]
    monkeypatch.setattr("src.core.protocol_operations._serial_ports", lambda: ports)

    edl = make_edl()

    assert edl.detect_device() is True
    assert edl.edl_ports()[0].device == "/dev/ttyUSB0"


def test_edl_detect_device_false_without_ports(monkeypatch):
    monkeypatch.setattr("src.core.protocol_operations._serial_ports", lambda: [])
    assert make_edl().detect_device() is False


# ---------------------------------------------------------------------------
# MTK operations
# ---------------------------------------------------------------------------

def test_mtk_candidates_narrowed_to_mtkclient():
    assert MtkOperations.candidates == ("mtk", "mtkclient")


def test_mtk_erase_partition_builds_expected_command(monkeypatch):
    mtk = make_mtk()
    calls = []
    monkeypatch.setattr(mtk, "run", lambda args, timeout=None: calls.append(args) or ok_result())

    mtk.erase_partition("frp")

    assert calls == [("e", "frp")]


def test_mtk_erase_partition_raises_flash_error_on_failure(monkeypatch):
    mtk = make_mtk()
    monkeypatch.setattr(mtk, "run", lambda args, timeout=None: fail_result())

    with pytest.raises(FlashError):
        mtk.erase_partition("frp")


def test_mtk_detect_device_with_fake_serial_ports(monkeypatch):
    ports = [
        SimpleNamespace(vid=0x0E8D, pid=0x0003, device="/dev/ttyACM0", description="MediaTek PreLoader"),
    ]
    monkeypatch.setattr("src.core.protocol_operations._serial_ports", lambda: ports)

    mtk = make_mtk()

    assert mtk.detect_device() is True
    assert mtk.mtk_ports()[0].device == "/dev/ttyACM0"


# ---------------------------------------------------------------------------
# Heimdall operations
# ---------------------------------------------------------------------------

def test_heimdall_flash_partition_builds_expected_command(monkeypatch, tmp_path):
    image = tmp_path / "boot.img"
    image.write_bytes(b"fake")
    heimdall = HeimdallOperations(DictConfig(), make_resolver())
    calls = []
    monkeypatch.setattr(heimdall, "run", lambda args, timeout=None: calls.append(args) or ok_result())

    heimdall.flash_partition("BOOT", image)

    assert calls == [("flash", "--BOOT", str(image), "--no-reboot")]


def test_heimdall_flash_partition_requires_existing_image():
    heimdall = HeimdallOperations(DictConfig(), make_resolver())

    with pytest.raises(FlashError):
        heimdall.flash_partition("BOOT", "/nonexistent/boot.img")


def test_heimdall_flash_partition_raises_flash_error_on_failure(monkeypatch, tmp_path):
    image = tmp_path / "boot.img"
    image.write_bytes(b"fake")
    heimdall = HeimdallOperations(DictConfig(), make_resolver())
    monkeypatch.setattr(heimdall, "run", lambda args, timeout=None: fail_result("flash failed"))

    with pytest.raises(FlashError):
        heimdall.flash_partition("BOOT", image)


def test_heimdall_detect_device_parses_output(monkeypatch):
    heimdall = HeimdallOperations(DictConfig(), make_resolver())
    monkeypatch.setattr(
        heimdall, "discover",
        lambda: ToolInfo(name="heimdall", available=True, path="/x", source="test"),
    )
    monkeypatch.setattr(heimdall, "detect", lambda: ok_result(stdout="Device detected"))

    assert heimdall.detect_device() is True


def test_heimdall_detect_device_false_when_binary_missing():
    heimdall = HeimdallOperations(DictConfig(), make_resolver())
    assert heimdall.detect_device() is False


# ---------------------------------------------------------------------------
# Special-mode scanning
# ---------------------------------------------------------------------------

class FakeUSBProbe:
    def __init__(self, devices=None, error=None, raises=False):
        self._devices = devices or []
        self._error = error
        self._raises = raises

    def scan(self):
        if self._raises:
            raise RuntimeError("usb exploded")
        return self._devices, self._error


def make_operations(usb_probe):
    return DeviceProtocolOperations(
        DictConfig(), resolver=make_resolver(), usb_probe=usb_probe
    )


def test_scan_special_modes_finds_edl_via_usb(monkeypatch):
    ports = [SimpleNamespace(vid=0x05C6, pid=0x9008, device="/dev/ttyUSB0", description="")]
    monkeypatch.setattr("src.core.protocol_operations._serial_ports", lambda: ports)
    ops = make_operations(FakeUSBProbe([USBDevice(0x05C6, 0x9008, "qualcomm_edl", 1, 2)]))

    found = ops.scan_special_modes()

    assert len(found) == 1
    assert found[0].mode == "edl"
    assert found[0].protocol == "edl"
    assert found[0].port == "/dev/ttyUSB0"


def test_scan_special_modes_finds_mtk_via_usb(monkeypatch):
    monkeypatch.setattr("src.core.protocol_operations._serial_ports", lambda: [])
    ops = make_operations(FakeUSBProbe([USBDevice(0x0E8D, 0x0003, "mediatek_bootrom", 1, 3)]))

    found = ops.scan_special_modes()

    assert len(found) == 1
    assert found[0].mode == "mtk_preloader"
    assert found[0].protocol == "mtk"


def test_scan_special_modes_serial_fallback_and_dedup(monkeypatch):
    ports = [SimpleNamespace(vid=0x05C6, pid=0x9008, device="/dev/ttyUSB0", description="")]
    monkeypatch.setattr("src.core.protocol_operations._serial_ports", lambda: ports)
    # USB probe reports nothing; serial fallback must find the EDL port.
    ops = make_operations(FakeUSBProbe([]))

    found = ops.scan_special_modes()

    assert [d.mode for d in found] == ["edl"]
    assert found[0].port == "/dev/ttyUSB0"


def test_scan_special_modes_usb_failure_does_not_hide_serial_detection(monkeypatch):
    ports = [SimpleNamespace(vid=0x05C6, pid=0x9008, device="/dev/ttyUSB0", description="")]
    monkeypatch.setattr("src.core.protocol_operations._serial_ports", lambda: ports)
    ops = make_operations(FakeUSBProbe(raises=True))

    found = ops.scan_special_modes()

    assert [d.mode for d in found] == ["edl"]


def test_scan_special_modes_empty_when_nothing_present(monkeypatch):
    monkeypatch.setattr("src.core.protocol_operations._serial_ports", lambda: [])
    ops = make_operations(FakeUSBProbe([]))

    assert ops.scan_special_modes() == []


# ---------------------------------------------------------------------------
# HardwareExploitManager integration with fake operations
# ---------------------------------------------------------------------------

class FakeEdl:
    def __init__(self, available=True, detected=True, gpt_text="boot_a\nsystem_a"):
        self.available = available
        self.detected = detected
        self.gpt_text = gpt_text
        self.erased = []
        self.reset_called = False

    def is_available(self):
        return self.available

    def detect_device(self):
        return self.detected

    def erase_partition(self, partition):
        self.erased.append(partition)

    def print_gpt(self):
        return ok_result(stdout=self.gpt_text)

    def reset(self):
        self.reset_called = True


class FakeMtk(FakeEdl):
    pass


class FakeOperations:
    def __init__(self, edl=None, mtk=None, heimdall=None):
        self.edl = edl
        self.mtk = mtk
        self.heimdall = heimdall


def noop_progress(message, percent):
    pass


def make_manager(operations, config=None):
    return HardwareExploitManager(config or Config(), Mock(), operations=operations)


def test_edl_2025_exploit_success_erases_frp_partition():
    edl = FakeEdl()
    manager = make_manager(FakeOperations(edl=edl))

    result = manager.qualcomm_edl_2025_exploit(make_device(), noop_progress)

    assert result["result"] == BypassResult.SUCCESS
    assert edl.erased == ["frp"]
    assert edl.reset_called is True


def test_edl_2025_exploit_partial_when_gpt_still_lists_frp():
    edl = FakeEdl(gpt_text="boot_a\nfrp\nsystem_a")
    manager = make_manager(FakeOperations(edl=edl))

    result = manager.qualcomm_edl_2025_exploit(make_device(), noop_progress)

    assert result["result"] == BypassResult.PARTIAL


def test_edl_2025_exploit_fails_honestly_without_edl_binary():
    edl = FakeEdl(available=False)
    manager = make_manager(FakeOperations(edl=edl))

    result = manager.qualcomm_edl_2025_exploit(make_device(), noop_progress)

    assert result["result"] == BypassResult.FAILED
    assert edl.erased == []


def test_edl_2025_exploit_fails_when_edl_entry_impossible():
    edl = FakeEdl(detected=False)
    device_manager = Mock()
    device_manager.execute_adb_command = Mock(return_value=(False, ""))
    device_manager.execute_fastboot_command = Mock(return_value=(False, ""))
    manager = HardwareExploitManager(Config(), device_manager, operations=FakeOperations(edl=edl))

    result = manager.qualcomm_edl_2025_exploit(make_device(), noop_progress)

    assert result["result"] == BypassResult.FAILED
    assert "EDL" in result["message"]


def test_mtk_2025_exploit_success_erases_frp_partition():
    mtk = FakeMtk()
    manager = make_manager(FakeOperations(mtk=mtk))

    result = manager.mediatek_cve_2025_exploit(make_device(), noop_progress)

    assert result["result"] == BypassResult.SUCCESS
    assert mtk.erased == ["frp"]


def test_mtk_2025_exploit_fails_when_device_not_detected():
    mtk = FakeMtk(detected=False)
    manager = make_manager(FakeOperations(mtk=mtk))

    result = manager.mediatek_cve_2025_exploit(make_device(), noop_progress)

    assert result["result"] == BypassResult.FAILED
    assert mtk.erased == []


def test_mali_gpu_exploit_fails_honestly_as_unimplemented():
    manager = make_manager(FakeOperations())

    result = manager.mali_gpu_pixel_exploit(make_device(), noop_progress)

    assert result["result"] == BypassResult.FAILED
    assert result["details"]["implemented"] is False


def test_odin_bypass_requires_configured_image():
    manager = make_manager(FakeOperations(heimdall=Mock()))

    assert manager._execute_odin_bypass_commands(make_device()) is False


def test_frp_partition_configurable():
    manager = make_manager(FakeOperations(), config=DictConfig({"bypass.frp_partition": "vendor_frp"}))
    assert manager._frp_partition() == "vendor_frp"


# ---------------------------------------------------------------------------
# DeviceManager special-mode scan
# ---------------------------------------------------------------------------

def test_device_manager_scan_download_mode_devices():
    manager = DeviceManager.__new__(DeviceManager)
    manager.logger = logging.getLogger("test")

    class FakeOps:
        def scan_special_modes(self):
            return [
                SpecialModeDevice(
                    mode="edl", protocol="edl", port="/dev/ttyUSB0",
                    detail="Qualcomm EDL (9008) download interface",
                ),
                SpecialModeDevice(
                    mode="samsung_download", protocol="heimdall", port="",
                    detail="Samsung download (Odin) mode",
                ),
            ]

    manager._protocol_operations = FakeOps()

    devices = manager._scan_download_mode_devices()

    assert len(devices) == 2
    edl_device = devices[0]
    assert edl_device.serial == "/dev/ttyUSB0"
    assert edl_device.connection_type == "edl"
    assert edl_device.chipset == "qualcomm"
    samsung_device = devices[1]
    assert samsung_device.serial == "samsung_download"
    assert samsung_device.connection_type == "download"
    assert samsung_device.manufacturer == "Samsung"


def test_device_manager_scan_survives_operations_failure():
    manager = DeviceManager.__new__(DeviceManager)
    manager.logger = logging.getLogger("test")

    class BrokenOps:
        def scan_special_modes(self):
            raise RuntimeError("scan exploded")

    manager._protocol_operations = BrokenOps()

    assert manager._scan_download_mode_devices() == []
