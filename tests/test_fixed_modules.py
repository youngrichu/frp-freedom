"""Tests for bug fixes in core modules."""

from unittest.mock import Mock

from src.ai.ai_engine import AIEngine
from src.bypass.hardware_exploits import HardwareExploitManager
from src.bypass.interface_exploits import InterfaceExploitManager
from src.bypass.types import BypassResult
from src.core.config import Config
from src.core.device_manager import DeviceInfo


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


def test_hardware_exploit_manager_chipset_exploits_initialized():
    """chipset_exploits must be available after construction."""
    config = Config()
    device_manager = Mock()
    manager = HardwareExploitManager(config, device_manager)

    assert hasattr(manager, "chipset_exploits")
    assert "qualcomm" in manager.chipset_exploits
    assert manager.get_supported_chipsets() == list(manager.chipset_exploits.keys())
    assert (
        manager.get_chipset_exploits("qualcomm") == manager.chipset_exploits["qualcomm"]
    )


def test_ai_engine_tracks_total_duration():
    """Performance updates must store duration under total_duration and report correct averages."""
    config = Config()
    ai = AIEngine(config)
    device = make_device()

    ai.update_method_performance("method_a", device, BypassResult.SUCCESS, 10.0)
    ai.update_method_performance("method_a", device, BypassResult.SUCCESS, 20.0)
    ai.update_method_performance("method_b", device, BypassResult.FAILED, 5.0)

    stats = ai.method_performance["method_a"]
    assert stats["total_duration"] == 30.0
    assert stats["success_rate"] == 1.0

    assert ai.get_average_execution_time() == 35.0 / 3.0
    fastest = ai.get_fastest_methods()
    assert fastest[0] == "method_b"
    assert "method_a" in fastest


def test_interface_simulate_ui_interaction_returns_true_on_success():
    """simulate_ui_interaction should return True when all interactions succeed."""
    config = Config()
    device_manager = Mock()
    device_manager.execute_adb_command = Mock(return_value=(True, ""))
    manager = InterfaceExploitManager(config, device_manager)
    device = make_device()

    interactions = [
        {"type": "tap", "coordinates": (100, 200)},
        {"type": "key", "keycode": "KEYCODE_HOME"},
    ]

    result = manager.simulate_ui_interaction(device, interactions)
    assert result is True


def test_bypass_manager_ai_analysis_keys():
    """BypassManager.get_ai_device_analysis must return ai_analysis with all expected keys."""
    from src.bypass.bypass_manager import BypassManager

    config = Config()
    device_manager = Mock()
    manager = BypassManager(config, device_manager)
    device = make_device(brand="Samsung", security_patch="2024-01-01")

    analysis = manager.get_ai_device_analysis(device)

    assert "device_info" in analysis
    assert "ai_analysis" in analysis
    ai = analysis["ai_analysis"]
    assert "complexity_score" in ai
    assert "vulnerability_score" in ai
    assert "frp_complexity" in ai
    assert "recommended_methods" in ai
    assert "success_probabilities" in ai
    assert "security_assessment" in ai
    assert "bypass_strategy" in ai
