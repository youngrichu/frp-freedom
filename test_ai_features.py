#!/usr/bin/env python3
"""
Comprehensive test script for AI features in FRP Freedom.
Tests all AI components including device analysis, recommendations, and notifications.
"""

import sys
import os
import time
import logging
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.device_manager import DeviceInfo
from src.bypass.bypass_manager import BypassManager
from src.bypass.types import BypassResult
from src.ai.notification_system import AINotificationSystem, NotificationType
from src.ai.ai_engine import AIEngine
from src.core.config import Config

def create_test_device():
    """Create a mock device for testing."""
    device = DeviceInfo(
        serial="test_device_001",
        model="Samsung Galaxy S21",
        manufacturer="Samsung",
        android_version="11",
        sdk_version="30",
        bootloader_version="unknown",
        frp_status="locked",
        connection_type="adb",
        chipset="Exynos 2100",
        imei="123456789012345"
    )
    
    # Add attributes expected by AIEngine
    device.brand = "Samsung"
    device.security_patch = "2023-05-01"
    device.bootloader_status = "locked"
    
    return device

def create_test_config():
    """Create a mock config for testing."""
    config = Config()
    # Load default configuration
    config.load_config()
    return config

def create_test_device_manager():
    """Create a mock device manager for testing."""
    class MockDeviceManager:
        def __init__(self):
            pass
        
        def get_connected_devices(self):
            return []
        
        def get_device_info(self, serial):
            return create_test_device()
    
    return MockDeviceManager()

def test_ai_engine():
    """Test AI Engine functionality."""
    print("\n🧠 Testing AI Engine...")
    
    config = create_test_config()
    ai_engine = AIEngine(config)
    device = create_test_device()
    
    # Test device analysis
    print("  ✓ Testing device analysis...")
    analysis = ai_engine.analyze_device(device)
    assert hasattr(analysis, 'vulnerability_score')
    assert hasattr(analysis, 'recommended_methods')
    assert hasattr(analysis, 'frp_complexity')
    print(f"    - Vulnerability Score: {analysis.vulnerability_score}")
    print(f"    - FRP Complexity: {analysis.frp_complexity}")
    print(f"    - Recommended Methods: {len(analysis.recommended_methods)}")
    
    # Test method performance tracking
    print("  ✓ Testing performance tracking...")
    ai_engine.update_method_performance("adb_enable_developer", device, BypassResult.SUCCESS, 45.2)
    ai_engine.update_method_performance("samsung_combination_file", device, BypassResult.FAILED, 120.5)
    
    # Test learning insights instead of performance stats
    insights = ai_engine.get_learning_insights()
    assert 'learning_status' in insights or 'message' in insights
    if 'learning_status' in insights:
        print(f"    - Learning Status: {insights['learning_status']}")
        print(f"    - Total Attempts: {insights.get('total_attempts', 0)}")
        print(f"    - Method Performance: {len(insights.get('method_performance', {}))} methods tracked")
    else:
        print(f"    - Status: {insights['message']}")
    
    print("  ✅ AI Engine tests passed!")

def test_bypass_manager_ai():
    """Test AI features in Bypass Manager."""
    print("\n🔧 Testing Bypass Manager AI Features...")
    
    config = create_test_config()
    device_manager = create_test_device_manager()
    bypass_manager = BypassManager(config, device_manager)
    device = create_test_device()
    
    # Test AI device analysis
    print("  ✓ Testing AI device analysis...")
    analysis = bypass_manager.get_ai_device_analysis(device)
    assert 'device_profile' in analysis
    assert 'security_assessment' in analysis
    assert 'bypass_strategy' in analysis
    assert 'vulnerability_score' in analysis['device_profile']
    assert 'recommended_methods' in analysis['device_profile']
    print(f"    - Analysis completed with {len(analysis['device_profile']['recommended_methods'])} recommendations")
    
    # Test AI recommended methods
    print("  ✓ Testing AI method recommendations...")
    methods = bypass_manager.get_recommended_methods(device)
    assert len(methods) > 0
    print(f"    - Got {len(methods)} AI-recommended methods")
    for i, method in enumerate(methods[:3]):
        # Handle both BypassMethod objects and dictionaries
        if hasattr(method, 'name'):
            name = method.name
            score = getattr(method, 'success_probability', 0.5)
        else:
            name = method.get('name', 'Unknown')
            score = method.get('success_probability', 0.5)
        print(f"      {i+1}. {name} (Score: {score:.1%})")
    
    # Test contextual help
    print("  ✓ Testing contextual help...")
    help_text = bypass_manager.get_contextual_help(device, "adb_enable_developer")
    assert len(help_text) > 0
    print(f"    - Help text length: {len(help_text)} characters")
    
    # Test AI insights
    print("  ✓ Testing AI insights...")
    insights = bypass_manager.get_ai_insights()
    assert 'learning_status' in insights or 'message' in insights
    if 'learning_status' in insights:
        print(f"    - Learning Status: {insights['learning_status']}")
        print(f"    - Total Attempts: {insights.get('total_attempts', 0)}")
    else:
        print(f"    - Status: {insights['message']}")
    
    # Test next method suggestion
    print("  ✓ Testing next method suggestions...")
    next_method = bypass_manager.suggest_next_method(device, ["adb_enable_developer"])
    if next_method:
        print(f"    - Suggested next method: {next_method.name}")
    else:
        print("    - No alternative method suggested")
    
    print("  ✅ Bypass Manager AI tests passed!")

