from unittest.mock import Mock

from src.core.device_manager import DeviceInfo
from src.bypass.bypass_manager import BypassManager
from src.gui.method_selection import MethodSelectionFrame


class FakeConfig:
    def get(self, key, default=None):
        values = {
            "bypass_methods.adb_exploits": True,
            "bypass_methods.hardware_methods": False,
        }
        return values.get(key, default)


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


def test_download_mode_ai_analysis_is_diagnostic_not_vulnerability_scoring():
    manager = BypassManager(FakeConfig(), Mock())
    manager.ai_engine.analyze_device = Mock(
        side_effect=AssertionError("AI scoring must not run for Download Mode")
    )

    analysis = manager.get_ai_device_analysis(make_download_device())
    profile = analysis["ai_analysis"]

    assert profile["analysis_available"] is False
    assert profile["vulnerability_score"] is None
    assert profile["frp_complexity"] == "unknown"
    assert profile["recommended_methods"] == []
    assert "Download Mode" in profile["security_assessment"]
    assert "ADB is unavailable" in profile["bypass_strategy"]
    assert "No implemented compatible methods are currently enabled" in profile["bypass_strategy"]
    manager.ai_engine.analyze_device.assert_not_called()


def test_download_mode_analysis_text_does_not_show_numeric_vulnerability_score():
    manager = BypassManager(FakeConfig(), Mock())
    device = make_download_device()
    analysis = manager.get_ai_device_analysis(device)

    text = MethodSelectionFrame.format_ai_analysis_text(
        device, analysis, available_methods=[]
    )

    assert "VULNERABILITY SCORE: Unavailable" in text
    assert "Begin with ADB methods" not in text
    assert "No compatible methods are currently available." in text
    assert "Hardware methods are disabled." in text
    assert "Device detection is working correctly." in text


def test_empty_download_method_list_explains_why_it_is_empty():
    message = MethodSelectionFrame.format_method_list_status(
        make_download_device(), available_methods=[], hardware_methods_enabled=False
    )

    assert "No compatible methods are currently available." in message
    assert "Hardware methods are disabled." in message
    assert "Device detection is working correctly." in message
