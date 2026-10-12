from unittest.mock import Mock, patch

from src.core.device_manager import DeviceInfo, DeviceManager
from src.gui.main_window import FRPFreedomApp


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


def test_format_device_info_text_uses_current_deviceinfo_fields():
    device = make_device(
        api_level="34",
        security_patch="2025-01-05",
        build_id="UP1A.231005.007",
    )

    info_text = FRPFreedomApp.format_device_info_text(device)

    assert "Model: Galaxy S21" in info_text
    assert "Manufacturer: Samsung" in info_text
    assert "Build ID: UP1A.231005.007" in info_text
    assert "FRP Status: locked" in info_text
    assert "Build Number" not in info_text
    assert "\nStatus:" not in f"\n{info_text}"


def test_format_device_info_text_uses_unknown_for_blank_optional_fields():
    device = make_device(
        manufacturer="",
        api_level="",
        security_patch="",
        build_id="",
        frp_status="",
    )

    info_text = FRPFreedomApp.format_device_info_text(device)

    assert "Manufacturer: Unknown" in info_text
    assert "API Level: Unknown" in info_text
    assert "Security Patch: Unknown" in info_text
    assert "Build ID: Unknown" in info_text
    assert "FRP Status: Unknown" in info_text


def test_scan_devices_deduplicates_duplicate_serials():
    manager = DeviceManager.__new__(DeviceManager)

    adb_device = make_device(serial="serial-001", connection_type="adb", manufacturer="Samsung")
    duplicate_modem_device = DeviceInfo(
        serial="serial-001",
        model="Samsung Modem",
        manufacturer="Samsung",
        android_version="Unknown",
        sdk_version="Unknown",
        bootloader_version="Unknown",
        frp_status="Unknown",
        connection_type="modem",
        brand="Samsung",
        bootloader_status="Unknown",
        root_status="Unknown",
        device="COM12",
        modem_port="COM12",
    )

    deduplicated = manager._deduplicate_devices([adb_device, duplicate_modem_device])

    assert len(deduplicated) == 1
    assert deduplicated[0].connection_type == "adb"
    assert deduplicated[0].serial == "serial-001"


def test_refresh_devices_uses_scan_devices_and_updates_selected_device():
    original_device = make_device(serial="serial-001", model="Old Model")
    refreshed_device = make_device(serial="serial-001", model="New Model")
    scanned_devices = [refreshed_device]

    app = FRPFreedomApp.__new__(FRPFreedomApp)
    app.device_manager = Mock()
    app.device_manager.scan_devices.return_value = scanned_devices
    app.selected_device = original_device
    app.root = Mock()
    app.root.after.side_effect = lambda _delay, callback, *args: callback(*args)

    app.device_frame = Mock()
    app.device_frame.winfo_exists.return_value = True

    class ImmediateThread:
        def __init__(self, target, daemon):
            self._target = target

        def start(self):
            self._target()

    with patch("src.gui.main_window.threading.Thread", ImmediateThread), patch(
        "src.gui.main_window.messagebox.showinfo"
    ) as showinfo:
        app.refresh_devices()

    app.device_manager.scan_devices.assert_called_once_with()
    app.device_frame.update_device_list.assert_called_once_with(scanned_devices)
    assert app.selected_device is refreshed_device
    showinfo.assert_called_once_with("Refresh Complete", "Device list refreshed successfully.")
