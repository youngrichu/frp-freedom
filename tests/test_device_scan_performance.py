import logging
from pathlib import Path
import threading
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


def test_scan_keeps_published_modem_port_until_matching_finishes():
    device = make_device(modem_port="COM7")
    manager = DeviceManager.__new__(DeviceManager)
    manager.logger = logging.getLogger(__name__)
    manager._scan_lock = threading.Lock()
    manager.connected_devices = [device]
    manager._scan_adb_devices = Mock(return_value=[device])
    manager._scan_fastboot_devices = Mock(return_value=[])
    manager._scan_download_mode_devices = Mock(return_value=[])

    observed = {}

    def scan_modems(candidates):
        observed["published_during"] = list(manager.connected_devices)
        observed["published_port"] = manager.connected_devices[0].modem_port
        observed["candidate"] = candidates[0]
        observed["candidate_port"] = candidates[0].modem_port
        candidates[0].modem_port = "COM9"
        return []

    manager.scan_samsung_modems = scan_modems

    result = manager.scan_devices(refresh_details=False)

    assert observed["published_during"] == [device]
    assert observed["published_port"] == "COM7"
    assert observed["candidate"] is not device
    assert observed["candidate_port"] == ""
    assert device.modem_port == "COM7"
    assert result[0].modem_port == "COM9"
    assert manager.connected_devices == result


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
    old_device = make_device(model="Old Model")
    frame.device_map = {"row-1": old_device}
    frame.selected_device = old_device
    frame.device_tree.selection.return_value = ("row-1",)
    frame.update_device_details = Mock()

    refreshed_device = make_device()
    DeviceSelectionFrame.update_device_list(frame, [refreshed_device])

    frame.device_tree.insert.assert_not_called()
    frame.device_tree.delete.assert_not_called()
    assert frame.device_tree.item.call_count == 1
    assert frame.device_map["row-1"] is refreshed_device
    assert frame.selected_device is refreshed_device
    frame.update_device_details.assert_called_once_with(refreshed_device)


def test_unchanged_device_replacement_does_not_redraw_details():
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
    frame.device_tree.selection.return_value = ("row-1",)
    frame.status_label = Mock()
    frame.status_label.winfo_exists.return_value = True
    frame.device_items_by_key = {("adb", "serial-001"): "row-1"}
    current_device = make_device(modem_port="COM7")
    frame.device_map = {"row-1": current_device}
    frame.selected_device = current_device
    frame.update_device_details = Mock()

    replacement = make_device(modem_port="COM7")
    DeviceSelectionFrame.update_device_list(frame, [replacement])

    assert frame.selected_device is replacement
    frame.update_device_details.assert_not_called()
    frame.device_tree.delete.assert_not_called()


def test_removing_selected_row_clears_selection_state():
    frame = DeviceSelectionFrame.__new__(DeviceSelectionFrame)
    frame.winfo_exists = Mock(return_value=True)
    frame.device_tree = Mock()
    frame.device_tree.winfo_exists.return_value = True
    frame.device_tree.selection.return_value = ("row-1",)
    frame.device_tree.insert.return_value = "row-2"
    frame.status_label = Mock()
    frame.status_label.winfo_exists.return_value = True
    frame.device_items_by_key = {("adb", "serial-001"): "row-1"}
    selected = make_device()
    frame.device_map = {"row-1": selected}
    frame.selected_device = selected
    frame.select_button = Mock()
    frame.info_button = Mock()
    frame.update_device_details = Mock()

    replacement = make_device(serial="serial-002")
    DeviceSelectionFrame.update_device_list(frame, [replacement])

    assert frame.selected_device is None
    assert "row-1" not in frame.device_map
    assert frame.device_map["row-2"] is replacement
    frame.device_tree.selection_remove.assert_called_once_with("row-1")
    frame.device_tree.delete.assert_called_once_with("row-1")
    frame.select_button.configure.assert_called_with(state="disabled")
    frame.info_button.configure.assert_called_with(state="disabled")
    frame.update_device_details.assert_called_once_with(None)


def test_removing_row_clears_selected_device_when_tree_selection_is_missing():
    frame = DeviceSelectionFrame.__new__(DeviceSelectionFrame)
    frame.winfo_exists = Mock(return_value=True)
    frame.device_tree = Mock()
    frame.device_tree.winfo_exists.return_value = True
    frame.device_tree.selection.return_value = ()
    frame.status_label = Mock()
    frame.status_label.winfo_exists.return_value = True
    frame.device_items_by_key = {("adb", "serial-001"): "row-1"}
    selected = make_device()
    frame.device_map = {"row-1": selected}
    frame.selected_device = selected
    frame.select_button = Mock()
    frame.info_button = Mock()
    frame.update_device_details = Mock()

    DeviceSelectionFrame.update_device_list(frame, [])

    assert frame.selected_device is None
    assert frame.device_map == {}
    frame.device_tree.selection_remove.assert_not_called()
    frame.device_tree.delete.assert_called_once_with("row-1")
    frame.select_button.configure.assert_called_with(state="disabled")
    frame.update_device_details.assert_called_once_with(None)
