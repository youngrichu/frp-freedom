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
    """Return True only on evidence that does not come from the removal writes.

    ``ro.frp.pst`` is unset on many devices that are still FRP-locked, and
    ``user_setup_complete`` / ``device_provisioned`` are the settings the
    removal sequence itself just wrote, so neither counts. A dumpsys account
    listing with no Google account is independent of those writes.
    """
    success, output = device_manager.execute_adb_command(
        serial, ['shell', 'dumpsys', 'account'])
    if not success or not output.strip():
        return False
    lowered = output.lower()
    if 'com.google' in lowered:
        return False
    return 'accounts: 0' in lowered
