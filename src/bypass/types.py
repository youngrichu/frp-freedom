#!/usr/bin/env python3
"""
Shared types and enums for the bypass module
This module contains common types to avoid circular imports
"""

from enum import Enum
from dataclasses import dataclass
from typing import List

class BypassResult(Enum):
    """Bypass operation results"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    DEVICE_ERROR = "device_error"
    USER_CANCELLED = "user_cancelled"
    VERIFICATION_FAILED = "verification_failed"

@dataclass
class BypassMethod:
    """Bypass method information"""
    name: str
    description: str
    category: str
    risk_level: str  # low, medium, high
    success_rate: float
    estimated_time: int  # minutes
    requirements: List[str]
    supported_devices: List[str]
    android_versions: List[str]