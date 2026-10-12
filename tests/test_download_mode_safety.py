from unittest.mock import Mock

from src.core.device_manager import DeviceInfo
from src.bypass.bypass_manager import BypassManager
from src.bypass.hardware_exploits import HardwareExploitManager
from src.bypass.types import BypassMethod


def make_download_device():
    return DeviceInfo(
        serial="samsung-download",
        model="Samsung Download Mode",
        manufacturer="Samsung",
        android_version="Unknown",
        sdk_version="unknown",
        bootloader_version="unknown",
        frp_status="unknown",
        connection_type="download",
        chipset="unknown",
        brand="Samsung",
    )


def make_method(category):
    return BypassMethod(
        name=f"{category}_method", description="test", category=category,
        risk_level="low", success_rate=0.5, estimated_time=1,
        requirements=[], supported_devices=["Samsung"], android_versions=["11.0"],
    )

def test_download_mode_only_accepts_hardware_methods():
    manager = BypassManager.__new__(BypassManager)
    device = make_download_device()

    assert manager._is_method_compatible(make_method("hardware"), device)
    assert not manager._is_method_compatible(make_method("adb"), device)
    assert not manager._is_method_compatible(make_method("interface"), device)
    assert not manager._is_method_compatible(make_method("system"), device)


def test_download_mode_flash_placeholder_is_not_compatible():
    manager = BypassManager.__new__(BypassManager)
    device = make_download_device()
    method = make_method("hardware")
    method.name = "download_mode_flash"

    assert not manager._is_method_compatible(method, device)


def test_hardware_manager_initializes_chipset_exploits():
    manager = HardwareExploitManager(Mock(), Mock())

    assert "exynos" in manager.get_supported_chipsets()
    assert "heimdall_exploit" in manager.get_chipset_exploits("exynos")


def test_download_mode_chipset_detection_does_not_use_adb():
    device_manager = Mock()
    manager = HardwareExploitManager(Mock(), device_manager)

    assert manager._detect_chipset(make_download_device()) is None
    device_manager.execute_adb_command.assert_not_called()

def test_unimplemented_odin_execution_fails_closed():
    manager = HardwareExploitManager(Mock(), Mock())

    assert manager._execute_odin_bypass_commands(make_download_device()) is False


def test_unimplemented_odin_verification_fails_closed():
    manager = HardwareExploitManager(Mock(), Mock())

    assert manager._verify_odin_modifications(make_download_device()) is False


def test_edl_2025_entry_fails_when_transport_commands_fail():
    device_manager = Mock()
    device_manager.execute_adb_command.return_value = (False, "")
    manager = HardwareExploitManager(Mock(), device_manager)

    assert manager._enter_edl_mode_2025(make_download_device()) is False


def test_edl_partition_execution_fails_closed():
    manager = HardwareExploitManager(Mock(), Mock())
    assert manager._execute_edl_frp_commands(make_download_device()) is False


def test_edl_verification_fails_closed():
    manager = HardwareExploitManager(Mock(), Mock())
    assert manager._verify_edl_modifications(make_download_device()) is False


def test_mtk_execution_fails_closed():
    manager = HardwareExploitManager(Mock(), Mock())
    assert manager._execute_mtk_bypass_commands(make_download_device()) is False


def test_mtk_verification_fails_closed():
    manager = HardwareExploitManager(Mock(), Mock())
    assert manager._verify_mtk_modifications(make_download_device()) is False


def test_gpu_edl_helpers_fail_closed():
    manager = HardwareExploitManager(Mock(), Mock())
    device = make_download_device()

    assert manager._exploit_gpu_vulnerabilities(device) is False
    assert manager._patch_frp_via_gpu(device) is False
    assert manager._reboot_from_edl(device) is False


def test_mediatek_cve_helpers_fail_closed():
    manager = HardwareExploitManager(Mock(), Mock())
    device = make_download_device()

    assert manager._exploit_mediatek_cve_2024(device) is False
    assert manager._mediatek_frp_bypass(device) is False


def test_mali_helpers_fail_closed():
    manager = HardwareExploitManager(Mock(), Mock())
    device = make_download_device()

    assert manager._exploit_mali_gpu_vulnerabilities(device) is False
    assert manager._pixel_frp_bypass_via_mali(device) is False
