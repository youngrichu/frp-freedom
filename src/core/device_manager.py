#!/usr/bin/env python3
"""
Device Manager for FRP Freedom
Handles device detection, communication, and information gathering
"""

import subprocess
import re
import time
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json
from dataclasses import dataclass

@dataclass
class DeviceInfo:
    """Device information container"""
    serial: str
    model: str
    manufacturer: str
    android_version: str
    sdk_version: str
    bootloader_version: str
    frp_status: str
    connection_type: str  # adb, fastboot, download
    chipset: str = "unknown"
    imei: str = ""
    brand: str = "unknown"
    bootloader_status: str = "unknown"
    root_status: str = "unknown"
    
    def to_dict(self) -> Dict:
        return {
            "serial": self.serial,
            "model": self.model,
            "manufacturer": self.manufacturer,
            "android_version": self.android_version,
            "sdk_version": self.sdk_version,
            "bootloader_version": self.bootloader_version,
            "frp_status": self.frp_status,
            "connection_type": self.connection_type,
            "chipset": self.chipset,
            "imei": self.imei[:4] + "****" + self.imei[-4:] if len(self.imei) >= 8 else "unknown",
            "brand": self.brand,
            "bootloader_status": self.bootloader_status,
            "root_status": self.root_status
        }

class DeviceManager:
    """Manages device detection and communication"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.adb_path = self._find_adb_binary()
        self.fastboot_path = self._find_fastboot_binary()
        self.connected_devices: List[DeviceInfo] = []
        
    def _find_adb_binary(self) -> Optional[Path]:
        """Find ADB binary in system PATH or bundled tools"""
        # Check bundled tools first
        bundled_adb = Path(__file__).parent.parent.parent / "tools" / "adb"
        if bundled_adb.exists():
            return bundled_adb
        
        # Check system PATH
        try:
            result = subprocess.run(["which", "adb"], capture_output=True, text=True)
            if result.returncode == 0:
                return Path(result.stdout.strip())
        except Exception:
            pass
        
        self.logger.warning("ADB binary not found. Some features may not work.")
        return None
    
    def _find_fastboot_binary(self) -> Optional[Path]:
        """Find fastboot binary in system PATH or bundled tools"""
        # Check bundled tools first
        bundled_fastboot = Path(__file__).parent.parent.parent / "tools" / "fastboot"
        if bundled_fastboot.exists():
            return bundled_fastboot
        
        # Check system PATH
        try:
            result = subprocess.run(["which", "fastboot"], capture_output=True, text=True)
            if result.returncode == 0:
                return Path(result.stdout.strip())
        except Exception:
            pass
        
        self.logger.warning("Fastboot binary not found. Some features may not work.")
        return None
    
    def scan_devices(self) -> List[DeviceInfo]:
        """Scan for connected Android devices"""
        self.logger.info("Scanning for connected devices...")
        devices = []
        
        # Scan ADB devices
        adb_devices = self._scan_adb_devices()
        devices.extend(adb_devices)
        
        # Scan fastboot devices
        fastboot_devices = self._scan_fastboot_devices()
        devices.extend(fastboot_devices)
        
        # Scan download mode devices (placeholder for future implementation)
        download_devices = self._scan_download_mode_devices()
        devices.extend(download_devices)
        
        self.connected_devices = devices
        self.logger.info(f"Found {len(devices)} connected device(s)")
        
        return devices
    
    def _scan_adb_devices(self) -> List[DeviceInfo]:
        """Scan for ADB-connected devices"""
        if not self.adb_path:
            self.logger.debug("No ADB path found")
            return []
        
        devices = []
        try:
            # Get device list
            result = subprocess.run(
                [str(self.adb_path), "devices", "-l"],
                capture_output=True, text=True, timeout=10
            )
            
            self.logger.debug(f"ADB devices output: {result.stdout}")
            
            if result.returncode != 0:
                self.logger.error(f"ADB devices command failed: {result.stderr}")
                return []
            
            # Parse device list
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            self.logger.debug(f"Processing {len(lines)} device lines")
            
            for line in lines:
                self.logger.debug(f"Processing line: '{line}'")
                if line.strip():
                    # Split by whitespace and get the first two parts (serial and status)
                    parts = line.split()
                    if len(parts) >= 2:
                        serial = parts[0]
                        status = parts[1]
                        self.logger.debug(f"Found device: serial={serial}, status={status}")
                        
                        if status in ['device', 'recovery']:
                            self.logger.debug(f"Getting device info for authorized device: {serial}")
                            device_info = self._get_adb_device_info(serial)
                            if device_info:
                                self.logger.debug(f"Successfully got device info for {serial}")
                                devices.append(device_info)
                            else:
                                self.logger.warning(f"Failed to get device info for {serial}")
                        elif status == 'unauthorized':
                            self.logger.debug(f"Getting device info for unauthorized device: {serial}")
                            # Handle unauthorized devices for FRP bypass scenarios
                            device_info = self._get_unauthorized_device_info(serial)
                            if device_info:
                                self.logger.debug(f"Successfully got unauthorized device info for {serial}")
                                devices.append(device_info)
                            else:
                                self.logger.warning(f"Failed to get unauthorized device info for {serial}")
                    else:
                        self.logger.debug(f"Skipping line with insufficient parts: {len(parts)}")
        
        except subprocess.TimeoutExpired:
            self.logger.error("ADB scan timeout")
        except Exception as e:
            self.logger.error(f"Error scanning ADB devices: {e}")
        
        self.logger.debug(f"Returning {len(devices)} devices")
        return devices
    
    def _scan_fastboot_devices(self) -> List[DeviceInfo]:
        """Scan for fastboot-connected devices"""
        if not self.fastboot_path:
            return []
        
        devices = []
        try:
            result = subprocess.run(
                [str(self.fastboot_path), "devices"],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode != 0:
                return []
            
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.strip() and '\t' in line:
                    serial = line.split('\t')[0]
                    device_info = self._get_fastboot_device_info(serial)
                    if device_info:
                        devices.append(device_info)
        
        except Exception as e:
            self.logger.error(f"Error scanning fastboot devices: {e}")
        
        return devices
    
    def _scan_download_mode_devices(self) -> List[DeviceInfo]:
        """Scan for devices in download mode (placeholder)"""
        # This would implement detection for Samsung Download Mode,
        # MediaTek Download Mode, Qualcomm EDL mode, etc.
        # For now, return empty list
        return []
    
    def _get_adb_device_info(self, serial: str) -> Optional[DeviceInfo]:
        """Get detailed information for an ADB device"""
        try:
            self.logger.debug(f"Getting device properties for {serial}")
            # Get device properties
            props = self._get_device_properties(serial)
            self.logger.debug(f"Got {len(props)} properties for {serial}")
            
            # Check FRP status
            self.logger.debug(f"Checking FRP status for {serial}")
            frp_status = self._check_frp_status(serial)
            self.logger.debug(f"FRP status for {serial}: {frp_status}")
            
            manufacturer = props.get('ro.product.manufacturer', 'unknown')
            device_info = DeviceInfo(
                serial=serial,
                model=props.get('ro.product.model', 'unknown'),
                manufacturer=manufacturer,
                android_version=props.get('ro.build.version.release', 'unknown'),
                sdk_version=props.get('ro.build.version.sdk', 'unknown'),
                bootloader_version=props.get('ro.bootloader', 'unknown'),
                frp_status=frp_status,
                connection_type='adb',
                chipset=props.get('ro.hardware', 'unknown'),
                brand=manufacturer,  # Use manufacturer as brand
                bootloader_status='unknown',  # Would need additional checks
                root_status='unknown'  # Would need additional checks
            )
            
            self.logger.debug(f"Created device info for {serial}: {device_info.model} ({device_info.manufacturer})")
            
            # Try to get IMEI (may require root)
            try:
                imei = self._get_device_imei(serial)
                device_info.imei = imei
            except Exception:
                pass  # IMEI not accessible
            
            return device_info
        
        except Exception as e:
            self.logger.error(f"Error getting device info for {serial}: {e}")
            return None
    
    def _get_unauthorized_device_info(self, serial: str) -> Optional[DeviceInfo]:
        """Get basic device info for unauthorized devices (FRP bypass scenarios)"""
        try:
            self.logger.info(f"Creating device info for unauthorized device: {serial}")
            
            # Create basic device info for FRP bypass
            device_info = DeviceInfo(
                serial=serial,
                model="Unknown (Unauthorized)",
                manufacturer="Unknown",
                android_version="Unknown",
                sdk_version="Unknown",
                bootloader_version="Unknown",
                frp_status="locked",  # Assume FRP is locked for unauthorized devices
                connection_type="adb_unauthorized",
                chipset="unknown",
                imei="",
                brand="Unknown",
                bootloader_status="Unknown",
                root_status="Unknown"
            )
            
            self.logger.info(f"Created unauthorized device info: {device_info.serial}")
            return device_info
            
        except Exception as e:
            self.logger.error(f"Error creating unauthorized device info for {serial}: {e}")
            return None
    
    def _get_fastboot_device_info(self, serial: str) -> Optional[DeviceInfo]:
        """Get information for a fastboot device"""
        try:
            # Get basic fastboot variables
            variables = {}
            for var in ['product', 'version-bootloader', 'version-baseband']:
                try:
                    result = subprocess.run(
                        [str(self.fastboot_path), "-s", serial, "getvar", var],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        # Fastboot outputs to stderr
                        output = result.stderr
                        if ':' in output:
                            variables[var] = output.split(':', 1)[1].strip()
                except Exception:
                    continue
            
            device_info = DeviceInfo(
                serial=serial,
                model=variables.get('product', 'unknown'),
                manufacturer='unknown',  # Not easily available in fastboot
                android_version='unknown',
                sdk_version='unknown',
                bootloader_version=variables.get('version-bootloader', 'unknown'),
                frp_status='unknown',  # Cannot check in fastboot mode
                connection_type='fastboot',
                brand='unknown',
                bootloader_status='unlocked',  # In fastboot mode, bootloader is likely unlocked
                root_status='unknown'
            )
            
            return device_info
        
        except Exception as e:
            self.logger.error(f"Error getting fastboot device info for {serial}: {e}")
            return None
    
    def _get_device_properties(self, serial: str) -> Dict[str, str]:
        """Get device properties via ADB"""
        props = {}
        try:
            result = subprocess.run(
                [str(self.adb_path), "-s", serial, "shell", "getprop"],
                capture_output=True, text=True, timeout=15
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if ':' in line and '[' in line and ']' in line:
                        # Parse property line: [key]: [value]
                        match = re.match(r'\[([^\]]+)\]:\s*\[([^\]]*)\]', line)
                        if match:
                            key, value = match.groups()
                            props[key] = value
        
        except Exception as e:
            self.logger.error(f"Error getting properties for {serial}: {e}")
        
        return props
    
    def _check_frp_status(self, serial: str) -> str:
        """Check FRP status of device"""
        try:
            # Try multiple methods to check FRP status
            
            # Method 1: Check persistent properties
            result = subprocess.run(
                [str(self.adb_path), "-s", serial, "shell", "getprop", "ro.frp.pst"],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                frp_value = result.stdout.strip()
                if frp_value in ['', '0', 'none']:
                    return 'disabled'
                else:
                    return 'enabled'
            
            # Method 2: Check accounts database
            result = subprocess.run(
                [str(self.adb_path), "-s", serial, "shell", 
                 "sqlite3 /data/system/users/0/accounts.db 'SELECT count(*) FROM accounts'"],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                count = result.stdout.strip()
                if count and count.isdigit() and int(count) > 0:
                    return 'enabled'
                else:
                    return 'disabled'
            
            # Method 3: Check setup wizard state
            result = subprocess.run(
                [str(self.adb_path), "-s", serial, "shell", 
                 "settings get secure user_setup_complete"],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                setup_complete = result.stdout.strip()
                if setup_complete == '0':
                    return 'frp_locked'
                elif setup_complete == '1':
                    return 'setup_complete'
            
        except Exception as e:
            self.logger.error(f"Error checking FRP status for {serial}: {e}")
        
        return 'unknown'
    
    def _get_device_imei(self, serial: str) -> str:
        """Get device IMEI (requires appropriate permissions)"""
        try:
            # Try service call method
            result = subprocess.run(
                [str(self.adb_path), "-s", serial, "shell", 
                 "service call iphonesubinfo 1"],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                # Parse the hex output to get IMEI
                output = result.stdout
                # This is a simplified parser - real implementation would be more robust
                imei_match = re.search(r'([0-9]{15})', output)
                if imei_match:
                    return imei_match.group(1)
        
        except Exception:
            pass
        
        return ""
    
    def execute_adb_command(self, serial: str, command: List[str]) -> Tuple[bool, str]:
        """Execute ADB command on specific device"""
        if not self.adb_path:
            return False, "ADB not available"
        
        try:
            full_command = [str(self.adb_path), "-s", serial] + command
            result = subprocess.run(
                full_command,
                capture_output=True, text=True, timeout=30
            )
            
            return result.returncode == 0, result.stdout + result.stderr
        
        except subprocess.TimeoutExpired:
            return False, "Command timeout"
        except Exception as e:
            return False, f"Command failed: {e}"
    
    def execute_fastboot_command(self, serial: str, command: List[str]) -> Tuple[bool, str]:
        """Execute fastboot command on specific device"""
        if not self.fastboot_path:
            return False, "Fastboot not available"
        
        try:
            full_command = [str(self.fastboot_path), "-s", serial] + command
            result = subprocess.run(
                full_command,
                capture_output=True, text=True, timeout=60
            )
            
            return result.returncode == 0, result.stdout + result.stderr
        
        except subprocess.TimeoutExpired:
            return False, "Command timeout"
        except Exception as e:
            return False, f"Command failed: {e}"
    
    def get_device_by_serial(self, serial: str) -> Optional[DeviceInfo]:
        """Get device info by serial number"""
        for device in self.connected_devices:
            if device.serial == serial:
                return device
        return None
    
    def refresh_device_info(self, serial: str) -> Optional[DeviceInfo]:
        """Refresh information for a specific device"""
        device = self.get_device_by_serial(serial)
        if not device:
            return None
        
        if device.connection_type == 'adb':
            updated_device = self._get_adb_device_info(serial)
        elif device.connection_type == 'fastboot':
            updated_device = self._get_fastboot_device_info(serial)
        else:
            return device
        
        if updated_device:
            # Update the device in the list
            for i, dev in enumerate(self.connected_devices):
                if dev.serial == serial:
                    self.connected_devices[i] = updated_device
                    break
            return updated_device
        
        return device