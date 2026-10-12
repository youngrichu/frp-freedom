#!/usr/bin/env python3
"""Safe wrappers for external Android device-protocol tools.

The adapters in this module only provide discovery, diagnostics, and read-only
probing. Destructive operations such as flashing or erasing partitions belong
in separately reviewed code.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class CommandResult:
    """Structured result returned by every external tool invocation."""

    ok: bool
    command: Tuple[str, ...]
    returncode: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None
    timed_out: bool = False
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class ToolInfo:
    """Discovery and health information for an external protocol tool."""

    name: str
    available: bool
    path: Optional[str] = None
    source: Optional[str] = None
    version: Optional[str] = None
    error: Optional[str] = None


@dataclass(frozen=True)
class USBDevice:
    """Minimal USB identity used for non-invasive mode classification."""

    vendor_id: int
    product_id: int
    mode: str
    bus: Optional[int] = None
    address: Optional[int] = None

    def to_dict(self) -> Dict[str, object]:
        data = asdict(self)
        data["vendor_id"] = f"0x{self.vendor_id:04x}"
        data["product_id"] = f"0x{self.product_id:04x}"
        return data


class BinaryResolver:
    """Resolve configured, bundled, and PATH-installed tool binaries."""

    def __init__(
        self,
        config=None,
        project_root: Optional[Path] = None,
        environ: Optional[Mapping[str, str]] = None,
    ):
        self.config = config
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self.environ = environ if environ is not None else os.environ

    def resolve(
        self, tool_name: str, candidates: Sequence[str]
    ) -> Tuple[Optional[Path], Optional[str]]:
        """Return the executable path and where it was discovered."""
        configured = self._configured_path(tool_name)
        if configured:
            path = self._valid_executable(Path(configured).expanduser())
            if path:
                return path, "configuration"

        env_name = f"FRP_FREEDOM_{tool_name.upper()}_PATH"
        if self.environ.get(env_name):
            path = self._valid_executable(Path(self.environ[env_name]).expanduser())
            if path:
                return path, "environment"

        tools_dir = self.project_root / "tools"
        for candidate in candidates:
            for filename in self._platform_names(candidate):
                path = self._valid_executable(tools_dir / filename)
                if path:
                    return path, "bundled"

        path_value = self.environ.get("PATH")
        for candidate in candidates:
            resolved = shutil.which(candidate, path=path_value)
            if resolved:
                return Path(resolved), "PATH"

        return None, None

    def _configured_path(self, tool_name: str) -> Optional[str]:
        if self.config is None or not hasattr(self.config, "get"):
            return None
        value = self.config.get(f"tools.{tool_name}.path")
        return str(value).strip() if value else None

    @staticmethod
    def _platform_names(candidate: str) -> Iterable[str]:
        yield candidate
        if os.name == "nt" and not candidate.lower().endswith(".exe"):
            yield f"{candidate}.exe"

    @staticmethod
    def _valid_executable(path: Path) -> Optional[Path]:
        try:
            if path.is_file() and (os.name == "nt" or os.access(path, os.X_OK)):
                return path.resolve()
        except OSError:
            pass
        return None


class ProtocolTool:
    """Base class for an external protocol tool with consistent failures."""

    name = "tool"
    candidates: Tuple[str, ...] = ()
    version_args: Tuple[str, ...] = ("--version",)

    def __init__(self, config=None, resolver: Optional[BinaryResolver] = None):
        self.config = config
        self.resolver = resolver or BinaryResolver(config)
        self.logger = logging.getLogger(f"{__name__}.{self.name}")

    def discover(self) -> ToolInfo:
        path, source = self.resolver.resolve(self.name, self.candidates)
        if path is None:
            return ToolInfo(
                name=self.name,
                available=False,
                error=f"{self.name} executable not found",
            )
        return ToolInfo(
            name=self.name,
            available=True,
            path=str(path),
            source=source,
        )

    def probe(self) -> ToolInfo:
        """Check that the binary launches and return its version text."""
        discovered = self.discover()
        if not discovered.available:
            return discovered

        result = self.run(self.version_args, timeout=10)
        if not result.ok:
            return ToolInfo(
                name=self.name,
                available=True,
                path=discovered.path,
                source=discovered.source,
                error=result.error or result.stderr.strip() or "probe failed",
            )

        version = self._first_output_line(result.stdout, result.stderr)
        return ToolInfo(
            name=self.name,
            available=True,
            path=discovered.path,
            source=discovered.source,
            version=version,
        )

    def run(
        self, arguments: Sequence[str], timeout: Optional[float] = None
    ) -> CommandResult:
        """Run a tool without a shell and return a structured result."""
        discovered = self.discover()
        if not discovered.available or not discovered.path:
            return CommandResult(
                ok=False,
                command=(self.name, *map(str, arguments)),
                error=discovered.error,
            )

        command = (discovered.path, *map(str, arguments))
        effective_timeout = timeout or self._default_timeout()
        started = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                check=False,
            )
            duration = time.monotonic() - started
            return CommandResult(
                ok=completed.returncode == 0,
                command=command,
                returncode=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                error=None if completed.returncode == 0 else "tool returned non-zero status",
                duration_seconds=duration,
            )
        except subprocess.TimeoutExpired as exc:
            return CommandResult(
                ok=False,
                command=command,
                stdout=self._decode_timeout_stream(exc.stdout),
                stderr=self._decode_timeout_stream(exc.stderr),
                error=f"command timed out after {effective_timeout:g} seconds",
                timed_out=True,
                duration_seconds=time.monotonic() - started,
            )
        except PermissionError:
            return CommandResult(
                ok=False,
                command=command,
                error=f"permission denied: {discovered.path}",
                duration_seconds=time.monotonic() - started,
            )
        except OSError as exc:
            self.logger.debug("Tool execution failed", exc_info=True)
            return CommandResult(
                ok=False,
                command=command,
                error=f"failed to execute {self.name}: {exc}",
                duration_seconds=time.monotonic() - started,
            )

    def _default_timeout(self) -> float:
        if self.config is not None and hasattr(self.config, "get"):
            configured = self.config.get("device.command_timeout", 30)
            try:
                return max(float(configured), 1.0)
            except (TypeError, ValueError):
                pass
        return 30.0

    @staticmethod
    def _decode_timeout_stream(value) -> str:
        if value is None:
            return ""
        return value.decode(errors="replace") if isinstance(value, bytes) else str(value)

    @staticmethod
    def _first_output_line(*values: str) -> Optional[str]:
        for value in values:
            for line in value.splitlines():
                if line.strip():
                    return line.strip()
        return None


class HeimdallTool(ProtocolTool):
    """Samsung Download Mode adapter backed by the open-source Heimdall CLI."""

    name = "heimdall"
    candidates = ("heimdall",)
    version_args = ("version",)

    def detect(self, timeout: float = 15) -> CommandResult:
        """Perform Heimdall's non-flashing device handshake."""
        return self.run(("detect", "--no-reboot"), timeout=timeout)


