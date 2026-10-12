import logging
from pathlib import Path
from unittest.mock import Mock

from src.core.device_manager import DeviceInfo, DeviceManager
from src.gui.device_selection import DeviceSelectionFrame


def make_device(**overrides):
    values = {
        "serial": "serial-001",
        "model": "Test Phone",
        "manufacturer": "Example",
        "android_version": "14",
        "sdk_version": "34",
        "bootloader_version": "unknown",
        "frp_status": "unknown",
        "connection_type": "adb",
    }
    values.update(overrides)
    return DeviceInfo(**values)


def test_adb_poll_reuses_details_for_an_unchanged_device(monkeypatch):
    manager = DeviceManager.__new__(DeviceManager)
    manager.logger = logging.getLogger(__name__)
    manager.adb_path = Path("adb")
    existing_device = make_device()
    manager.connected_devices = [existing_device]
    manager._get_adb_device_info = Mock(
        side_effect=AssertionError("poll should reuse cached device details")
    )
    monkeypatch.setattr(
        "src.core.device_manager.subprocess.run",
        Mock(return_value=Mock(
            returncode=0,
            stdout="List of devices attached\nserial-001 device model:Test_Phone\n",
            stderr="",
        )),
    )

    devices = manager._scan_adb_devices(refresh_details=False)

    assert devices == [existing_device]
    manager._get_adb_device_info.assert_not_called()


def test_device_list_poll_does_not_rebuild_unchanged_tree_rows():
    frame = DeviceSelectionFrame.__new__(DeviceSelectionFrame)
    frame.winfo_exists = Mock(return_value=True)
    frame.device_tree = Mock()
    frame.device_tree.winfo_exists.return_value = True
    frame.device_tree.item.return_value = (
        "serial-001",
        "Test Phone",
        "unknown",
        "14",
        "ADB",
        "unknown",
    )
    frame.status_label = Mock()
    frame.status_label.winfo_exists.return_value = True
    frame.device_items_by_key = {("adb", "serial-001"): "row-1"}
    frame.device_map = {"row-1": make_device()}

    refreshed_device = make_device()
    DeviceSelectionFrame.update_device_list(frame, [refreshed_device])

    frame.device_tree.insert.assert_not_called()
    frame.device_tree.delete.assert_not_called()
    frame.device_tree.item.assert_called_once()
    assert frame.device_map["row-1"] is refreshed_device
