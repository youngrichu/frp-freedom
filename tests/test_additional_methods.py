"""Tests for the fastboot erase, combination flash, and test-mode ADB methods."""

import io
import logging
import tarfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from src.bypass.frp_removal import (
    FRP_REMOVAL_COMMANDS,
    frp_indicators_cleared,
    run_frp_removal_commands,
)
from src.bypass.hardware_exploits import HardwareExploitManager
from src.bypass.interface_exploits import InterfaceExploitManager
from src.bypass.types import BypassResult
from src.core.config import Config
from src.core.device_manager import DeviceInfo, DeviceManager
from src.core.protocol_operations import FlashError


class DictConfig:
    def __init__(self, values=None):
        self.values = values or {}

    def get(self, key, default=None):
        return self.values.get(key, default)


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


def noop_progress(message, percent):
    pass


def make_tar(path: Path, members) -> Path:
    with tarfile.open(path, "w") as tar:
        for name, content in members:
            data = content.encode() if isinstance(content, str) else content
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return path


# ---------------------------------------------------------------------------
# Shared FRP removal helpers
# ---------------------------------------------------------------------------

def test_run_frp_removal_commands_counts_successes():
    device_manager = Mock()
    results = iter([(True, ""), (False, "denied"), (True, ""), (False, "denied")])
    device_manager.execute_adb_command = Mock(side_effect=lambda s, c: next(results))

    executed = run_frp_removal_commands(device_manager, "serial-001")

    assert executed == 2
    assert device_manager.execute_adb_command.call_count == len(FRP_REMOVAL_COMMANDS)


def test_frp_indicators_empty_pst_is_inconclusive():
    device_manager = Mock()
    device_manager.execute_adb_command = Mock(return_value=(True, ""))
    assert frp_indicators_cleared(device_manager, "serial-001") is False


def test_frp_indicators_ignore_settings_the_removal_just_wrote():
    device_manager = Mock()
    device_manager.execute_adb_command = Mock(return_value=(True, "1"))
    assert frp_indicators_cleared(device_manager, "serial-001") is False


def test_frp_indicators_cleared_when_no_google_account():
    device_manager = Mock()
    device_manager.execute_adb_command = Mock(return_value=(True, "Accounts: 0"))
    assert frp_indicators_cleared(device_manager, "serial-001") is True


def test_frp_indicators_not_cleared_when_google_account_remains():
    device_manager = Mock()
    device_manager.execute_adb_command = Mock(
        return_value=(True, "Accounts: 1\nAccount {name=x, type=com.google}")
    )
    assert frp_indicators_cleared(device_manager, "serial-001") is False


# ---------------------------------------------------------------------------
# DeviceManager.wait_for_connection
# ---------------------------------------------------------------------------

def test_wait_for_connection_returns_matching_device():
    manager = DeviceManager.__new__(DeviceManager)
    manager.logger = logging.getLogger("test")
    adb_device = make_device(connection_type="adb")
    manager.scan_devices = Mock(return_value=[make_device(connection_type="edl"), adb_device])

    assert manager.wait_for_connection(["adb"], timeout_seconds=5) is adb_device


def test_wait_for_connection_times_out_without_match():
    manager = DeviceManager.__new__(DeviceManager)
    manager.logger = logging.getLogger("test")
    manager.scan_devices = Mock(return_value=[])

    assert manager.wait_for_connection(["adb"], timeout_seconds=0) is None


def test_wait_for_connection_skips_excluded_serials():
    manager = DeviceManager.__new__(DeviceManager)
    manager.logger = logging.getLogger("test")
    other = make_device(serial="other-phone", connection_type="adb")
    target = make_device(serial="new-phone", connection_type="adb")
    manager.scan_devices = Mock(return_value=[other, target])

    found = manager.wait_for_connection(
        ["adb"], timeout_seconds=0, exclude_serials={"other-phone"}
    )

    assert found is target


# ---------------------------------------------------------------------------
# fastboot_frp_erase
# ---------------------------------------------------------------------------

