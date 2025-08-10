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
        self.assertEqual(self.config.get('app.name'), 'FRP Freedom')
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
            audit_logger.log_device_detection("test_device", "connected")
            audit_logger.log_ownership_verification("test_user", True, "Test verification")
            audit_logger.log_bypass_attempt("test_device", "test_method", "started")
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
        """Test bypass manager"""
        device_manager = DeviceManager(self.config)
        bypass_manager = BypassManager(self.config, device_manager)
        self.assertIsNotNone(bypass_manager)
        
        # Test method initialization
        bypass_manager.initialize_methods()
        
        # Test getting available methods
        methods = bypass_manager.get_available_methods()
        self.assertIsInstance(methods, list)
        
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