class QualcommEDLTool(ProtocolTool):
    """Adapter for the commonly used open-source ``edl`` command."""

    name = "edl"
    candidates = ("edl", "edl.py")
    version_args = ("--help",)


class MediaTekTool(ProtocolTool):
    """Discovery adapter for MediaTek CLI distributions.

    MediaTek packages expose incompatible command lines, so this adapter
    intentionally limits itself to launch diagnostics until a known variant is
    identified.
    """

    name = "mediatek"
    candidates = ("mtk", "flash_tool", "spflashtool", "SPFlashTool")
    version_args = ("--help",)


class USBModeProbe:
    """Classify known low-level USB modes without issuing device commands."""

    QUALCOMM_EDL = {(0x05C6, 0x9008)}
    MEDIATEK = {
        (0x0E8D, 0x0003),
        (0x0E8D, 0x2000),
        (0x0E8D, 0x2001),
    }
    # Samsung Odin/download mode. Classified from the descriptor alone so a
    # device scan never has to open a Heimdall session.
    SAMSUNG_DOWNLOAD = {(0x04E8, 0x685D)}

    def scan(self) -> Tuple[List[USBDevice], Optional[str]]:
        try:
            import usb.core

            devices = usb.core.find(find_all=True) or []
            detected = []
            for device in devices:
                mode = self.classify(device.idVendor, device.idProduct)
                if mode:
                    detected.append(
                        USBDevice(
                            vendor_id=device.idVendor,
                            product_id=device.idProduct,
                            mode=mode,
                            bus=getattr(device, "bus", None),
                            address=getattr(device, "address", None),
                        )
                    )
            return detected, None
        except Exception as exc:
            return [], f"USB scan failed: {exc}"

    @classmethod
    def classify(cls, vendor_id: int, product_id: int) -> Optional[str]:
        identity = (vendor_id, product_id)
        if identity in cls.QUALCOMM_EDL:
            return "qualcomm_edl"
        if identity in cls.MEDIATEK:
            return "mediatek_bootrom"
        if identity in cls.SAMSUNG_DOWNLOAD:
            return "samsung_download"
        return None


class ProtocolToolRegistry:
    """Central access point for protocol tools and capability diagnostics."""

    def __init__(
        self,
        config=None,
        resolver: Optional[BinaryResolver] = None,
        usb_probe: Optional[USBModeProbe] = None,
    ):
        resolver = resolver or BinaryResolver(config)
        self.tools: Dict[str, ProtocolTool] = {
            "heimdall": HeimdallTool(config, resolver),
            "edl": QualcommEDLTool(config, resolver),
            "mediatek": MediaTekTool(config, resolver),
        }
        self.usb_probe = usb_probe or USBModeProbe()

    def discover(self) -> Dict[str, ToolInfo]:
        return {name: tool.discover() for name, tool in self.tools.items()}

    def diagnostics(self, probe_versions: bool = False) -> Dict[str, object]:
        tool_info = {
            name: asdict(tool.probe() if probe_versions else tool.discover())
            for name, tool in self.tools.items()
        }
        usb_devices, usb_error = self.usb_probe.scan()
        return {
            "tools": tool_info,
            "usb_devices": [device.to_dict() for device in usb_devices],
            "usb_error": usb_error,
        }
