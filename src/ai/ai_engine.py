#!/usr/bin/env python3
"""
AI Engine for FRP Freedom
Provides intelligent device detection, method adaptation, and contextual assistance
"""

import logging
import json
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from ..core.device_manager import DeviceInfo
from ..bypass.types import BypassMethod, BypassResult

@dataclass
class DeviceProfile:
    """Enhanced device profile with AI insights"""
    device_id: str
    brand: str
    model: str
    android_version: str
    security_patch: str
    bootloader_status: str
    frp_complexity: str  # 'low', 'medium', 'high', 'extreme'
    vulnerability_score: float  # 0.0 to 1.0
    recommended_methods: List[str]
    success_probability: Dict[str, float]
    last_updated: datetime
    
@dataclass
class MethodPerformance:
    """Track method performance across devices"""
    method_name: str
    device_signature: str
    success_count: int
    failure_count: int
    average_time: float
    last_success: Optional[datetime]
    risk_factors: List[str]
    
class AIEngine:
    """AI-driven intelligence for FRP bypass operations"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # AI knowledge base
        self.device_profiles: Dict[str, DeviceProfile] = {}
        self.method_performance: Dict[str, MethodPerformance] = {}
        self.vulnerability_patterns: Dict[str, List[str]] = {}
        self.success_history: List[Dict[str, Any]] = []
        
        # Load existing knowledge
        self._load_knowledge_base()
        
        # Initialize vulnerability patterns
        self._initialize_vulnerability_patterns()
    
    def _load_knowledge_base(self):
        """Load existing AI knowledge from storage"""
        try:
            # In a real implementation, this would load from a database or file
            # For now, we'll initialize with some baseline knowledge
            self._initialize_baseline_knowledge()
        except Exception as e:
            self.logger.warning(f"Could not load AI knowledge base: {e}")
            self._initialize_baseline_knowledge()
    
    def _initialize_baseline_knowledge(self):
        """Initialize baseline AI knowledge"""
        # Samsung device patterns
        self.vulnerability_patterns['samsung'] = [
            'setup_wizard_exploit',
            'talkback_chrome_2025',
            'emergency_call_interface',
            'adb_intent_manipulation'
        ]
        
        # Google Pixel patterns
        self.vulnerability_patterns['google'] = [
            'adb_setup_wizard',
            'chrome_intent_exploit',
            'framework_patch_android15'
        ]
        
        # Xiaomi patterns
        self.vulnerability_patterns['xiaomi'] = [
            'adb_intent_manipulation',
            'persist_partition_edit',
            'emergency_call_exploit'
        ]
    
    def _initialize_vulnerability_patterns(self):
        """Initialize known vulnerability patterns by Android version"""
        self.android_vulnerabilities = {
            '15.0': {
                'high_success': ['talkback_chrome_2025', 'framework_patch_android15'],
                'medium_success': ['adb_intent_manipulation', 'chrome_intent_exploit'],
                'patched': ['adb_setup_wizard', 'emergency_call_exploit']
            },
            '14.0': {
                'high_success': ['talkback_chrome_2025', 'adb_intent_manipulation'],
                'medium_success': ['samsung_setup_wizard_2025', 'chrome_intent_exploit'],
                'patched': ['adb_talkback_legacy']
            },
            '13.0': {
                'high_success': ['adb_intent_manipulation', 'samsung_setup_wizard_2025'],
                'medium_success': ['chrome_intent_exploit', 'emergency_call_exploit'],
                'patched': ['adb_setup_wizard']
            }
        }
    
    def analyze_device(self, device: DeviceInfo) -> DeviceProfile:
        """Perform AI-driven device analysis"""
        device_id = self._generate_device_id(device)
        
        # Check if we have existing profile
        if device_id in self.device_profiles:
            profile = self.device_profiles[device_id]
            # Update if profile is old (>7 days)
            if datetime.now() - profile.last_updated > timedelta(days=7):
                profile = self._create_device_profile(device, device_id)
        else:
            profile = self._create_device_profile(device, device_id)
        
        self.device_profiles[device_id] = profile
        return profile
    
    def _generate_device_id(self, device: DeviceInfo) -> str:
        """Generate unique device identifier"""
        device_string = f"{device.brand}_{device.model}_{device.android_version}_{device.security_patch}"
        return hashlib.md5(device_string.encode()).hexdigest()[:16]
    
    def _create_device_profile(self, device: DeviceInfo, device_id: str) -> DeviceProfile:
        """Create comprehensive device profile with AI analysis"""
        # Analyze FRP complexity
        frp_complexity = self._analyze_frp_complexity(device)
        
        # Calculate vulnerability score
        vulnerability_score = self._calculate_vulnerability_score(device)
        
        # Get AI-recommended methods
        recommended_methods = self._get_ai_recommendations(device)
        
        # Calculate success probabilities
        success_probability = self._calculate_success_probabilities(device, recommended_methods)
        
        return DeviceProfile(
            device_id=device_id,
            brand=device.brand or 'Unknown',
            model=device.model or 'Unknown',
            android_version=device.android_version or 'Unknown',
            security_patch=device.security_patch or 'Unknown',
            bootloader_status=device.bootloader_status or 'Unknown',
            frp_complexity=frp_complexity,
            vulnerability_score=vulnerability_score,
            recommended_methods=recommended_methods,
            success_probability=success_probability,
            last_updated=datetime.now()
        )
    
    def _analyze_frp_complexity(self, device: DeviceInfo) -> str:
        """Analyze FRP bypass complexity using AI heuristics"""
        complexity_score = 0
        
        # Android version factor
        if device.android_version:
            version_major = float(device.android_version.split('.')[0])
            if version_major >= 15:
                complexity_score += 3
            elif version_major >= 13:
                complexity_score += 2
            elif version_major >= 11:
                complexity_score += 1
        
        # Security patch factor
        if device.security_patch:
            try:
                patch_date = datetime.strptime(device.security_patch, '%Y-%m-%d')
                months_old = (datetime.now() - patch_date).days / 30
                if months_old < 3:
                    complexity_score += 2
                elif months_old < 6:
                    complexity_score += 1
            except:
                pass
        
        # Brand-specific factors
        brand_complexity = {
            'samsung': 1,
            'google': 2,
            'xiaomi': 1,
            'huawei': 2,
            'oneplus': 1
        }
        complexity_score += brand_complexity.get(device.brand.lower() if device.brand else '', 1)
        
        # Bootloader status
        if device.bootloader_status and 'locked' in device.bootloader_status.lower():
            complexity_score += 1
        
        # Map score to complexity level
        if complexity_score <= 2:
            return 'low'
        elif complexity_score <= 4:
            return 'medium'
        elif complexity_score <= 6:
            return 'high'
        else:
            return 'extreme'
    
    def _calculate_vulnerability_score(self, device: DeviceInfo) -> float:
        """Calculate device vulnerability score (0.0 = secure, 1.0 = vulnerable)"""
        score = 0.5  # Base score
        
        # Android version vulnerabilities
        if device.android_version:
            version = device.android_version
            if version in self.android_vulnerabilities:
                vuln_data = self.android_vulnerabilities[version]
                high_success_count = len(vuln_data.get('high_success', []))
                patched_count = len(vuln_data.get('patched', []))
                
                # More high-success methods = higher vulnerability
                score += (high_success_count * 0.1)
                # More patched methods = lower vulnerability
                score -= (patched_count * 0.05)
        
        # Brand-specific adjustments
        brand_vulnerability = {
            'samsung': 0.1,   # Generally more vulnerable
            'xiaomi': 0.05,
            'google': -0.1,   # Generally more secure
            'huawei': -0.05
        }
        score += brand_vulnerability.get(device.brand.lower() if device.brand else '', 0)
        
        # Security patch age
        if device.security_patch:
            try:
                patch_date = datetime.strptime(device.security_patch, '%Y-%m-%d')
                months_old = (datetime.now() - patch_date).days / 30
                # Older patches = higher vulnerability
                score += min(months_old * 0.02, 0.2)
            except:
                score += 0.1  # Unknown patch date = slight vulnerability increase
        
        return max(0.0, min(1.0, score))
    
    def _get_ai_recommendations(self, device: DeviceInfo) -> List[str]:
        """Get AI-driven method recommendations"""
        recommendations = []
        
        # Brand-specific recommendations
        brand_key = device.brand.lower() if device.brand else 'unknown'
        if brand_key in self.vulnerability_patterns:
            recommendations.extend(self.vulnerability_patterns[brand_key])
        
        # Android version-specific recommendations
        if device.android_version and device.android_version in self.android_vulnerabilities:
            vuln_data = self.android_vulnerabilities[device.android_version]
            recommendations.extend(vuln_data.get('high_success', []))
            recommendations.extend(vuln_data.get('medium_success', []))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for method in recommendations:
            if method not in seen:
                seen.add(method)
                unique_recommendations.append(method)
        
        return unique_recommendations[:5]  # Top 5 recommendations
    
    def _calculate_success_probabilities(self, device: DeviceInfo, methods: List[str]) -> Dict[str, float]:
        """Calculate success probability for each method"""
        probabilities = {}
        
        for method in methods:
            base_probability = 0.5
            
            # Check historical performance
            device_signature = f"{device.brand}_{device.model}_{device.android_version}"
            perf_key = f"{method}_{device_signature}"
            
            if perf_key in self.method_performance:
                perf = self.method_performance[perf_key]
                total_attempts = perf.success_count + perf.failure_count
                if total_attempts > 0:
                    base_probability = perf.success_count / total_attempts
            
            # Adjust based on device vulnerability score
            vulnerability_score = self._calculate_vulnerability_score(device)
            adjusted_probability = base_probability * (0.5 + vulnerability_score * 0.5)
            
            # Android version adjustments
            if device.android_version and device.android_version in self.android_vulnerabilities:
                vuln_data = self.android_vulnerabilities[device.android_version]
                if method in vuln_data.get('high_success', []):
                    adjusted_probability *= 1.2
                elif method in vuln_data.get('patched', []):
                    adjusted_probability *= 0.3
            
            probabilities[method] = max(0.1, min(0.95, adjusted_probability))
        
        return probabilities
    
    def update_method_performance(self, method_name: str, device: DeviceInfo, 
                                 result: BypassResult, execution_time: float):
        """Update method performance based on execution results"""
        device_signature = f"{device.brand}_{device.model}_{device.android_version}"
        perf_key = f"{method_name}_{device_signature}"
        
        if perf_key not in self.method_performance:
            self.method_performance[perf_key] = MethodPerformance(
                method_name=method_name,
                device_signature=device_signature,
                success_count=0,
                failure_count=0,
                average_time=0.0,
                last_success=None,
                risk_factors=[]
            )
        
        perf = self.method_performance[perf_key]
        
        # Update counts
        if result == BypassResult.SUCCESS:
            perf.success_count += 1
            perf.last_success = datetime.now()
        else:
            perf.failure_count += 1
        
        # Update average time
        total_attempts = perf.success_count + perf.failure_count
        perf.average_time = ((perf.average_time * (total_attempts - 1)) + execution_time) / total_attempts
        
        # Record in success history
        self.success_history.append({
            'timestamp': datetime.now().isoformat(),
            'method': method_name,
            'device_signature': device_signature,
            'result': result.value,
            'execution_time': execution_time
        })
    
    def get_contextual_help(self, device: DeviceInfo, method_name: str) -> Dict[str, Any]:
        """Provide contextual help and guidance"""
        profile = self.analyze_device(device)
        
        help_data = {
            'device_analysis': {
                'frp_complexity': profile.frp_complexity,
                'vulnerability_score': profile.vulnerability_score,
                'security_assessment': self._get_security_assessment(profile)
            },
            'method_guidance': self._get_method_guidance(method_name, device),
            'prerequisites': self._get_method_prerequisites(method_name, device),
            'troubleshooting': self._get_troubleshooting_tips(method_name, device),
            'alternatives': self._get_alternative_methods(device, method_name),
            'success_probability': profile.success_probability.get(method_name, 0.5)
        }
        
        return help_data
    
    def _get_security_assessment(self, profile: DeviceProfile) -> str:
        """Generate security assessment text"""
        if profile.vulnerability_score > 0.7:
            return "High vulnerability - Multiple bypass methods likely to succeed"
        elif profile.vulnerability_score > 0.4:
            return "Medium vulnerability - Some methods may work with proper execution"
        else:
            return "Low vulnerability - Limited bypass options, may require advanced techniques"
    
    def _get_method_guidance(self, method_name: str, device: DeviceInfo) -> List[str]:
        """Get method-specific guidance"""
        guidance = {
            'adb_setup_wizard': [
                "Ensure device is in setup wizard state",
                "USB debugging must be enabled during setup",
                "Have ADB drivers installed on computer"
            ],
            'talkback_chrome_2025': [
                "Enable TalkBack accessibility service",
                "Chrome browser must be available",
                "Voice commands may be required",
                "Works best on Samsung devices with Android 14/15"
            ],
            'emergency_call_exploit': [
                "Access emergency call interface",
                "Navigate to settings through emergency contacts",
                "May require multiple attempts"
            ]
        }
        
        return guidance.get(method_name, ["Follow standard bypass procedure"])
    
    def _get_method_prerequisites(self, method_name: str, device: DeviceInfo) -> List[str]:
        """Get method prerequisites"""
        prerequisites = {
            'adb_setup_wizard': ["USB cable", "ADB drivers", "Setup wizard active"],
            'talkback_chrome_2025': ["TalkBack enabled", "Chrome browser", "Voice input"],
            'hardware_exploits': ["Fastboot mode", "Hardware tools", "Technical expertise"]
        }
        
        return prerequisites.get(method_name, ["Basic device access"])
    
    def _get_troubleshooting_tips(self, method_name: str, device: DeviceInfo) -> List[str]:
        """Get troubleshooting tips"""
        tips = {
            'adb_setup_wizard': [
                "Try different USB ports",
                "Restart ADB service",
                "Check device drivers"
            ],
            'talkback_chrome_2025': [
                "Ensure TalkBack is properly configured",
                "Try voice commands slowly and clearly",
                "Restart device if TalkBack becomes unresponsive"
            ]
        }
        
        return tips.get(method_name, ["Check device connection", "Verify method requirements"])
    
    def _get_alternative_methods(self, device: DeviceInfo, current_method: str) -> List[str]:
        """Get alternative methods if current one fails"""
        profile = self.analyze_device(device)
        alternatives = [method for method in profile.recommended_methods if method != current_method]
        return alternatives[:3]  # Top 3 alternatives
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """Get AI learning insights and statistics"""
        total_attempts = len(self.success_history)
        if total_attempts == 0:
            return {'message': 'No data available yet'}
        
        successes = sum(1 for h in self.success_history if h['result'] == 'SUCCESS')
        success_rate = successes / total_attempts
        
        # Method performance analysis
        method_stats = {}
        for perf in self.method_performance.values():
            total = perf.success_count + perf.failure_count
            if total > 0:
                method_stats[perf.method_name] = {
                    'success_rate': perf.success_count / total,
                    'average_time': perf.average_time,
                    'total_attempts': total
                }
        
        return {
            'overall_success_rate': success_rate,
            'total_attempts': total_attempts,
            'method_performance': method_stats,
            'device_profiles_count': len(self.device_profiles),
            'learning_status': 'Active' if total_attempts > 10 else 'Learning'
        }