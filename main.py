#!/usr/bin/env python3
"""
FRP Freedom - Factory Reset Protection Bypass Tool
Main application entry point

This tool is designed for legitimate device recovery purposes only.
Users must ensure they have legal authorization before proceeding with any bypass operations.
"""

import sys
import os
import logging
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from src.gui.main_window import FRPFreedomApp
from src.core.logger import setup_logging
from src.core.config import Config

def main():
    """Main application entry point"""
    try:
        # Setup logging
        setup_logging()
        logger = logging.getLogger(__name__)
        
        logger.info("Starting FRP Freedom application")
        logger.info("Version: 1.0.0")
        logger.info("For legitimate device recovery purposes only")
        
        # Load configuration
        config = Config()
        
        # Create and run the main application
        app = FRPFreedomApp(config)
        app.run()
        
    except Exception as e:
        logging.error(f"Fatal error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()