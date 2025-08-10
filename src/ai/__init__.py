#!/usr/bin/env python3
"""
AI Module for FRP Freedom
Provides intelligent device analysis and method recommendations
"""

from .ai_engine import AIEngine, DeviceProfile, MethodPerformance
from .notification_system import AINotificationSystem, AINotification, NotificationType

__all__ = ['AIEngine', 'DeviceProfile', 'MethodPerformance', 'AINotificationSystem', 'AINotification', 'NotificationType']