def make_fastboot_manager(responses, fastboot_path="/usr/bin/fastboot"):
    """responses: function(args) -> (success, output)"""
    device_manager = Mock()
    device_manager.fastboot_path = fastboot_path
    calls = []
    def execute(serial, args):
        calls.append(args)
        return responses(args)
    device_manager.execute_fastboot_command = Mock(side_effect=execute)
    manager = HardwareExploitManager(Config(), device_manager, operations=Mock())
    return manager, calls


def test_fastboot_erase_fails_without_fastboot_binary():
    manager, _ = make_fastboot_manager(lambda a: (True, ""), fastboot_path=None)
    result = manager.fastboot_frp_erase_exploit(make_device(connection_type="fastboot"), noop_progress)
    assert result["result"] == BypassResult.FAILED


def test_fastboot_erase_fails_when_bootloader_locked():
    def responses(args):
        if args == ["getvar", "unlocked"]:
            return True, "unlocked: no"
        return True, ""
    manager, calls = make_fastboot_manager(responses)

    result = manager.fastboot_frp_erase_exploit(make_device(connection_type="fastboot"), noop_progress)

    assert result["result"] == BypassResult.FAILED
    assert "locked" in result["message"].lower()
    assert ["erase", "frp"] not in calls


def test_fastboot_erase_success_with_first_variant():
    manager, calls = make_fastboot_manager(lambda a: (True, ""))

    result = manager.fastboot_frp_erase_exploit(make_device(connection_type="fastboot"), noop_progress)

    assert result["result"] == BypassResult.SUCCESS
    assert ["erase", "frp"] in calls
    assert ["reboot"] in calls


def test_fastboot_erase_falls_back_to_oem_variant():
    def responses(args):
        if args == ["erase", "frp"]:
            return False, "not supported"
        return True, ""
    manager, calls = make_fastboot_manager(responses)

    result = manager.fastboot_frp_erase_exploit(make_device(connection_type="fastboot"), noop_progress)

    assert result["result"] == BypassResult.SUCCESS
    assert "oem frp-erase" in result["details"]["variant"]


def test_fastboot_erase_falls_back_to_flash_variant():
    def responses(args):
        if args[0] in ("erase", "oem"):
            return False, "not supported"
        return True, ""
    manager, calls = make_fastboot_manager(responses)

    result = manager.fastboot_frp_erase_exploit(make_device(connection_type="fastboot"), noop_progress)

    assert result["result"] == BypassResult.SUCCESS
    assert any(c[0] == "flash" for c in calls)


def test_fastboot_erase_fails_honestly_when_all_variants_fail():
    manager, _ = make_fastboot_manager(lambda a: (False, "remote: not allowed"))

    result = manager.fastboot_frp_erase_exploit(make_device(connection_type="fastboot"), noop_progress)

    assert result["result"] == BypassResult.FAILED
    assert "remote: not allowed" in result["message"]


# ---------------------------------------------------------------------------
# samsung_combination_flash
# ---------------------------------------------------------------------------

class FakeHeimdall:
    def __init__(self, available=True, detected=True, fail_partitions=()):
        self.available = available
        self.detected = detected
        self.fail_partitions = set(fail_partitions)
        self.flashed = []

    def discover(self):
        return SimpleNamespace(available=self.available)

    def detect_device(self):
        return self.detected

    def flash_partitions(self, images, reboot=False):
        for partition, image in images.items():
            self.flashed.append((partition, Path(image).name, reboot))
            if partition in self.fail_partitions:
                raise FlashError(f"flash of {partition} failed")


def make_combination_manager(heimdall, config, adb_device=None, adb_ok=True, existing_adb=()):
    device_manager = Mock()
    device_manager.scan_devices = Mock(return_value=list(existing_adb))
    device_manager.wait_for_connection = Mock(return_value=adb_device)
    device_manager.execute_adb_command = Mock(
        return_value=(adb_ok, "Accounts: 0" if adb_ok else "")
    )
    operations = SimpleNamespace(heimdall=heimdall)
    return HardwareExploitManager(config, device_manager, operations=operations)


