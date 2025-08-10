#!/usr/bin/env python3
"""
Core module for FRP Freedom
Contains configuration, logging, and device management functionality
"""

from .config import Config
from .logger import setup_logging, AuditLogger
from .device_manager import DeviceManager, DeviceInfo

__all__ = [
    'Config',
    'setup_logging',
    'AuditLogger',
    'DeviceManager',
    'DeviceInfo'
]