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
        
        return recommended
    
    def _is_method_compatible(self, method: BypassMethod, device: DeviceInfo) -> bool:
        """Check if a method is compatible with the device"""
        # Handle unauthorized devices (FRP bypass scenarios)
        if device.connection_type == 'adb_unauthorized':
            # For unauthorized devices, only allow interface-based methods
            # Skip ADB methods since device is not authorized
            if method.category == 'adb':
                return False
            # Prioritize interface methods for FRP bypass
            if method.category not in ['interface', 'system']:
                return False
        
        # Handle restricted devices (FRP lock, Test Mode, etc.)
        if device.connection_type == 'adb_restricted':
            # Device is connected but shell access is blocked
            # Only allow interface methods that don't require shell access
            if method.category == 'adb':
                return False  # ADB methods need shell access
            # Allow interface and some system methods
            if method.category not in ['interface', 'system']:
                return False
        
        # Check manufacturer (skip for unknown devices)
        if device.manufacturer != "Unknown" and device.manufacturer.lower() not in [d.lower() for d in method.supported_devices]:
            return False
        
        # Check Android version (skip for unknown versions OR restricted devices)
        # For restricted devices, we can't determine Android version, so allow all methods
        if device.android_version != "Unknown" and device.connection_type not in ['adb_restricted', 'adb_unauthorized']:
            device_version = device.android_version
            if device_version not in method.android_versions:
                # Try to match major version
                device_major = device_version.split('.')[0] if '.' in device_version else device_version
                method_majors = [v.split('.')[0] for v in method.android_versions]
                if device_major not in method_majors:
                    return False
        
        # Check connection type requirements for normal devices
        if device.connection_type not in ['adb_unauthorized', 'adb_restricted']:
            if method.category == 'adb' and device.connection_type not in ['adb']:
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
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Bypass method '{method_name}' failed with error: {e}")
            
            # Update AI with failure
            self.ai_engine.update_method_performance(method_name, device, BypassResult.FAILED, execution_time)
            
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
        return self.adb_exploits.execute_method(device, method, self.progress_callback)
    
    def _execute_interface_bypass(self, device: DeviceInfo, method: BypassMethod) -> Dict[str, Any]:
        """Execute interface-based bypass methods"""
        return self.interface_exploits.execute_method(device, method, self.progress_callback)
    
    def _execute_system_bypass(self, device: DeviceInfo, method: BypassMethod) -> Dict[str, Any]:
        """Execute system-level bypass methods"""
        return self.system_exploits.execute_method(device, method, self.progress_callback)
    
    def _execute_hardware_bypass(self, device: DeviceInfo, method: BypassMethod) -> Dict[str, Any]:
        """Execute hardware-level bypass methods"""
        return self.hardware_exploits.execute_method(device, method, self.progress_callback)
    
    def _verify_bypass_success(self, device: DeviceInfo) -> bool:
        """Verify that the bypass was successful"""
        try:
            # Check if we can access the device without FRP restrictions
            success, output = self.device_manager.execute_adb_command(
                device.serial, 
                ['shell', 'getprop', 'ro.frp.pst']
            )
            
            if success:
                # If FRP property is empty or not set, bypass likely successful
                if not output.strip() or output.strip() == '':
                    return True
                    
            # Additional checks for specific bypass indicators
            success, output = self.device_manager.execute_adb_command(
                device.serial,
                ['shell', 'pm', 'list', 'users']
            )
            
            if success and 'UserInfo{0:' in output:
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error verifying bypass success: {e}")
            return False
    
    def _update_progress(self, message: str, percentage: int):
        """Update progress callback if available"""
        if self.progress_callback:
            self.progress_callback(message, percentage)
    
    def get_method_info(self, method_name: str) -> Optional[BypassMethod]:
        """Get detailed information about a specific method"""
        return next((m for m in self.available_methods if m.name == method_name), None)
    
    def estimate_bypass_time(self, device: DeviceInfo, method_name: str) -> int:
        """Estimate bypass time using AI analysis"""
        method = self.get_method_info(method_name)
        if not method:
            return 0
        
        # Get AI analysis for more accurate time estimation
        device_profile = self.ai_engine.analyze_device(device)
        
        # Base time from method definition
        base_time = method.estimated_time
        
        # Adjust based on AI analysis
        complexity_factor = device_profile.complexity_score
        if complexity_factor > 0.8:
            base_time = int(base_time * 1.5)  # 50% longer for complex devices
        elif complexity_factor < 0.3:
            base_time = int(base_time * 0.8)  # 20% faster for simple devices
        
        # Factor in success probability (lower success = potentially longer time)
        success_prob = device_profile.success_probability.get(method_name, 0.5)
        if success_prob < 0.5:
            base_time = int(base_time * 1.3)  # 30% longer for uncertain methods
        
        return max(base_time, 1)  # Minimum 1 minute
    
    def get_ai_device_analysis(self, device: DeviceInfo) -> Dict[str, Any]:
        """Get comprehensive AI analysis of the device"""
        device_profile = self.ai_engine.analyze_device(device)
        
        return {
            'device_info': {
                'brand': device.brand,
                'model': device.model,
                'android_version': device.android_version,
                'security_patch': device.security_patch
            },
            'ai_analysis': {
                'complexity_score': device_profile.complexity_score,
                'vulnerability_score': device_profile.vulnerability_score,
                'recommended_methods': device_profile.recommended_methods,
                'success_probabilities': device_profile.success_probability,
                'security_assessment': self._get_security_assessment_text(device_profile.vulnerability_score),
                'bypass_strategy': self._get_bypass_strategy(device_profile)
            }
        }
    
    def _get_security_assessment_text(self, vulnerability_score: float) -> str:
        """Convert vulnerability score to human-readable assessment"""
        if vulnerability_score >= 0.8:
            return "High vulnerability - Multiple bypass vectors available"
        elif vulnerability_score >= 0.6:
            return "Moderate vulnerability - Several bypass options possible"
        elif vulnerability_score >= 0.4:
            return "Low vulnerability - Limited bypass methods may work"
        else:
            return "Very low vulnerability - Bypass may be challenging"
    
    def _get_bypass_strategy(self, profile: DeviceProfile) -> str:
        """Generate bypass strategy recommendation"""
        if profile.complexity_score < 0.3:
            return "Start with interface-based methods, then try ADB exploits"
        elif profile.complexity_score < 0.7:
            return "Begin with ADB methods, fallback to system-level approaches"
        else:
            return "Consider hardware-level methods or advanced system exploits"
    
    def get_contextual_help(self, device: DeviceInfo, method_name: str) -> Dict[str, Any]:
        """Get contextual help and tips for a specific method and device"""
        return self.ai_engine.get_contextual_help(device, method_name)
    
    def set_notification_system(self, notification_system):
        """Set the notification system for bypass insights"""
        self.notification_system = notification_system
    
    def get_ai_insights(self) -> Dict[str, Any]:
        """Get AI insights about bypass performance and trends"""
        return {
            'total_bypasses': self.ai_engine.get_total_bypasses(),
            'success_rate_by_method': self.ai_engine.get_success_rates_by_method(),
            'trending_methods': self.ai_engine.get_trending_methods(),
            'device_compatibility': self.ai_engine.get_device_compatibility_stats(),
            'performance_metrics': {
                'average_execution_time': self.ai_engine.get_average_execution_time(),
                'fastest_methods': self.ai_engine.get_fastest_methods(),
                'most_reliable_methods': self.ai_engine.get_most_reliable_methods()
            }
        }
    
    def suggest_next_method(self, device: DeviceInfo, failed_methods: List[str]) -> Optional[BypassMethod]:
        """Suggest the next best method after failures"""
        available_methods = self.get_recommended_methods(device)
        
        # Filter out failed methods
        remaining_methods = [m for m in available_methods if m.name not in failed_methods]
        
        if remaining_methods:
            return remaining_methods[0]  # Return the top recommended method
        
        return None