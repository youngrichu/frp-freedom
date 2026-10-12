from unittest.mock import Mock

from src.bypass.bypass_manager import BypassManager
from src.bypass.types import BypassMethod
from src.core import device_manager as device_manager_module
from src.core.device_manager import DeviceInfo
from src.gui.device_selection import DeviceSelectionFrame


class FakeConfig:
    def __init__(self, hardware=False):
        self.hardware = hardware

    def get(self, key, default=None):
        values = {
            "bypass_methods.adb_exploits": True,
            "bypass_methods.bootloader_exploits": True,
            "bypass_methods.interface_exploits": True,
            "bypass_methods.hardware_methods": self.hardware,
        }
        return values.get(key, default)


def make_device(connection_type="download", android_version="Unknown"):
    return DeviceInfo(
        serial="test-device",
        model="Test Device",
        manufacturer="Samsung",
        android_version=android_version,
        sdk_version="unknown",
        bootloader_version="unknown",
        frp_status="unknown",
        connection_type=connection_type,
        chipset="unknown",
        brand="Samsung",
    )


def describe_connection_capabilities(*args, **kwargs):
    function = getattr(device_manager_module, "describe_connection_capabilities", None)
    assert function is not None, "describe_connection_capabilities is not implemented"
    return function(*args, **kwargs)


def evaluate_method_capability(manager, *args, **kwargs):
    function = getattr(manager, "evaluate_method_capability", None)
    assert function is not None, "evaluate_method_capability is not implemented"
    return function(*args, **kwargs)


def format_capability_summary(capabilities):
    function = getattr(DeviceSelectionFrame, "format_capability_summary", None)
    assert function is not None, "format_capability_summary is not implemented"
    return function(capabilities)


def make_method(name="download_mode_flash", category="hardware"):
    return BypassMethod(
        name=name,
        description="Test method",
        category=category,
        risk_level="low",
        success_rate=0.5,
        estimated_time=1,
        requirements=[],
        supported_devices=["Samsung"],
        android_versions=["11.0"],
    )


def test_connection_capabilities_describe_download_mode_without_guessing():
    capabilities = describe_connection_capabilities(
        make_device(), hardware_methods_enabled=False
    )

    assert capabilities["connection_type"] == "download"
    assert capabilities["adb_available"] is False
    assert capabilities["fastboot_available"] is False
    assert capabilities["download_mode"] is True
    assert capabilities["hardware_methods_enabled"] is False
    assert capabilities["ai_metadata_sufficient"] is False


def test_hardware_method_is_disabled_by_config_before_compatibility_claims():
    manager = BypassManager(FakeConfig(hardware=False), Mock())

    result = evaluate_method_capability(manager,
        make_device(), make_method()
    )

    assert result["available"] is False
    assert result["status"] == "disabled_by_config"


def test_download_mode_placeholder_is_not_reported_as_implemented():
    manager = BypassManager(FakeConfig(hardware=True), Mock())

    result = evaluate_method_capability(manager,
        make_device(), make_method()
    )

    assert result["available"] is False
    assert result["status"] == "not_implemented"


def test_download_mode_adb_method_reports_transport_requirement():
    manager = BypassManager(FakeConfig(hardware=False), Mock())

    result = evaluate_method_capability(manager,
        make_device(), make_method(name="adb_probe", category="adb")
    )

    assert result["available"] is False
    assert result["status"] == "requires_adb"


def test_download_mode_recommendations_do_not_invoke_ai_scoring():
    manager = BypassManager(FakeConfig(hardware=True), Mock())
    manager.ai_engine.analyze_device = Mock(
        side_effect=AssertionError("AI scoring must not run")
    )

    assert manager.get_recommended_methods(make_device()) == []
    manager.ai_engine.analyze_device.assert_not_called()


def test_unknown_metadata_adb_unauthorized_analysis_is_diagnostic_only():
    manager = BypassManager(FakeConfig(), Mock())
    manager.ai_engine.analyze_device = Mock(
        side_effect=AssertionError("AI scoring must not run")
    )

    analysis = manager.get_ai_device_analysis(
        make_device(connection_type="adb_unauthorized")
    )

    profile = analysis["ai_analysis"]
    assert profile["analysis_available"] is False
    assert profile["vulnerability_score"] is None
    assert profile["frp_complexity"] == "unknown"
    manager.ai_engine.analyze_device.assert_not_called()


def test_device_capability_summary_uses_canonical_connection_facts():
    capabilities = describe_connection_capabilities(
        make_device(), hardware_methods_enabled=False
    )

    text = format_capability_summary(capabilities)

    assert "ADB Transport: Not Available" in text
    assert "Fastboot Transport: Not Available" in text
    assert "Hardware Methods Configuration: Disabled" in text
    assert "Interface Access: Limited" in text
    assert "AI Analysis: Diagnostic only" in text
