#!/usr/bin/env python3
"""
Bypass Manager for FRP Freedom
Coordinates different bypass methods and manages the bypass process
"""

import logging
import time
from typing import Dict, List, Optional, Callable, Any

from ..core.device_manager import DeviceInfo, DeviceManager
from .types import BypassResult, BypassMethod
from .adb_exploits import ADBExploitManager
from .interface_exploits import InterfaceExploitManager
from .system_exploits import SystemExploitManager
from .hardware_exploits import HardwareExploitManager
from ..ai.ai_engine import AIEngine, DeviceProfile
    
class BypassManager:
    """Main bypass coordination class"""
    
    def __init__(self, config, device_manager: DeviceManager):
        self.config = config
        self.device_manager = device_manager
        self.logger = logging.getLogger(__name__)
        
        # Initialize exploit managers
        self.adb_exploits = ADBExploitManager(config, device_manager)
        self.interface_exploits = InterfaceExploitManager(config, device_manager)
        self.system_exploits = SystemExploitManager(config, device_manager)
        self.hardware_exploits = HardwareExploitManager(config, device_manager)
        
        # Initialize AI engine
        self.ai_engine = AIEngine(config)
        
        # Initialize notification system (will be set later)
        self.notification_system = None
        
        # Progress callback
        self.progress_callback: Optional[Callable[[str, int], None]] = None
        
        # Available bypass methods
        self.available_methods = self._initialize_methods()
    
    def _initialize_methods(self) -> List[BypassMethod]:
        """Initialize available bypass methods"""
        methods = []
        
        # ADB-based methods
        if self.config.get('bypass_methods.adb_exploits', True):
            methods.extend([
                BypassMethod(
                    name="adb_setup_wizard",
                    description="Exploit setup wizard to enable ADB debugging",
                    category="adb",
                    risk_level="low",
                    success_rate=0.85,
                    estimated_time=5,
                    requirements=["USB connection", "Setup wizard active"],
                    supported_devices=["Samsung", "Google", "LG", "HTC"],
                    android_versions=["5.0", "6.0", "7.0", "8.0", "9.0", "10.0", "11.0"]
                ),
                BypassMethod(
                    name="adb_talkback_chrome",
                    description="TalkBack + Chrome navigation for Android 14/15 (2025 method)",
                    category="adb",
                    risk_level="low",
                    success_rate=0.92,
                    estimated_time=6,
                    requirements=["TalkBack available", "Chrome browser", "Voice commands"],
                    supported_devices=["Samsung Galaxy A04", "Samsung Galaxy S24", "Samsung"],
                    android_versions=["14.0", "15.0"]
                ),
                BypassMethod(
                    name="adb_talkback_legacy",
                    description="Use TalkBack accessibility to bypass FRP (legacy method)",
                    category="adb",
                    risk_level="low",
                    success_rate=0.75,
                    estimated_time=8,
                    requirements=["ADB access", "TalkBack available"],
                    supported_devices=["Samsung", "Google", "Xiaomi"],
                    android_versions=["5.0", "6.0", "7.0", "8.0", "9.0", "10.0"]
                ),
                BypassMethod(
                    name="adb_intent_manipulation",
                    description="ADB intent manipulation for SQLite database editing",
                    category="adb",
                    risk_level="medium",
                    success_rate=0.88,
                    estimated_time=10,
                    requirements=["ADB access", "USB debugging enabled"],
                    supported_devices=["Samsung", "Xiaomi", "Huawei", "Google"],
                    android_versions=["12.0", "13.0", "14.0", "15.0"]
                )
            ])
        
        # Interface exploit methods
        methods.extend([
            BypassMethod(
                name="emergency_call_exploit",
                description="Exploit emergency call interface to access settings",
                category="interface",
                risk_level="low",
                success_rate=0.70,
                estimated_time=10,
                requirements=["Physical access", "Emergency call available"],
                supported_devices=["Samsung", "LG", "HTC"],
                android_versions=["5.0", "6.0", "7.0", "8.0"]
            ),
            BypassMethod(
                name="chrome_intent_exploit",
                description="Use Chrome browser intent to bypass setup",
                category="interface",
                risk_level="medium",
                success_rate=0.65,
                estimated_time=12,
                requirements=["ADB access", "Chrome browser"],
                supported_devices=["Samsung", "Google", "Xiaomi"],
                android_versions=["6.0", "7.0", "8.0", "9.0", "10.0"]
            ),
            BypassMethod(
                name="apk_injection_setup",
                description="APK injection during setup wizard (no-PC method)",
                category="interface",
                risk_level="medium",
                success_rate=0.82,
                estimated_time=15,
                requirements=["Physical access", "Setup wizard active", "File manager access"],
                supported_devices=["Xiaomi", "Huawei", "Samsung"],
                android_versions=["13.0", "14.0", "15.0"]
            ),
            BypassMethod(
                name="samsung_setup_wizard_2025",
                description="Samsung-specific setup wizard exploit (2025 method)",
                category="interface",
                risk_level="low",
                success_rate=0.95,
                estimated_time=8,
                requirements=["Samsung device", "Setup wizard", "Precise timing"],
                supported_devices=["Samsung Galaxy A04", "Samsung Galaxy S24", "Samsung"],
                android_versions=["14.0", "15.0"]
            )
        ])
        
        # System-level methods
        if self.config.get('bypass_methods.bootloader_exploits', True):
            methods.extend([
                BypassMethod(
                    name="accounts_db_modification",
                    description="Modify accounts database to remove FRP",
                    category="system",
                    risk_level="medium",
                    success_rate=0.90,
                    estimated_time=15,
                    requirements=["Root access", "Custom recovery"],
                    supported_devices=["Samsung", "Google", "Xiaomi", "OnePlus"],
                    android_versions=["5.0", "6.0", "7.0", "8.0", "9.0", "10.0"]
                ),
                BypassMethod(
                    name="persist_partition_edit",
                    description="Edit persist partition to disable FRP",
                    category="system",
                    risk_level="high",
                    success_rate=0.95,
                    estimated_time=20,
                    requirements=["Unlocked bootloader", "Custom recovery"],
                    supported_devices=["Samsung", "Google", "Xiaomi"],
                    android_versions=["6.0", "7.0", "8.0", "9.0", "10.0", "11.0", "12.0", "13.0"]
                ),
                BypassMethod(
                    name="framework_patch_android15",
                    description="Framework patching for Android 15 hardened FRP",
                    category="system",
                    risk_level="high",
                    success_rate=0.78,
                    estimated_time=35,
                    requirements=["Root access", "Custom recovery", "Framework modification"],
                    supported_devices=["Samsung", "Google", "Xiaomi"],
                    android_versions=["15.0"]
                )
            ])
        
        # Hardware methods (if enabled)
        if self.config.get('bypass_methods.hardware_methods', False):
            methods.extend([
                BypassMethod(
                    name="download_mode_flash",
                    description="Flash custom firmware via download mode",
                    category="hardware",
                    risk_level="high",
                    success_rate=0.85,
                    estimated_time=30,
                    requirements=["Download mode", "Custom firmware"],
                    supported_devices=["Samsung"],
                    android_versions=["5.0", "6.0", "7.0", "8.0", "9.0", "10.0", "11.0"]
                ),
                BypassMethod(
                    name="qualcomm_edl_2025",
                    description="Qualcomm EDL mode with 2025 GPU exploits (CVE-2025-48530)",
                    category="hardware",
                    risk_level="high",
                    success_rate=0.92,
                    estimated_time=35,
                    requirements=["EDL mode", "Qualcomm chipset", "GPU vulnerability"],
                    supported_devices=["Samsung Galaxy S24", "Xiaomi", "OnePlus", "Google"],
                    android_versions=["13.0", "14.0", "15.0"]
                ),
                BypassMethod(
                    name="mediatek_cve_2025",
                    description="MediaTek out-of-bounds write exploit (CVE-2025-20698)",
                    category="hardware",
                    risk_level="high",
                    success_rate=0.89,
                    estimated_time=40,
                    requirements=["MediaTek chipset", "SP Flash Tool", "Custom firmware"],
                    supported_devices=["Xiaomi", "Realme", "Oppo"],
                    android_versions=["13.0", "14.0", "15.0"]
                ),
                BypassMethod(
                    name="mali_gpu_pixel_exploit",
                    description="Mali GPU vulnerability for Pixel devices (2024 method)",
                    category="hardware",
                    risk_level="high",
                    success_rate=0.87,
                    estimated_time=25,
                    requirements=["Google Pixel", "Mali GPU", "Kernel exploit"],
                    supported_devices=["Google Pixel 7", "Google Pixel 8", "Google Pixel 8 Pro"],
                    android_versions=["14.0"]
                )
            ])
        
        return methods
    
    def get_recommended_methods(self, device: DeviceInfo) -> List[BypassMethod]:
        """Get AI-enhanced recommended bypass methods for a specific device"""
        # Get AI analysis of the device
        device_profile = self.ai_engine.analyze_device(device)
        
        # Get compatible methods using traditional logic
        compatible_methods = []
        for method in self.available_methods:
            if self._is_method_compatible(method, device):
                compatible_methods.append(method)
        
        # Enhance with AI recommendations
        ai_recommended_names = device_profile.recommended_methods
        ai_methods = [m for m in compatible_methods if m.name in ai_recommended_names]
        other_methods = [m for m in compatible_methods if m.name not in ai_recommended_names]
        
        # Sort AI methods by success probability
        ai_methods.sort(key=lambda m: device_profile.success_probability.get(m.name, 0.5), reverse=True)
        
        # Sort other methods by traditional criteria
        other_methods.sort(key=lambda m: (m.success_rate, -self._risk_score(m.risk_level)), reverse=True)
        
        # Combine: AI recommendations first, then others
        recommended = ai_methods + other_methods
        
        self.logger.info(f"AI recommended {len(ai_methods)} methods for {device.brand} {device.model}")
        
        # Send notification about method recommendations
        if self.notification_system and ai_methods:
            top_method = ai_methods[0]
            success_prob = analysis.get('success_probabilities', {}).get(top_method.name, 0.5)
            self.notification_system.notify_method_recommendation(
                top_method.name,
                success_prob
            )
        
        return recommended
    
    def _is_method_compatible(self, method: BypassMethod, device: DeviceInfo) -> bool:
        """Check if a method is compatible with the device"""
        # Check manufacturer
        if device.manufacturer.lower() not in [d.lower() for d in method.supported_devices]:
            return False
        
        # Check Android version
        device_version = device.android_version
        if device_version not in method.android_versions:
            # Try to match major version
            device_major = device_version.split('.')[0] if '.' in device_version else device_version
            method_majors = [v.split('.')[0] for v in method.android_versions]
            if device_major not in method_majors:
                return False
        
        # Check connection type requirements
        if method.category == 'adb' and device.connection_type != 'adb':
            return False
        elif method.category == 'hardware' and device.connection_type not in ['fastboot', 'download']:
            return False
        
        return True
    
    def _risk_score(self, risk_level: str) -> int:
        """Convert risk level to numeric score"""
        risk_scores = {'low': 1, 'medium': 2, 'high': 3}
        return risk_scores.get(risk_level, 2)
    
    def execute_bypass(self, device: DeviceInfo, method_name: str, 
                      progress_callback: Optional[Callable[[str, int], None]] = None) -> Dict[str, Any]:
        """Execute a specific bypass method with AI monitoring"""
        self.progress_callback = progress_callback
        start_time = time.time()
        
        # Find the method
        method = next((m for m in self.available_methods if m.name == method_name), None)
        if not method:
            return {
                'result': BypassResult.FAILED,
                'message': f'Unknown bypass method: {method_name}',
                'details': {}
            }
        
        self.logger.info(f"Starting bypass method '{method_name}' on device {device.serial}")
        self._update_progress(f"Initializing {method.description}", 0)
        
        try:
            # Pre-bypass checks
            if not self._pre_bypass_checks(device, method):
                return {
                    'result': BypassResult.VERIFICATION_FAILED,
                    'message': 'Pre-bypass verification failed',
                    'details': {}
                }
            
            # Execute the appropriate bypass method
            if method.category == 'adb':
                result = self._execute_adb_bypass(device, method)
            elif method.category == 'interface':
                result = self._execute_interface_bypass(device, method)
            elif method.category == 'system':
                result = self._execute_system_bypass(device, method)
            elif method.category == 'hardware':
                result = self._execute_hardware_bypass(device, method)
            else:
                result = {
                    'result': BypassResult.FAILED,
                    'message': f'Unsupported method category: {method.category}',
                    'details': {}
                }
            
            # Post-bypass verification
            if result['result'] == BypassResult.SUCCESS:
                self._update_progress("Verifying bypass success", 90)
                if self._verify_bypass_success(device):
                    self._update_progress("Bypass completed successfully", 100)
                    self.logger.info(f"Bypass method '{method_name}' completed successfully")
                else:
                    result['result'] = BypassResult.PARTIAL
                    result['message'] = "Bypass partially successful, manual verification needed"
            
            # Update AI performance tracking
            execution_time = time.time() - start_time
            self.ai_engine.update_method_performance(method_name, device, result['result'], execution_time)
            
            # Send failure notification if method failed
            if result['result'] == BypassResult.FAILED and self.notification_system:
                suggested_method = self.suggest_next_method(device, [method_name])
                if suggested_method:
                    self.notification_system.notify_method_failure_insight(
                        method_name,
                        suggested_method.name,
                        lambda data: self.execute_bypass(device, data['suggested_alternative'])
                    )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Bypass method '{method_name}' failed with error: {e}")
            
            # Update AI with failure
            self.ai_engine.update_method_performance(method_name, device, BypassResult.FAILED, execution_time)
            
            # Send failure notification
            if self.notification_system:
                suggested_method = self.suggest_next_method(device, [method_name])
                if suggested_method:
                    self.notification_system.notify_method_failure_insight(
                        method_name,
                        suggested_method.name,
                        lambda data: self.execute_bypass(device, data['suggested_alternative'])
                    )
            
            return {
                 'result': BypassResult.FAILED,
                 'message': f'Bypass execution failed: {str(e)}',
                 'details': {'error': str(e), 'execution_time': execution_time}
             }
    
    def _pre_bypass_checks(self, device: DeviceInfo, method: BypassMethod) -> bool:
        """Perform pre-bypass security and compatibility checks"""
        self._update_progress("Performing security checks", 10)
        
        # Check rate limiting
        if not self._check_rate_limiting(device.serial):
            self.logger.warning(f"Rate limit exceeded for device {device.serial}")
            return False
        
        # Verify device requirements
        self._update_progress("Verifying device requirements", 20)
        if not self._verify_device_requirements(device, method):
            self.logger.warning(f"Device requirements not met for method {method.name}")
            return False
        
        return True
    
    def _check_rate_limiting(self, serial: str) -> bool:
        """Check if device has exceeded rate limits"""
        # This would check against a database or file of recent attempts
        # For now, always return True
        return True
    
    def _verify_device_requirements(self, device: DeviceInfo, method: BypassMethod) -> bool:
        """Verify device meets method requirements"""
        for requirement in method.requirements:
            if requirement == "USB connection" and device.connection_type not in ['adb', 'fastboot']:
                return False
            elif requirement == "ADB access" and device.connection_type != 'adb':
                return False
            elif requirement == "Root access":
                # Check if device has root access
                success, output = self.device_manager.execute_adb_command(device.serial, ['shell', 'su', '-c', 'id'])
                if not success or 'uid=0' not in output:
                    return False
        
        return True
    
    def _execute_adb_bypass(self, device: DeviceInfo, method: BypassMethod) -> Dict[str, Any]:
        """Execute ADB-based bypass methods"""
        if method.name == "adb_setup_wizard":
            return self.adb_exploits.setup_wizard_exploit(device, self._update_progress)
        elif method.name == "adb_talkback":
            return self.adb_exploits.talkback_exploit(device, self._update_progress)
        else:
            return {'result': BypassResult.FAILED, 'message': f'Unknown ADB method: {method.name}', 'details': {}}
    
    def _execute_interface_bypass(self, device: DeviceInfo, method: BypassMethod) -> Dict[str, Any]:
        """Execute interface-based bypass methods"""
        if method.name == "emergency_call_exploit":
            return self.interface_exploits.emergency_call_exploit(device, self._update_progress)
        elif method.name == "chrome_intent_exploit":
            return self.interface_exploits.chrome_intent_exploit(device, self._update_progress)
        else:
            return {'result': BypassResult.FAILED, 'message': f'Unknown interface method: {method.name}', 'details': {}}
    
    def _execute_system_bypass(self, device: DeviceInfo, method: BypassMethod) -> Dict[str, Any]:
        """Execute system-level bypass methods"""
        if method.name == "accounts_db_modification":
            return self.system_exploits.modify_accounts_database(device, self._update_progress)
        elif method.name == "persist_partition_edit":
            return self.system_exploits.edit_persist_partition(device, self._update_progress)
        else:
            return {'result': BypassResult.FAILED, 'message': f'Unknown system method: {method.name}', 'details': {}}
    
    def _execute_hardware_bypass(self, device: DeviceInfo, method: BypassMethod) -> Dict[str, Any]:
        """Execute hardware-based bypass methods"""
        if method.name == "download_mode_flash":
            return self.hardware_exploits.download_mode_flash(device, self._update_progress)
        elif method.name == "qualcomm_edl_exploit":
            return self.hardware_exploits.qualcomm_edl_exploit(device, self._update_progress)
        else:
            return {'result': BypassResult.FAILED, 'message': f'Unknown hardware method: {method.name}', 'details': {}}
    
    def _verify_bypass_success(self, device: DeviceInfo) -> bool:
        """Verify that the bypass was successful"""
        try:
            # Refresh device info
            updated_device = self.device_manager.refresh_device_info(device.serial)
            if not updated_device:
                return False
            
            # Check FRP status
            if updated_device.frp_status in ['disabled', 'setup_complete']:
                return True
            
            # Additional checks
            success, output = self.device_manager.execute_adb_command(
                device.serial, ['shell', 'settings', 'get', 'secure', 'user_setup_complete']
            )
            
            if success and output.strip() == '1':
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Error verifying bypass success: {e}")
            return False
    
    def _update_progress(self, message: str, percentage: int):
        """Update progress callback"""
        if self.progress_callback:
            self.progress_callback(message, percentage)
        self.logger.info(f"Progress: {percentage}% - {message}")
    
    def get_method_info(self, method_name: str) -> Optional[BypassMethod]:
        """Get information about a specific method"""
        return next((m for m in self.available_methods if m.name == method_name), None)
    
    def estimate_bypass_time(self, device: DeviceInfo, method_name: str) -> int:
        """Estimate bypass time for a specific method and device"""
        method = self.get_method_info(method_name)
        if not method:
            return 0
        
        base_time = method.estimated_time
        
        # Adjust based on device characteristics
        if device.android_version.startswith('5.'):
            base_time *= 0.8  # Older Android versions are often easier
        elif device.android_version.startswith(('10.', '11.', '12.')):
            base_time *= 1.3  # Newer versions have more protections
        
        # Adjust based on manufacturer
        if device.manufacturer.lower() == 'samsung':
            base_time *= 1.1  # Samsung has additional protections
        elif device.manufacturer.lower() == 'google':
            base_time *= 1.2  # Pixel devices have strong security
        
        return int(base_time)
    
    def get_ai_device_analysis(self, device: DeviceInfo) -> Dict[str, Any]:
        """Get comprehensive AI analysis of device"""
        profile = self.ai_engine.analyze_device(device)
        
        result = {
            'device_profile': {
                'frp_complexity': profile.frp_complexity,
                'vulnerability_score': profile.vulnerability_score,
                'recommended_methods': profile.recommended_methods,
                'success_probabilities': profile.success_probability
            },
            'security_assessment': self._get_security_assessment_text(profile.vulnerability_score),
            'bypass_strategy': self._get_bypass_strategy(profile)
        }
        
        # Send notification about analysis completion
        if self.notification_system:
            self.notification_system.notify_device_analysis_complete(
                profile.vulnerability_score,
                profile.recommended_methods
            )
        
        return result
    
    def _get_security_assessment_text(self, vulnerability_score: float) -> str:
        """Convert vulnerability score to human-readable assessment"""
        if vulnerability_score > 0.7:
            return "High vulnerability detected - Multiple bypass methods likely to succeed"
        elif vulnerability_score > 0.4:
            return "Medium vulnerability - Some methods may work with proper execution"
        else:
            return "Low vulnerability - Limited bypass options, advanced techniques may be required"
    
    def _get_bypass_strategy(self, profile: DeviceProfile) -> str:
        """Generate AI-driven bypass strategy"""
        if profile.frp_complexity == 'low':
            return "Start with ADB-based methods, then try interface exploits"
        elif profile.frp_complexity == 'medium':
            return "Combine multiple methods, focus on device-specific exploits"
        elif profile.frp_complexity == 'high':
            return "Use advanced techniques, consider hardware-based methods"
        else:
            return "Extreme security - Hardware exploits or professional tools may be required"
    
    def get_contextual_help(self, device: DeviceInfo, method_name: str) -> Dict[str, Any]:
        """Get AI-powered contextual help for a specific method"""
        return self.ai_engine.get_contextual_help(device, method_name)
    
    def set_notification_system(self, notification_system):
        """Set the notification system for AI insights"""
        self.notification_system = notification_system
    
    def get_ai_insights(self) -> Dict[str, Any]:
        """Get AI learning insights and performance statistics"""
        insights = self.ai_engine.get_learning_insights()
        
        # Send notification if system is available
        if self.notification_system and insights.get('new_insights'):
            learning_status = insights.get('learning_status', 'Unknown')
            success_rate = insights.get('overall_success_rate', 0.0)
            self.notification_system.notify_learning_update(
                f"AI Learning Status: {learning_status}. Overall success rate: {success_rate:.1%}"
            )
        
        return insights
    
    def suggest_next_method(self, device: DeviceInfo, failed_methods: List[str]) -> Optional[BypassMethod]:
        """AI-powered suggestion for next method to try after failures"""
        profile = self.ai_engine.analyze_device(device)
        
        # Get methods not yet tried
        available_methods = [m for m in profile.recommended_methods if m not in failed_methods]
        
        if not available_methods:
            # Fall back to other compatible methods
            compatible = self.get_recommended_methods(device)
            available_methods = [m.name for m in compatible if m.name not in failed_methods]
        
        if available_methods:
            # Return method with highest success probability
            best_method_name = max(available_methods, 
                                 key=lambda m: profile.success_probability.get(m, 0.0))
            return self.get_method_info(best_method_name)
        
        return None