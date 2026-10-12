from unittest.mock import Mock

from src.ai.ai_engine import DeviceProfile
from src.bypass.bypass_manager import BypassManager
from src.bypass.system_exploits import SystemExploitManager
from src.bypass.types import BypassMethod
from src.core.device_manager import DeviceInfo, describe_connection_capabilities
from src.gui.device_selection import DeviceSelectionFrame


class FakeConfig:
    def get(self, key, default=None):
        values = {
            "bypass_methods.adb_exploits": True,
            "bypass_methods.bootloader_exploits": True,
            "bypass_methods.interface_exploits": True,
            "bypass_methods.hardware_methods": False,
        }
        return values.get(key, default)


def make_device(connection_type="adb", android_version="11.0"):
    return DeviceInfo(
        serial="test-device",
        model="Test Device",
        manufacturer="Samsung",
        android_version=android_version,
        sdk_version="30",
        bootloader_version="unknown",
        frp_status="unknown",
        connection_type=connection_type,
        chipset="unknown",
        brand="Samsung",
    )


def make_method(name, category):
    return BypassMethod(
        name=name,
        description=name,
        category=category,
        risk_level="low",
        success_rate=0.5,
        estimated_time=1,
        requirements=[],
        supported_devices=["Samsung"],
        android_versions=["11.0"],
    )


def test_unauthorized_and_restricted_states_reject_adb_dependent_categories():
    manager = BypassManager(FakeConfig(), Mock())

    for connection_type in ("adb_unauthorized", "adb_restricted"):
        device = make_device(connection_type=connection_type, android_version="Unknown")
        for category in ("interface", "system"):
            result = manager.evaluate_method_capability(
                device, make_method(f"{category}_probe", category)
            )
            assert result["available"] is False
            assert result["status"] == "unsupported_connection_state"


def test_ai_analysis_filters_recommendations_through_capability_evaluation():
    manager = BypassManager(FakeConfig(), Mock())
    compatible = make_method("system_probe", "system")
    incompatible = make_method("hardware_probe", "hardware")
    manager.available_methods = [compatible, incompatible]
    manager.ai_engine.analyze_device = Mock(
        return_value=DeviceProfile(
            vulnerability_score=0.5,
            frp_complexity="medium",
            complexity_score=0.5,
            recommended_methods=["hardware_probe", "system_probe"],
            success_probability={"hardware_probe": 0.9, "system_probe": 0.7},
            security_assessment="test",
            bypass_strategy="test",
        )
    )

    analysis = manager.get_ai_device_analysis(make_device())
    profile = analysis["ai_analysis"]

    assert profile["recommended_methods"] == ["system_probe"]
    assert profile["success_probabilities"] == {"system_probe": 0.7}


def test_accounts_database_absence_marker_requires_root_shell():
    dm = Mock()
    dm.execute_adb_command.side_effect = [
        (False, "sqlite unavailable"),
        (True, "ABSENT"),
    ]
    manager = SystemExploitManager(Mock(), dm)

    assert manager._verify_database_changes(make_device()) is True

    marker_command = dm.execute_adb_command.call_args_list[1].args[1]
    assert marker_command[:3] == ["shell", "su", "-c"]
    assert "/data/system/users/0/accounts.db" in marker_command[3]


def test_persist_absence_marker_requires_root_shell():
    dm = Mock()
    dm.execute_adb_command.return_value = (True, "ABSENT")
    manager = SystemExploitManager(Mock(), dm)

    assert manager._verify_persist_changes(make_device()) is True

    marker_command = dm.execute_adb_command.call_args.args[1]
    assert marker_command[:3] == ["shell", "su", "-c"]
    assert "/persist/frp" in marker_command[3]


def test_capability_summary_labels_transport_facts_as_transport_not_methods():
    capabilities = describe_connection_capabilities(
        make_device(), hardware_methods_enabled=True
    )

    text = DeviceSelectionFrame.format_capability_summary(capabilities)

    assert "ADB Transport: Available" in text
    assert "Fastboot Transport: Not Available" in text
    assert "Hardware Methods Configuration: Enabled" in text
    assert "Interface Access: Available" in text
    assert "ADB Methods:" not in text
    assert "Fastboot Methods:" not in text