def test_combination_flash_requires_configured_image():
    manager = make_combination_manager(FakeHeimdall(), Config())
    result = manager.samsung_combination_flash_exploit(make_device(), noop_progress)
    assert result["result"] == BypassResult.FAILED
    assert "combination_image" in result["message"]


def test_combination_flash_requires_existing_image(tmp_path):
    config = DictConfig({"tools.heimdall.combination_image": str(tmp_path / "missing.tar")})
    manager = make_combination_manager(FakeHeimdall(), config)
    result = manager.samsung_combination_flash_exploit(make_device(), noop_progress)
    assert result["result"] == BypassResult.FAILED
    assert "not found" in result["message"]


def test_combination_flash_requires_heimdall(tmp_path):
    archive = make_tar(tmp_path / "combo.tar", [("boot.img", b"boot")])
    config = DictConfig({"tools.heimdall.combination_image": str(archive)})
    manager = make_combination_manager(FakeHeimdall(available=False), config)

    result = manager.samsung_combination_flash_exploit(make_device(), noop_progress)

    assert result["result"] == BypassResult.FAILED
    assert "Heimdall" in result["message"]


def test_combination_flash_success(tmp_path):
    archive = make_tar(tmp_path / "combo.tar.md5", [
        ("boot.img", b"boot-bytes"),
        ("recovery.img", b"recovery-bytes"),
    ])
    config = DictConfig({
        "tools.heimdall.combination_image": str(archive),
        "bypass.combination_adb_timeout": 0,
    })
    heimdall = FakeHeimdall()
    adb_device = make_device(serial="adb-999", connection_type="adb")
    other = make_device(serial="other-phone", connection_type="adb")
    manager = make_combination_manager(
        heimdall, config, adb_device=adb_device, existing_adb=[other])

    result = manager.samsung_combination_flash_exploit(make_device(), noop_progress)

    assert result["result"] == BypassResult.SUCCESS
    assert manager.device_manager.wait_for_connection.call_args.kwargs["exclude_serials"] == {
        "other-phone"
    }
    assert result["details"]["reflash_stock_required"] is True
    flashed_partitions = [entry[0] for entry in heimdall.flashed]
    assert flashed_partitions == ["BOOT", "RECOVERY"]
    # One Heimdall session, rebooting at the end of it
    assert {entry[2] for entry in heimdall.flashed} == {True}


def test_combination_flash_fails_when_all_flashes_fail(tmp_path):
    archive = make_tar(tmp_path / "combo.tar", [("boot.img", b"boot")])
    config = DictConfig({"tools.heimdall.combination_image": str(archive)})
    heimdall = FakeHeimdall(fail_partitions={"BOOT"})
    manager = make_combination_manager(heimdall, config)

    result = manager.samsung_combination_flash_exploit(make_device(), noop_progress)

    assert result["result"] == BypassResult.FAILED
    assert "partially written" in result["message"]
    assert "BOOT" in result["details"]["partitions"]


def test_combination_flash_skips_modem_and_rejects_nested_archives(tmp_path):
    safe = make_tar(tmp_path / "combo.tar", [
        ("boot.img", b"boot"),
        ("modem.bin", b"radio"),
    ])
    config = DictConfig({"tools.heimdall.combination_image": str(safe)})
    heimdall = FakeHeimdall()
    manager = make_combination_manager(heimdall, config, adb_device=make_device(serial="new"))

    result = manager.samsung_combination_flash_exploit(make_device(), noop_progress)

    assert result["result"] == BypassResult.SUCCESS
    assert [entry[0] for entry in heimdall.flashed] == ["BOOT"]

    nested = make_tar(tmp_path / "nested.tar", [("AP.tar", b"not-an-image")])
    nested_config = DictConfig({"tools.heimdall.combination_image": str(nested)})
    nested_manager = make_combination_manager(FakeHeimdall(), nested_config)
    nested_result = nested_manager.samsung_combination_flash_exploit(make_device(), noop_progress)
    assert nested_result["result"] == BypassResult.FAILED
    assert "nested archive" in nested_result["message"]


