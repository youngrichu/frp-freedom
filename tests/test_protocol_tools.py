"""Tests for external protocol tool discovery and safe execution."""

from pathlib import Path

from src.core.device_manager import DeviceManager
from src.core.protocol_tools import (
    BinaryResolver,
    ProtocolTool,
    ProtocolToolRegistry,
    USBDevice,
    USBModeProbe,
)


class DictConfig:
    def __init__(self, values=None):
        self.values = values or {}

    def get(self, key, default=None):
        return self.values.get(key, default)


class FakeTool(ProtocolTool):
    name = "fake"
    candidates = ("fake",)
    version_args = ("--version",)


def make_executable(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o111)
    return path


def test_binary_resolver_prefers_configured_path(tmp_path):
    configured = make_executable(tmp_path / "configured-tool", "exit 0")
    bundled = make_executable(tmp_path / "tools" / "fake", "exit 0")
    config = DictConfig({"tools.fake.path": str(configured)})
    resolver = BinaryResolver(config, project_root=tmp_path, environ={"PATH": ""})

    path, source = resolver.resolve("fake", ("fake",))

    assert path == configured.resolve()
    assert source == "configuration"
    assert path != bundled.resolve()


def test_binary_resolver_uses_environment_override(tmp_path):
    executable = make_executable(tmp_path / "env-tool", "exit 0")
    resolver = BinaryResolver(
        project_root=tmp_path,
        environ={"PATH": "", "FRP_FREEDOM_FAKE_PATH": str(executable)},
    )

    path, source = resolver.resolve("fake", ("fake",))

    assert path == executable.resolve()
    assert source == "environment"


def test_protocol_tool_returns_structured_success(tmp_path):
    make_executable(tmp_path / "tools" / "fake", 'echo "fake 1.2.3"')
    resolver = BinaryResolver(project_root=tmp_path, environ={"PATH": ""})
    tool = FakeTool(DictConfig(), resolver)

    info = tool.probe()
    result = tool.run(("--version",))

    assert info.available is True
    assert info.version == "fake 1.2.3"
    assert result.ok is True
    assert result.returncode == 0
    assert result.stdout.strip() == "fake 1.2.3"
    assert result.error is None


def test_protocol_tool_reports_missing_binary(tmp_path):
    resolver = BinaryResolver(project_root=tmp_path, environ={"PATH": ""})
    tool = FakeTool(DictConfig(), resolver)

    result = tool.run(("--version",))

    assert result.ok is False
    assert result.returncode is None
    assert "not found" in result.error


def test_protocol_tool_reports_timeout(tmp_path):
    make_executable(tmp_path / "tools" / "fake", "sleep 2")
    resolver = BinaryResolver(project_root=tmp_path, environ={"PATH": ""})
    tool = FakeTool(DictConfig(), resolver)

    result = tool.run((), timeout=0.01)

    assert result.ok is False
    assert result.timed_out is True
    assert "timed out" in result.error


def test_usb_mode_probe_classifies_known_boot_modes():
    assert USBModeProbe.classify(0x05C6, 0x9008) == "qualcomm_edl"
    assert USBModeProbe.classify(0x0E8D, 0x0003) == "mediatek_bootrom"
    assert USBModeProbe.classify(0x04E8, 0x685D) == "samsung_download"
    assert USBModeProbe.classify(0x18D1, 0x4EE7) is None


def test_registry_diagnostics_combines_tools_and_usb(tmp_path):
    class FakeUSBProbe:
        def scan(self):
            return [USBDevice(0x05C6, 0x9008, "qualcomm_edl", 1, 2)], None

    resolver = BinaryResolver(project_root=tmp_path, environ={"PATH": ""})
    registry = ProtocolToolRegistry(
        DictConfig(), resolver=resolver, usb_probe=FakeUSBProbe()
    )

    diagnostics = registry.diagnostics()

    assert set(diagnostics["tools"]) == {"heimdall", "edl", "mediatek"}
    assert diagnostics["tools"]["heimdall"]["available"] is False
    assert diagnostics["usb_devices"] == [
        {
            "vendor_id": "0x05c6",
            "product_id": "0x9008",
            "mode": "qualcomm_edl",
            "bus": 1,
            "address": 2,
        }
    ]
    assert diagnostics["usb_error"] is None


def test_device_manager_exposes_protocol_diagnostics():
    expected = {"tools": {}, "usb_devices": [], "usb_error": None}
    manager = DeviceManager.__new__(DeviceManager)

    class FakeRegistry:
        def diagnostics(self, probe_versions=False):
            assert probe_versions is True
            return expected

    manager.protocol_tools = FakeRegistry()

    assert manager.get_protocol_diagnostics(probe_versions=True) == expected
