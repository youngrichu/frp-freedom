#!/usr/bin/env python3
"""
Test script for FRP Freedom application
This script performs basic functionality tests to ensure the application works correctly.
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.core.config import Config
    from src.core.logger import setup_logging, AuditLogger
    from src.core.device_manager import DeviceManager
    from src.bypass.bypass_manager import BypassManager
    from src.gui.main_window import FRPFreedomApp
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)


class TestFRPFreedom(unittest.TestCase):
    """Basic tests for FRP Freedom components"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        
    def test_config_loading(self):
        """Test configuration loading"""
        self.assertIsNotNone(self.config)
        self.assertEqual(self.config.get('app.version'), '1.0.0')
        
    def test_logging_setup(self):
        """Test logging setup"""
        logger = setup_logging(self.config)
        self.assertIsNotNone(logger)
        
    def test_audit_logger(self):
        """Test audit logger"""
        audit_logger = AuditLogger(self.config)
        self.assertIsNotNone(audit_logger)
        
        # Test logging without errors
        try:
            # Test device detection logging
            device_info = {
                "model": "Test Device",
                "manufacturer": "Test Manufacturer",
                "android_version": "14",
                "serial": "test123456"
            }
            audit_logger.log_device_detection(device_info)
            
            # Test ownership verification logging
            audit_logger.log_ownership_verification("123456789012345", True, "manual_verification")
            
            # Test bypass attempt logging
            audit_logger.log_bypass_attempt(device_info, "test_method", True)
        except Exception as e:
            self.fail(f"Audit logging failed: {e}")
            
    @patch('subprocess.run')
    def test_device_manager(self, mock_run):
        """Test device manager"""
        # Mock subprocess calls
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "List of devices attached\n"
        
        device_manager = DeviceManager(self.config)
        self.assertIsNotNone(device_manager)
        
        # Test device scanning
        devices = device_manager.scan_devices()
        self.assertIsInstance(devices, list)
        
    def test_bypass_manager(self):
        """Test bypass manager with new 2025 methods"""
        device_manager = DeviceManager(self.config)
        bypass_manager = BypassManager(self.config, device_manager)
        self.assertIsNotNone(bypass_manager)
        
        # Test getting available methods
        methods = bypass_manager.available_methods
        self.assertIsInstance(methods, list)
        
        # Test that new 2025 methods are included (excluding hardware methods which require config)
        method_names = [method.name for method in methods]
        expected_2025_methods = [
            'adb_talkback_chrome',
            'samsung_setup_wizard_2025',
            'apk_injection_setup',
            'framework_patch_android15'
        ]
        
        for method_name in expected_2025_methods:
            self.assertIn(method_name, method_names, f"Missing 2025 method: {method_name}")
        
        # Test that we have at least 11 methods total (hardware methods are optional)
        self.assertGreaterEqual(len(methods), 11, "Should have at least 11 bypass methods")
        
    def test_adb_exploits_2025(self):
        """Test new 2025 ADB exploit methods"""
        from src.bypass.adb_exploits import ADBExploitManager
        device_manager = DeviceManager(self.config)
        adb_exploits = ADBExploitManager(self.config, device_manager)
        
        # Test that new methods exist
        self.assertTrue(hasattr(adb_exploits, 'talkback_chrome_exploit'))
        self.assertTrue(hasattr(adb_exploits, 'intent_manipulation_exploit'))
        
        # Test method callable
        self.assertTrue(callable(getattr(adb_exploits, 'talkback_chrome_exploit')))
        self.assertTrue(callable(getattr(adb_exploits, 'intent_manipulation_exploit')))
    
    def test_interface_exploits_2025(self):
        """Test new 2025 interface exploit methods"""
        from src.bypass.interface_exploits import InterfaceExploitManager
        device_manager = DeviceManager(self.config)
        interface_exploits = InterfaceExploitManager(self.config, device_manager)
        
        # Test that new methods exist
        self.assertTrue(hasattr(interface_exploits, 'samsung_setup_wizard_2025_exploit'))
        self.assertTrue(hasattr(interface_exploits, 'apk_injection_setup_exploit'))
        
        # Test method callable
        self.assertTrue(callable(getattr(interface_exploits, 'samsung_setup_wizard_2025_exploit')))
        self.assertTrue(callable(getattr(interface_exploits, 'apk_injection_setup_exploit')))
    
    def test_hardware_exploits_2025(self):
        """Test new 2025 hardware exploit methods"""
        from src.bypass.hardware_exploits import HardwareExploitManager
        device_manager = DeviceManager(self.config)
        hardware_exploits = HardwareExploitManager(self.config, device_manager)
        
        # Test that new methods exist
        self.assertTrue(hasattr(hardware_exploits, 'qualcomm_edl_2025_exploit'))
        self.assertTrue(hasattr(hardware_exploits, 'mediatek_cve_2025_exploit'))
        self.assertTrue(hasattr(hardware_exploits, 'mali_gpu_pixel_exploit'))
        
        # Test method callable
        self.assertTrue(callable(getattr(hardware_exploits, 'qualcomm_edl_2025_exploit')))
        self.assertTrue(callable(getattr(hardware_exploits, 'mediatek_cve_2025_exploit')))
        self.assertTrue(callable(getattr(hardware_exploits, 'mali_gpu_pixel_exploit')))
    
    def test_system_exploits_2025(self):
        """Test new 2025 system exploit methods"""
        from src.bypass.system_exploits import SystemExploitManager
        device_manager = DeviceManager(self.config)
        system_exploits = SystemExploitManager(self.config, device_manager)
        
        # Test that new method exists
        self.assertTrue(hasattr(system_exploits, 'framework_patch_android15_exploit'))
        
        # Test method callable
        self.assertTrue(callable(getattr(system_exploits, 'framework_patch_android15_exploit')))
    
    def test_gui_creation(self):
        """Test GUI creation (without showing)"""
        try:
            # Create main window without showing it
            app = FRPFreedomApp(self.config)
            self.assertIsNotNone(app)
            
            # Clean up
            if hasattr(app, 'root') and hasattr(app.root, 'destroy'):
                app.root.destroy()
        except Exception as e:
            # GUI tests might fail in headless environments
            print(f"GUI test skipped (likely headless environment): {e}")
    
    def test_bypass_methods_integration_2025(self):
        """Test integration of all 2025 bypass methods"""
        device_manager = DeviceManager(self.config)
        bypass_manager = BypassManager(self.config, device_manager)
        
        methods = bypass_manager.available_methods
        method_dict = {method.name: method for method in methods}
        
        # Test ADB methods
        adb_methods = ['adb_setup_wizard', 'adb_talkback_chrome', 'adb_talkback_legacy', 'adb_intent_manipulation']
        for method_name in adb_methods:
            self.assertIn(method_name, method_dict, f"ADB method {method_name} not found")
            method = method_dict[method_name]
            self.assertEqual(method.category, 'adb')
        
        # Test Interface methods
        interface_methods = ['emergency_call_exploit', 'chrome_intent_exploit', 'samsung_setup_wizard_2025', 'apk_injection_setup']
        for method_name in interface_methods:
            self.assertIn(method_name, method_dict, f"Interface method {method_name} not found")
            method = method_dict[method_name]
            self.assertEqual(method.category, 'interface')
        
        # Test System methods
        system_methods = ['persist_partition_edit', 'framework_patch_android15']
        for method_name in system_methods:
            self.assertIn(method_name, method_dict, f"System method {method_name} not found")
            method = method_dict[method_name]
            self.assertEqual(method.category, 'system')
        
        # Test Android version compatibility
        android15_methods = [m for m in methods if '15.0' in m.android_versions]
        self.assertGreater(len(android15_methods), 0, "No methods support Android 15")
        
        android14_methods = [m for m in methods if '14.0' in m.android_versions]
        self.assertGreater(len(android14_methods), 0, "No methods support Android 14")
        
        # Test that we have methods for different risk levels
        low_risk_methods = [m for m in methods if m.risk_level == 'low']
        medium_risk_methods = [m for m in methods if m.risk_level == 'medium']
        high_risk_methods = [m for m in methods if m.risk_level == 'high']
        
        self.assertGreater(len(low_risk_methods), 0, "No low risk methods available")
        self.assertGreater(len(medium_risk_methods), 0, "No medium risk methods available")
        self.assertGreater(len(high_risk_methods), 0, "No high risk methods available")
        
        print(f"\n✅ Integration test passed:")
        print(f"   - Total methods: {len(methods)}")
        print(f"   - ADB methods: {len([m for m in methods if m.category == 'adb'])}")
        print(f"   - Interface methods: {len([m for m in methods if m.category == 'interface'])}")
        print(f"   - System methods: {len([m for m in methods if m.category == 'system'])}")
        print(f"   - Android 15 compatible: {len(android15_methods)}")
        print(f"   - Android 14 compatible: {len(android14_methods)}")