def test_combination_flash_rejects_lz4_members(tmp_path):
    archive = make_tar(tmp_path / "combo.tar", [("boot.img.lz4", b"compressed")])
    config = DictConfig({"tools.heimdall.combination_image": str(archive)})
    manager = make_combination_manager(FakeHeimdall(), config)

    result = manager.samsung_combination_flash_exploit(make_device(), noop_progress)

    assert result["result"] == BypassResult.FAILED
    assert "lz4" in result["message"]


def test_combination_flash_partial_when_adb_never_appears(tmp_path):
    archive = make_tar(tmp_path / "combo.tar", [("boot.img", b"boot")])
    config = DictConfig({
        "tools.heimdall.combination_image": str(archive),
        "bypass.combination_adb_timeout": 0,
    })
    manager = make_combination_manager(FakeHeimdall(), config, adb_device=None)

    result = manager.samsung_combination_flash_exploit(make_device(), noop_progress)

    assert result["result"] == BypassResult.PARTIAL
    assert "ADB" in result["message"]


# ---------------------------------------------------------------------------
# samsung_test_mode_adb
# ---------------------------------------------------------------------------

class FakeEnabler:
    def __init__(self, ports=(), enable_ok=True):
        self._ports = list(ports)
        self._enable_ok = enable_ok

    def get_samsung_modem_ports(self):
        return self._ports

    def enable_adb(self, port, progress_callback=None):
        return self._enable_ok


def modem_port(device="/dev/ttyACM0"):
    return SimpleNamespace(device=device, description="Samsung Android Modem")


def make_test_mode_manager(monkeypatch, enabler, adb_device=None, adb_ok=True, existing_adb=()):
    monkeypatch.setattr(
        "src.bypass.interface_exploits.SamsungADBEnabler", lambda: enabler)
    device_manager = Mock()
    device_manager.scan_devices = Mock(return_value=list(existing_adb))
    device_manager.wait_for_connection = Mock(return_value=adb_device)
    device_manager.execute_adb_command = Mock(
        return_value=(adb_ok, "Accounts: 0" if adb_ok else "")
    )
    return InterfaceExploitManager(Config(), device_manager)


def test_test_mode_adb_fails_without_modem_port(monkeypatch):
    manager = make_test_mode_manager(monkeypatch, FakeEnabler(ports=[]))

    result = manager.samsung_test_mode_adb_exploit(make_device(), noop_progress)

    assert result["result"] == BypassResult.FAILED
    assert "modem port" in result["message"]


def test_test_mode_adb_uses_device_modem_port_when_set(monkeypatch):
    enabler = FakeEnabler(ports=[], enable_ok=False)
    manager = make_test_mode_manager(monkeypatch, enabler)

    result = manager.samsung_test_mode_adb_exploit(
        make_device(modem_port="/dev/ttyACM9"), noop_progress)

    # Port came from the device, so the enable sequence ran and failed there
    assert result["result"] == BypassResult.FAILED
    assert result["details"]["port"] == "/dev/ttyACM9"


def test_test_mode_adb_ignores_non_modem_samsung_ports(monkeypatch):
    enabler = FakeEnabler(ports=[SimpleNamespace(device="/dev/ttyACM0", description="Samsung MTP")])
    manager = make_test_mode_manager(monkeypatch, enabler)

    result = manager.samsung_test_mode_adb_exploit(make_device(), noop_progress)

    assert result["result"] == BypassResult.FAILED
    assert "modem" in result["message"].lower()


def test_test_mode_adb_fails_when_enable_sequence_fails(monkeypatch):
    enabler = FakeEnabler(ports=[modem_port()], enable_ok=False)
    manager = make_test_mode_manager(monkeypatch, enabler)

    result = manager.samsung_test_mode_adb_exploit(make_device(), noop_progress)

    assert result["result"] == BypassResult.FAILED
    assert "enable" in result["message"].lower()