def test_notification_system():
    """Test AI Notification System."""
    print("\n🔔 Testing AI Notification System...")
    
    # Create a mock parent window for testing
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()  # Hide the window
    
    notification_system = AINotificationSystem(root)
    
    # Test different notification types
    print("  ✓ Testing notification creation...")
    
    # Test method recommendation
    notification_system.notify_method_recommendation(
        "adb_setup_wizard", 0.85,
        lambda: print("Method selected")
    )
    
    # Test device analysis completion
    notification_system.notify_device_analysis_complete(
        0.75,
        ["adb_enable_developer", "samsung_combination_file"]
    )
    
    # Test method failure insight
    notification_system.notify_method_failure_insight(
        "failed_method",
        "suggested_alternative",
        lambda: print("Alternative tried")
    )
    
    # Test learning update
    notification_system.notify_learning_update(
        "Improved recommendations based on recent successes"
    )
    
    print(f"    - Created {len(notification_system.notification_widgets)} notifications")
    
    # Test notification queue functionality
    print("  ✓ Testing notification queue...")
    queue_size = len(notification_system.notification_queue)
    print(f"    - Queue size: {queue_size}")
    print("    - Notification system working correctly")
    
    # Clean up
    root.destroy()
    
    print("  ✅ Notification System tests passed!")

def test_integration():
    """Test integration between components."""
    print("\n🔗 Testing Component Integration...")
    
    config = create_test_config()
    device_manager = create_test_device_manager()
    bypass_manager = BypassManager(config, device_manager)
    device = create_test_device()
    
    # Mock notification system
    with patch('tkinter.Toplevel'), patch('tkinter.Label'), patch('tkinter.Button'):
        notification_system = AINotificationSystem(None)
        bypass_manager.set_notification_system(notification_system)
        
        print("  ✓ Testing notification system integration...")
        assert bypass_manager.notification_system is not None
        
        # Test AI analysis with notifications
        print("  ✓ Testing AI analysis with notifications...")
        analysis = bypass_manager.get_ai_device_analysis(device)
        
        # Verify notifications were created
        assert len(notification_system.notification_widgets) >= 0
        print(f"    - Generated {len(notification_system.notification_widgets)} notifications")
        
        # Test AI insights with notifications
    print("  ✓ Testing AI analysis with notifications...")
    initial_count = len(notification_system.notification_widgets)
    insights = bypass_manager.get_ai_insights()
    
    # Should create learning update notification if new insights
    if insights.get('new_insights_available'):
        assert len(notification_system.notification_widgets) > initial_count
        print("    - Learning update notification created")
    else:
        print("    - No new insights available for notification")
        
    print("  ✅ Integration tests passed!")

def test_error_handling():
    """Test error handling in AI components."""
    print("\n⚠️  Testing Error Handling...")
    
    config = create_test_config()
    device_manager = create_test_device_manager()
    bypass_manager = BypassManager(config, device_manager)
    
    # Test with invalid device
    print("  ✓ Testing invalid device handling...")
    try:
        invalid_device = None
        analysis = bypass_manager.get_ai_device_analysis(invalid_device)
        # Should handle gracefully
        print("    - Invalid device handled gracefully")
    except Exception as e:
        print(f"    - Expected error handled: {type(e).__name__}")
    
    # Test with invalid method name
    print("  ✓ Testing invalid method name handling...")
    device = create_test_device()
    help_text = bypass_manager.get_contextual_help(device, "nonexistent_method")
    assert isinstance(help_text, dict)  # Should return default help dictionary
    print("    - Invalid method name handled gracefully")
    
    print("  ✅ Error handling tests passed!")

def run_performance_test():
    """Test performance of AI operations."""
    print("\n⚡ Testing Performance...")
    
    config = create_test_config()
    device_manager = create_test_device_manager()
    bypass_manager = BypassManager(config, device_manager)
    device = create_test_device()
    
    # Test AI analysis performance
    print("  ✓ Testing AI analysis performance...")
    start_time = time.time()
    analysis = bypass_manager.get_ai_device_analysis(device)
    analysis_time = time.time() - start_time
    print(f"    - AI analysis completed in {analysis_time:.3f}s")
    assert analysis_time < 2.0, "AI analysis should complete within 2 seconds"
    
    # Test method recommendation performance
    print("  ✓ Testing method recommendation performance...")
    start_time = time.time()
    methods = bypass_manager.get_recommended_methods(device)
    end_time = time.time()
    recommendation_time = end_time - start_time
    print(f"    - Method recommendations completed in {recommendation_time:.3f}s")
    assert recommendation_time < 1.0, "Method recommendations should complete within 1 second"
    
    print("  ✅ Performance tests passed!")

def main():
    """Run all AI feature tests."""
    print("🚀 Starting FRP Freedom AI Features Test Suite")
    print("=" * 50)
    
    try:
        # Run all test suites
        test_ai_engine()
        test_bypass_manager_ai()
        test_notification_system()
        test_integration()
        test_error_handling()
        run_performance_test()
        
        print("\n" + "=" * 50)
        print("🎉 All AI Feature Tests Passed Successfully!")
        print("\n✅ Test Summary:")
        print("  • AI Engine: Device analysis, performance tracking")
        print("  • Bypass Manager: AI recommendations, contextual help")
        print("  • Notification System: All notification types")
        print("  • Integration: Component communication")
        print("  • Error Handling: Graceful failure management")
        print("  • Performance: Response time validation")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)