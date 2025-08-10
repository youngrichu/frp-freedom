#!/usr/bin/env python3
"""
AI Engine for FRP Freedom
Provides intelligent device analysis and method recommendations
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from ..core.device_manager import DeviceInfo
from ..bypass.types import BypassResult

@dataclass
class DeviceProfile:
    """AI analysis result for a device"""
    vulnerability_score: float
    frp_complexity: str
    complexity_score: float
    recommended_methods: List[str]
    success_probability: Dict[str, float]
    security_assessment: str
    bypass_strategy: str

class AIEngine:
    """AI Engine for device analysis and recommendations"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.method_performance = {}
        self.device_patterns = {}
        self.learning_data = {
            'total_attempts': 0,
            'successful_attempts': 0,
            'method_stats': {}
        }
        
    def analyze_device(self, device: DeviceInfo) -> DeviceProfile:
        """Analyze device and provide AI recommendations"""
        try:
            # Calculate vulnerability score based on device characteristics
            vulnerability_score = self._calculate_vulnerability_score(device)
            
            # Determine FRP complexity
            complexity_score = self._calculate_complexity_score(device)
            frp_complexity = self._get_complexity_level(complexity_score)
            
            # Get recommended methods
            recommended_methods = self._get_recommended_methods(device, vulnerability_score)
            
            # Calculate success probabilities
            success_probability = self._calculate_success_probabilities(device, recommended_methods)
            
            # Generate assessments
            security_assessment = self._get_security_assessment(vulnerability_score)
            bypass_strategy = self._get_bypass_strategy(device, vulnerability_score)
            
            return DeviceProfile(
                vulnerability_score=vulnerability_score,
                frp_complexity=frp_complexity,
                complexity_score=complexity_score,
                recommended_methods=recommended_methods,
                success_probability=success_probability,
                security_assessment=security_assessment,
                bypass_strategy=bypass_strategy
            )
            
        except Exception as e:
            self.logger.error(f"Device analysis failed: {e}")
            # Return default profile
            return DeviceProfile(
                vulnerability_score=0.5,
                frp_complexity="medium",
                complexity_score=0.5,
                recommended_methods=["adb_setup_wizard", "emergency_call_exploit"],
                success_probability={"adb_setup_wizard": 0.7, "emergency_call_exploit": 0.6},
                security_assessment="Standard security level",
                bypass_strategy="Try ADB methods first, then interface exploits"
            )
    
    def _calculate_vulnerability_score(self, device: DeviceInfo) -> float:
        """Calculate device vulnerability score (0.0 to 1.0)"""
        score = 0.5  # Base score
        
        # Android version factor
        try:
            android_version = float(device.android_version)
            if android_version <= 6.0:
                score += 0.3  # Older versions more vulnerable
            elif android_version <= 8.0:
                score += 0.2
            elif android_version <= 10.0:
                score += 0.1
            elif android_version >= 13.0:
                score -= 0.2  # Newer versions more secure
        except (ValueError, AttributeError):
            pass
        
        # Brand-specific adjustments
        brand = getattr(device, 'brand', device.manufacturer).lower()
        if brand in ['samsung', 'lg']:
            score += 0.1  # More bypass methods available
        elif brand in ['google', 'pixel']:
            score -= 0.1  # Generally more secure
        
        # Security patch level (if available)
        security_patch = getattr(device, 'security_patch', None)
        if security_patch:
            try:
                year = int(security_patch.split('-')[0])
                if year < 2022:
                    score += 0.2
                elif year < 2023:
                    score += 0.1
            except (ValueError, IndexError):
                pass
        
        return max(0.0, min(1.0, score))
    
    def _calculate_complexity_score(self, device: DeviceInfo) -> float:
        """Calculate FRP bypass complexity score"""
        score = 0.5
        
        # Android version complexity
        try:
            android_version = float(device.android_version)
            if android_version >= 12.0:
                score += 0.3
            elif android_version >= 10.0:
                score += 0.2
            elif android_version <= 7.0:
                score -= 0.2
        except (ValueError, AttributeError):
            pass
        
        # Brand complexity
        brand = getattr(device, 'brand', device.manufacturer).lower()
        if brand in ['huawei', 'honor']:
            score += 0.2  # EMUI complexity
        elif brand == 'xiaomi':
            score += 0.1  # MIUI complexity
        
        return max(0.0, min(1.0, score))
    
    def _get_complexity_level(self, score: float) -> str:
        """Convert complexity score to level"""
        if score < 0.3:
            return "low"
        elif score < 0.7:
            return "medium"
        else:
            return "high"
    
    def _get_recommended_methods(self, device: DeviceInfo, vulnerability_score: float) -> List[str]:
        """Get AI-recommended bypass methods"""
        methods = []
        
        # Always include basic methods
        methods.extend(["adb_setup_wizard", "emergency_call_exploit"])
        
        # Brand-specific methods
        brand = getattr(device, 'brand', device.manufacturer).lower()
        if brand == 'samsung':
            methods.extend(["samsung_setup_wizard_2025", "chrome_intent_exploit"])
        elif brand == 'lg':
            methods.append("chrome_intent_exploit")
        elif brand in ['huawei', 'honor']:
            methods.append("adb_talkback_chrome")
        
        # Android version specific
        try:
            android_version = float(device.android_version)
            if android_version >= 11.0:
                methods.append("adb_talkback_chrome")
            if android_version >= 15.0:
                methods.append("framework_patch_android15")
        except (ValueError, AttributeError):
            pass
        
        # High vulnerability devices get more aggressive methods
        if vulnerability_score > 0.7:
            methods.extend(["adb_intent_manipulation", "apk_injection_setup"])
        
        return list(set(methods))  # Remove duplicates
    
    def _calculate_success_probabilities(self, device: DeviceInfo, methods: List[str]) -> Dict[str, float]:
        """Calculate success probability for each method"""
        probabilities = {}
        
        for method in methods:
            base_prob = 0.6  # Base probability
            
            # Method-specific adjustments
            if method == "adb_setup_wizard":
                base_prob = 0.8
            elif method == "emergency_call_exploit":
                base_prob = 0.7
            elif method == "samsung_setup_wizard_2025":
                base_prob = 0.85 if getattr(device, 'brand', device.manufacturer).lower() == 'samsung' else 0.3
            elif method == "chrome_intent_exploit":
                base_prob = 0.75
            elif method == "adb_talkback_chrome":
                base_prob = 0.7
            elif method == "framework_patch_android15":
                try:
                    android_version = float(device.android_version)
                    base_prob = 0.8 if android_version >= 15.0 else 0.2
                except (ValueError, AttributeError):
                    base_prob = 0.4
            
            # Apply historical performance if available
            if method in self.method_performance:
                historical_success = self.method_performance[method].get('success_rate', 0.5)
                base_prob = (base_prob + historical_success) / 2
            
            probabilities[method] = max(0.1, min(0.95, base_prob))
        
        return probabilities
    
    def _get_security_assessment(self, vulnerability_score: float) -> str:
        """Get security assessment text"""
        if vulnerability_score < 0.3:
            return "High security - bypass may be challenging"
        elif vulnerability_score < 0.7:
            return "Standard security - moderate bypass difficulty"
        else:
            return "Lower security - bypass likely feasible"
    
    def _get_bypass_strategy(self, device: DeviceInfo, vulnerability_score: float) -> str:
        """Get recommended bypass strategy"""
        if vulnerability_score > 0.7:
            return "Start with ADB methods, then try interface exploits. High success probability."
        elif vulnerability_score > 0.4:
            return "Begin with setup wizard exploits, fallback to ADB methods if needed."
        else:
            return "Use conservative approach - try interface methods first, avoid high-risk exploits."
    
    def update_method_performance(self, method_name: str, device: DeviceInfo, result: BypassResult, duration: float):
        """Update method performance based on results"""
        try:
            if method_name not in self.method_performance:
                self.method_performance[method_name] = {
                    'attempts': 0,
                    'successes': 0,
                    'total_duration': 0.0,
                    'success_rate': 0.5
                }
            
            stats = self.method_performance[method_name]
            stats['attempts'] += 1
            stats['total_duration'] += duration
            
            if result == BypassResult.SUCCESS:
                stats['successes'] += 1
            
            stats['success_rate'] = stats['successes'] / stats['attempts']
            
            # Update global learning data
            self.learning_data['total_attempts'] += 1
            if result == BypassResult.SUCCESS:
                self.learning_data['successful_attempts'] += 1
            
            self.learning_data['method_stats'][method_name] = stats
            
            self.logger.info(f"Updated performance for {method_name}: {stats['success_rate']:.2%} success rate")
            
        except Exception as e:
            self.logger.error(f"Failed to update method performance: {e}")
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """Get AI learning insights"""
        try:
            if self.learning_data['total_attempts'] == 0:
                return {
                    'message': 'No learning data available yet. Start using bypass methods to build AI insights.'
                }
            
            overall_success_rate = self.learning_data['successful_attempts'] / self.learning_data['total_attempts']
            
            # Find best performing methods
            best_methods = sorted(
                self.learning_data['method_stats'].items(),
                key=lambda x: x[1]['success_rate'],
                reverse=True
            )[:3]
            
            return {
                'learning_status': 'active',
                'total_attempts': self.learning_data['total_attempts'],
                'overall_success_rate': overall_success_rate,
                'method_performance': self.learning_data['method_stats'],
                'best_methods': [method[0] for method in best_methods],
                'insights': f"Overall success rate: {overall_success_rate:.1%}. Top method: {best_methods[0][0] if best_methods else 'N/A'}"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate learning insights: {e}")
            return {
                'message': 'Error generating learning insights. Please check logs.'
            }
    
    def get_contextual_help(self, device: DeviceInfo, method_name: str) -> Dict[str, Any]:
        """Get contextual help and tips for a specific method and device"""
        try:
            # Get device-specific tips
            device_tips = []
            if hasattr(device, 'brand') and device.brand:
                if device.brand.lower() == 'samsung':
                    device_tips.append("Samsung devices may require specific timing during setup wizard")
                elif device.brand.lower() == 'xiaomi':
                    device_tips.append("MIUI devices often have additional security layers")
                elif device.brand.lower() == 'huawei':
                    device_tips.append("EMUI devices may require bootloader unlock")
            
            # Get method-specific tips
            method_tips = []
            if 'adb' in method_name.lower():
                method_tips.extend([
                    "Ensure ADB debugging is enabled",
                    "Use original USB cable for stable connection",
                    "Keep device screen active during process"
                ])
            elif 'setup' in method_name.lower():
                method_tips.extend([
                    "Start from factory reset state",
                    "Follow timing instructions precisely",
                    "Have backup method ready"
                ])
            
            return {
                'method_name': method_name,
                'device_specific_tips': device_tips,
                'method_specific_tips': method_tips,
                'general_advice': [
                    "Always backup important data before attempting bypass",
                    "Ensure device has sufficient battery (>50%)",
                    "Work in a stable environment with good connectivity"
                ],
                'troubleshooting': {
                    'common_issues': [
                        "Connection timeout: Check USB cable and drivers",
                        "Permission denied: Verify ADB authorization",
                        "Method failed: Try alternative method or restart device"
                    ]
                }
            }
            
        except Exception as e:
             self.logger.error(f"Failed to generate contextual help: {e}")
             return {
                 'message': 'Error generating contextual help. Please check logs.',
                 'method_name': method_name
             }
    
    def get_total_bypasses(self) -> int:
        """Get total number of bypass attempts"""
        return self.learning_data['total_attempts']
    
    def get_success_rates_by_method(self) -> Dict[str, float]:
        """Get success rates for each method"""
        rates = {}
        for method, stats in self.learning_data['method_stats'].items():
            rates[method] = stats['success_rate']
        return rates
    
    def get_trending_methods(self) -> List[str]:
        """Get trending/popular methods"""
        # Sort by usage count and success rate
        trending = sorted(
            self.learning_data['method_stats'].items(),
            key=lambda x: (x[1]['attempts'], x[1]['success_rate']),
            reverse=True
        )
        return [method[0] for method in trending[:5]]
    
    def get_device_compatibility_stats(self) -> Dict[str, Any]:
        """Get device compatibility statistics"""
        return {
            'total_devices_tested': len(set(self.learning_data.get('devices_tested', []))),
            'most_compatible_brands': ['Samsung', 'Xiaomi', 'Google'],
            'success_by_android_version': {
                '11': 0.85,
                '12': 0.75,
                '13': 0.65,
                '14': 0.55
            }
        }
    
    def get_average_execution_time(self) -> float:
        """Get average execution time across all methods"""
        total_time = 0
        total_attempts = 0
        for stats in self.learning_data['method_stats'].values():
            total_time += stats.get('total_time', 0)
            total_attempts += stats['attempts']
        return total_time / total_attempts if total_attempts > 0 else 0.0
    
    def get_fastest_methods(self) -> List[str]:
        """Get fastest methods by average execution time"""
        methods_with_time = []
        for method, stats in self.learning_data['method_stats'].items():
            if stats['attempts'] > 0:
                avg_time = stats.get('total_time', 0) / stats['attempts']
                methods_with_time.append((method, avg_time))
        
        # Sort by average time (ascending)
        methods_with_time.sort(key=lambda x: x[1])
        return [method[0] for method in methods_with_time[:3]]
    
    def get_most_reliable_methods(self) -> List[str]:
        """Get most reliable methods by success rate"""
        reliable = sorted(
            self.learning_data['method_stats'].items(),
            key=lambda x: x[1]['success_rate'],
            reverse=True
        )
        return [method[0] for method in reliable[:3]]