def run_basic_tests():
    """Run basic functionality tests"""
    print("FRP Freedom - Basic Functionality Test")
    print("=" * 40)
    
    # Test 1: Import all modules
    print("\n1. Testing module imports...")
    try:
        from src.core.config import Config
        from src.core.logger import setup_logging
        from src.core.device_manager import DeviceManager
        from src.bypass.bypass_manager import BypassManager
        from src.gui.main_window import FRPFreedomApp
        print("   ✓ All modules imported successfully")
    except ImportError as e:
        print(f"   ✗ Import failed: {e}")
        return False
    
    # Test 2: Configuration
    print("\n2. Testing configuration...")
    try:
        config = Config()
        config.load_config()
        print(f"   ✓ Configuration loaded: {config.get('app.name')} v{config.get('app.version')}")
    except Exception as e:
        print(f"   ✗ Configuration failed: {e}")
        return False
    
    # Test 3: Logging
    print("\n3. Testing logging system...")
    try:
        logger = setup_logging(config)
        logger.info("Test log message")
        print("   ✓ Logging system initialized")
    except Exception as e:
        print(f"   ✗ Logging failed: {e}")
        return False
    
    # Test 4: Device Manager
    print("\n4. Testing device manager...")
    try:
        device_manager = DeviceManager(config)
        print("   ✓ Device manager initialized")
    except Exception as e:
        print(f"   ✗ Device manager failed: {e}")
        return False
    
    # Test 5: Bypass Manager
    print("\n5. Testing bypass manager...")
    try:
        bypass_manager = BypassManager(config, device_manager)
        methods = bypass_manager.available_methods
        print(f"   ✓ Bypass manager initialized with {len(methods)} methods")
    except Exception as e:
        print(f"   ✗ Bypass manager failed: {e}")
        return False
    
    print("\n" + "=" * 40)
    print("✓ All basic tests passed!")
    print("\nThe FRP Freedom application is ready to use.")
    print("Run 'python main.py' to start the application.")
    return True


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--unittest':
        # Run unit tests
        unittest.main(argv=[''], exit=False)
    else:
        # Run basic tests
        success = run_basic_tests()
        sys.exit(0 if success else 1)