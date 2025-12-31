#!/usr/bin/env python3
"""
Configuration management for FRP Freedom
Handles application settings, ethical guidelines, and security parameters
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any
from cryptography.fernet import Fernet

class Config:
    """Application configuration manager"""
    
    def __init__(self, config_file: str = None):
        # Initialize paths and allow overrides via environment variables
        self.app_dir = Path.home() / ".frp_freedom"

        # Environment override for config file path
        env_config = os.getenv('FRP_FREEDOM_CONFIG')
        if config_file:
            self.config_file = Path(config_file)
        elif env_config:
            self.config_file = Path(env_config)
        else:
            self.config_file = self.app_dir / "config.yaml"

        # Environment override for logs directory
        env_logs = os.getenv('FRP_FREEDOM_LOG_DIR')
        if env_logs:
            self.logs_dir = Path(env_logs)
        else:
            self.logs_dir = self.app_dir / "logs"

        self.cache_dir = self.app_dir / "cache"

        # Create directories if they don't exist
        self.app_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)

        # Default configuration
        self.default_config = {
            "app": {
                "version": "1.0.0",
                "debug_mode": False,
                "auto_update": True,
                "language": "en"
            },

            "security": {
                "max_attempts_per_device": 3,
                "encrypt_logs": True,
                "audit_trail": True
            },
            "device": {
                "auto_detect": True,
                "supported_android_versions": ["5.0", "15.0"],
                "timeout_seconds": 30
            },
            "bypass_methods": {
                "adb_exploits": True,
                "bootloader_exploits": True,
                "interface_exploits": True,
                "hardware_methods": False  # Disabled by default for safety
            },
            "ui": {
                "theme": "light",
                "show_advanced_options": False,
                "wizard_mode": True
            }
        }

        # Honor FRP_FREEDOM_DEBUG environment variable if set (true/1/yes/on)
        debug_env = os.getenv('FRP_FREEDOM_DEBUG')
        if debug_env is not None:
            self.default_config['app']['debug_mode'] = str(debug_env).lower() in ('1', 'true', 'yes', 'on')

        self.config = self.load_config()
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = yaml.safe_load(f)
                # Merge with defaults to ensure all keys exist
                return self._merge_configs(self.default_config, loaded_config)
            except Exception as e:
                print(f"Error loading config: {e}. Using defaults.")
                return self.default_config.copy()
        else:
            # Create default config file
            self.save_config(self.default_config)
            return self.default_config.copy()
    
    def save_config(self, config: Dict[str, Any] = None) -> None:
        """Save configuration to file"""
        config_to_save = config or self.config
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(config_to_save, f, default_flow_style=False, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def _merge_configs(self, default: Dict, loaded: Dict) -> Dict:
        """Recursively merge loaded config with defaults"""
        result = default.copy()
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        return result
    
    def get(self, key_path: str, default=None):
        """Get configuration value using dot notation (e.g., 'app.version')"""
        keys = key_path.split('.')
        value = self.config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any) -> None:
        """Set configuration value using dot notation"""
        keys = key_path.split('.')
        config = self.config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value
        self.save_config()
    
    def get_ethical_guidelines(self) -> Dict[str, str]:
        """Return ethical guidelines and legal disclaimers"""
        return {
            "legal_disclaimer": "This tool is provided for educational and legitimate device recovery purposes only. Users are responsible for compliance with local laws.",
            "anti_theft": "Using this tool on stolen devices is illegal and unethical. All bypass attempts are logged for audit purposes.",
            "data_privacy": "All operations are performed locally. No data is transmitted to external servers.",
            "rate_limiting": f"Limited to {self.get('security.max_attempts_per_device', 3)} attempts per device per day to prevent abuse."
        }
    
    def generate_encryption_key(self) -> bytes:
        """Generate encryption key for log files"""
        key_file = self.app_dir / ".key"
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            # Set restrictive permissions
            os.chmod(key_file, 0o600)
            return key
    
    @property
    def logs_encrypted(self) -> bool:
        """Check if log encryption is enabled"""
        return self.get('security.encrypt_logs', True)
    
    @property
    def debug_mode(self) -> bool:
        """Check if debug mode is enabled"""
        return self.get('app.debug_mode', False)