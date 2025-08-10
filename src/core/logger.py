#!/usr/bin/env python3
"""
Logging system for FRP Freedom
Provides encrypted logging, audit trails, and security compliance
"""

import logging
import logging.handlers
import json
import datetime
from pathlib import Path
from typing import Dict, Any
from cryptography.fernet import Fernet
import coloredlogs

class EncryptedFileHandler(logging.FileHandler):
    """Custom file handler that encrypts log entries"""
    
    def __init__(self, filename, encryption_key: bytes, mode='a', encoding=None, delay=False):
        self.cipher = Fernet(encryption_key)
        super().__init__(filename, mode, encoding, delay)
    
    def emit(self, record):
        """Emit a log record, encrypting the message"""
        try:
            msg = self.format(record)
            encrypted_msg = self.cipher.encrypt(msg.encode('utf-8'))
            
            # Write encrypted message as base64 string
            with open(self.baseFilename, 'ab') as f:
                f.write(encrypted_msg + b'\n')
        except Exception:
            self.handleError(record)

class AuditLogger:
    """Specialized logger for audit trails and security events"""
    
    def __init__(self, config):
        self.config = config
        self.audit_file = config.logs_dir / "audit.log"
        self.encryption_key = config.generate_encryption_key() if config.logs_encrypted else None
        
        # Setup audit logger
        self.logger = logging.getLogger('frp_freedom.audit')
        self.logger.setLevel(logging.INFO)
        
        if config.logs_encrypted and self.encryption_key:
            handler = EncryptedFileHandler(self.audit_file, self.encryption_key)
        else:
            handler = logging.FileHandler(self.audit_file)
        
        formatter = logging.Formatter(
            '%(asctime)s - AUDIT - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_device_detection(self, device_info: Dict[str, Any]):
        """Log device detection event"""
        event = {
            "event_type": "device_detection",
            "timestamp": datetime.datetime.now().isoformat(),
            "device_info": {
                "model": device_info.get("model", "unknown"),
                "manufacturer": device_info.get("manufacturer", "unknown"),
                "android_version": device_info.get("android_version", "unknown"),
                "serial_partial": device_info.get("serial", "unknown")[:4] + "****" if device_info.get("serial") else "unknown"
            }
        }
        self.logger.info(json.dumps(event))
    

    def log_bypass_attempt(self, device_info: Dict, method: str, success: bool, error: str = None):
        """Log bypass attempt"""
        event = {
            "event_type": "bypass_attempt",
            "timestamp": datetime.datetime.now().isoformat(),
            "device_serial_partial": device_info.get("serial", "unknown")[:4] + "****" if device_info.get("serial") else "unknown",
            "bypass_method": method,
            "success": success,
            "error": error
        }
        self.logger.info(json.dumps(event))
    
    def log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log security-related events"""
        event = {
            "event_type": f"security_{event_type}",
            "timestamp": datetime.datetime.now().isoformat(),
            "details": details
        }
        self.logger.warning(json.dumps(event))
    
    def log_event(self, event_type: str, details: Dict[str, Any]):
        """Log general application events"""
        event = {
            "event_type": event_type,
            "timestamp": datetime.datetime.now().isoformat(),
            "details": details
        }
        self.logger.info(json.dumps(event))

def setup_logging(config=None):
    """Setup application logging"""
    if config is None:
        from .config import Config
        config = Config()
    
    # Create logs directory
    config.logs_dir.mkdir(exist_ok=True)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if config.debug_mode else logging.INFO)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Setup colored logs for console
    coloredlogs.install(
        level='DEBUG' if config.debug_mode else 'INFO',
        logger=root_logger,
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # File handler for application logs
    app_log_file = config.logs_dir / "frp_freedom.log"
    
    if config.logs_encrypted:
        encryption_key = config.generate_encryption_key()
        file_handler = EncryptedFileHandler(app_log_file, encryption_key)
    else:
        file_handler = logging.handlers.RotatingFileHandler(
            app_log_file, maxBytes=10*1024*1024, backupCount=5
        )
    
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Setup specific loggers
    logging.getLogger('frp_freedom').setLevel(logging.DEBUG if config.debug_mode else logging.INFO)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    return root_logger

def get_audit_logger(config=None):
    """Get the audit logger instance"""
    if config is None:
        from .config import Config
        config = Config()
    
    return AuditLogger(config)

def decrypt_log_file(log_file: Path, encryption_key: bytes) -> str:
    """Decrypt an encrypted log file for viewing"""
    cipher = Fernet(encryption_key)
    decrypted_lines = []
    
    try:
        with open(log_file, 'rb') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        decrypted_line = cipher.decrypt(line).decode('utf-8')
                        decrypted_lines.append(decrypted_line)
                    except Exception as e:
                        decrypted_lines.append(f"[DECRYPTION ERROR: {e}]")
        
        return '\n'.join(decrypted_lines)
    except Exception as e:
        return f"Error reading log file: {e}"