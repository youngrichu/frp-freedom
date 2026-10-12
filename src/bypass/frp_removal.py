#!/usr/bin/env python3
"""Shared ADB-side FRP removal sequence.

Used by every method that ends up with an authorized ADB session (test-mode
ADB enable, combination firmware boot, etc.) so the removal commands and the
post-removal indicator checks stay consistent.
"""

import logging
from typing import List


FRP_REMOVAL_COMMANDS: List[List[str]] = [
    ['shell', 'settings', 'put', 'secure', 'user_setup_complete', '1'],
    ['shell', 'settings', 'put', 'system', 'device_provisioned', '1'],
    ['shell', 'settings', 'put', 'global', 'device_provisioned', '1'],
    ['shell', 'setprop', 'ro.frp.pst', ''],
]


def run_frp_removal_commands(device_manager, serial: str,
                             logger: logging.Logger = None) -> int:
    """Run the removal sequence, returning how many commands succeeded."""
    logger = logger or logging.getLogger(__name__)
    executed = 0
    for command in FRP_REMOVAL_COMMANDS:
        success, output = device_manager.execute_adb_command(serial, command)
        if success:
            executed += 1
        else:
            logger.debug(f"FRP removal command {command} failed: {output}")
    return executed


def frp_indicators_cleared(device_manager, serial: str) -> bool:
    """Check the on-device FRP indicators after a removal attempt."""
    success, output = device_manager.execute_adb_command(
        serial, ['shell', 'getprop', 'ro.frp.pst'])
    if success and not output.strip():
        return True
    success, output = device_manager.execute_adb_command(
        serial, ['shell', 'settings', 'get', 'secure', 'user_setup_complete'])
    return success and output.strip() == '1'