def test_test_mode_adb_fails_when_adb_never_appears(monkeypatch):
    enabler = FakeEnabler(ports=[modem_port()])
    manager = make_test_mode_manager(monkeypatch, enabler, adb_device=None)

    result = manager.samsung_test_mode_adb_exploit(make_device(), noop_progress)

    assert result["result"] == BypassResult.FAILED
    assert "did not appear" in result["message"]


def test_test_mode_adb_success(monkeypatch):
    enabler = FakeEnabler(ports=[modem_port()])
    adb_device = make_device(serial="adb-123", connection_type="adb")
    other = make_device(serial="other-phone", connection_type="adb")
    manager = make_test_mode_manager(
        monkeypatch, enabler, adb_device=adb_device, existing_adb=[other])

    result = manager.samsung_test_mode_adb_exploit(make_device(), noop_progress)

    assert result["result"] == BypassResult.SUCCESS
    assert result["details"]["commands_executed"] == len(FRP_REMOVAL_COMMANDS)
    assert manager.device_manager.wait_for_connection.call_args.kwargs["exclude_serials"] == {
        "other-phone"
    }


def test_test_mode_adb_partial_when_indicators_remain(monkeypatch):
    enabler = FakeEnabler(ports=[modem_port()])
    adb_device = make_device(serial="adb-123", connection_type="adb")
    monkeypatch.setattr(
        "src.bypass.interface_exploits.SamsungADBEnabler", lambda: enabler)
    device_manager = Mock()
    device_manager.scan_devices = Mock(return_value=[])
    device_manager.wait_for_connection = Mock(return_value=adb_device)

    def adb_side_effect(serial, command):
        if "getprop" in command:
            return True, "0x0"
        if "get" in command:
            return True, "0"
        return True, ""

    device_manager.execute_adb_command = Mock(side_effect=adb_side_effect)
    manager = InterfaceExploitManager(Config(), device_manager)

    result = manager.samsung_test_mode_adb_exploit(make_device(), noop_progress)

    assert result["result"] == BypassResult.PARTIAL


def test_test_mode_adb_fails_when_no_removal_command_succeeds(monkeypatch):
    enabler = FakeEnabler(ports=[modem_port()])
    adb_device = make_device(serial="adb-123", connection_type="adb")
    manager = make_test_mode_manager(
        monkeypatch, enabler, adb_device=adb_device, adb_ok=False)

    result = manager.samsung_test_mode_adb_exploit(make_device(), noop_progress)

    assert result["result"] == BypassResult.FAILED
    assert "no removal command succeeded" in result["message"]


# ---------------------------------------------------------------------------
# Method registration
# ---------------------------------------------------------------------------

def make_bypass_manager():
    from src.bypass.bypass_manager import BypassManager

    config = DictConfig({"bypass_methods.hardware_methods": True})
    return BypassManager(config, Mock())


def test_new_methods_registered_in_bypass_manager():
    manager = make_bypass_manager()
    by_name = {m.name: m for m in manager.available_methods}

    assert by_name["fastboot_frp_erase"].category == "hardware"
    assert by_name["samsung_combination_flash"].category == "hardware"
    assert by_name["samsung_test_mode_adb"].category == "interface"


def test_new_methods_compatible_with_their_connection_types():
    manager = make_bypass_manager()
    by_name = {m.name: m for m in manager.available_methods}

    fastboot_device = make_device(connection_type="fastboot", manufacturer="Google")
    assert manager._is_method_compatible(by_name["fastboot_frp_erase"], fastboot_device)

    download_device = make_device(connection_type="download", manufacturer="Samsung")
    assert manager._is_method_compatible(by_name["samsung_combination_flash"], download_device)

    locked_device = make_device(connection_type="adb_unauthorized", manufacturer="Samsung")
    assert manager._is_method_compatible(by_name["samsung_test_mode_adb"], locked_device)
