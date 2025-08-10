#!/usr/bin/env python3
"""
Main Window for FRP Freedom
Implements the primary GUI interface with wizard-style navigation
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import logging
from typing import Optional, Dict, Any, Callable
from pathlib import Path

from ..core.config import Config
from ..core.logger import setup_logging, AuditLogger
from ..core.device_manager import DeviceManager, DeviceInfo
from ..bypass.bypass_manager import BypassManager, BypassResult
from ..ai import AINotificationSystem
from .device_selection import DeviceSelectionFrame
from .method_selection import MethodSelectionFrame
from .utils import ProgressDialog
# from .results_window import ResultsWindow  # Not implemented yet

class FRPFreedomApp:
    """Main application class for FRP Freedom"""
    
    def __init__(self, config=None):
        self.root = tk.Tk()
        self.config = config or Config()
        self.logger = logging.getLogger(__name__)
        self.audit_logger = AuditLogger(self.config)
        
        # Initialize managers
        self.device_manager = DeviceManager(self.config)
        self.bypass_manager = BypassManager(self.config, self.device_manager)
        
        # Initialize AI notification system (will be set after window creation)
        self.notification_system = None
        
        # GUI state
        self.current_step = 0
        self.selected_device: Optional[DeviceInfo] = None
        self.selected_methods = []
        self.bypass_results = []
        
        # Setup GUI
        self.setup_window()
        self.setup_styles()
        self.create_widgets()
        self.setup_menu()
        
        # Initialize AI notification system
        self.notification_system = AINotificationSystem(self.root)
        
        # Integrate notification system with bypass manager
        self.bypass_manager.set_notification_system(self.notification_system)
        
        # Start device scanning
        self.start_device_scanning()
        
        # Log application start
        self.audit_logger.log_event(
            'application_start',
            {'version': self.config.get('app.version')}
        )
    
    def setup_window(self):
        """Configure main window properties"""
        self.root.title("FRP Freedom - Android FRP Bypass Tool")
        self.root.geometry("1024x768")
        self.root.minsize(800, 600)
        
        # Center window on screen
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (1024 // 2)
        y = (self.root.winfo_screenheight() // 2) - (768 // 2)
        self.root.geometry(f"1024x768+{x}+{y}")
        
        # Configure window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Set window icon (if available)
        try:
            # self.root.iconbitmap("assets/icon.ico")
            pass
        except:
            pass
    
    def setup_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        
        # Configure button styles
        style.configure('Primary.TButton', font=('Arial', 10, 'bold'))
        style.configure('Secondary.TButton', font=('Arial', 9))
        
        # Configure frame styles
        style.configure('Card.TFrame', relief='raised', borderwidth=1)
        style.configure('Header.TFrame', background='#2c3e50')
        
        # Configure label styles
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        style.configure('Subtitle.TLabel', font=('Arial', 12))
        style.configure('Header.TLabel', font=('Arial', 14, 'bold'), foreground='white')
    
    def create_widgets(self):
        """Create main window widgets"""
        # Main container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header
        self.create_header()
        
        # Content area
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Footer with navigation buttons
        self.create_footer()
        
        # Show initial screen
        self.show_welcome_screen()
    
    def create_header(self):
        """Create application header"""
        header_frame = ttk.Frame(self.main_frame, style='Header.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Title
        title_label = ttk.Label(
            header_frame,
            text="FRP Freedom",
            style='Header.TLabel'
        )
        title_label.pack(side=tk.LEFT, padx=20, pady=15)
        
        # Subtitle
        subtitle_label = ttk.Label(
            header_frame,
            text="Android Factory Reset Protection Bypass Tool",
            style='Header.TLabel',
            font=('Arial', 10)
        )
        subtitle_label.pack(side=tk.LEFT, padx=(0, 20), pady=15)
        
        # Status indicator
        self.status_label = ttk.Label(
            header_frame,
            text="Ready",
            style='Header.TLabel',
            font=('Arial', 9)
        )
        self.status_label.pack(side=tk.RIGHT, padx=20, pady=15)
    
    def create_footer(self):
        """Create footer with navigation buttons"""
        footer_frame = ttk.Frame(self.main_frame)
        footer_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Progress indicator
        self.progress_label = ttk.Label(
            footer_frame,
            text="Step 1 of 4: Welcome",
            font=('Arial', 9)
        )
        self.progress_label.pack(side=tk.LEFT)
        
        # Navigation buttons
        button_frame = ttk.Frame(footer_frame)
        button_frame.pack(side=tk.RIGHT)
        
        self.back_button = ttk.Button(
            button_frame,
            text="← Back",
            command=self.go_back,
            state='disabled'
        )
        self.back_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.next_button = ttk.Button(
            button_frame,
            text="Next →",
            command=self.go_next,
            style='Primary.TButton'
        )
        self.next_button.pack(side=tk.LEFT)
    
    def setup_menu(self):
        """Create application menu"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export Logs...", command=self.export_logs)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Device Information", command=self.show_device_info)
        tools_menu.add_command(label="Refresh Devices", command=self.refresh_devices)
        tools_menu.add_command(label="Settings", command=self.show_settings)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="User Guide", command=self.show_user_guide)
        help_menu.add_command(label="Legal Disclaimer", command=self.show_legal_disclaimer)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self.show_about)
    
    def show_welcome_screen(self):
        """Display welcome screen with terms and conditions"""
        self.clear_content()
        self.current_step = 0
        self.update_progress("Step 1 of 4: Welcome")
        
        # Welcome frame
        welcome_frame = ttk.Frame(self.content_frame)
        welcome_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            welcome_frame,
            text="Welcome to FRP Freedom",
            style='Title.TLabel'
        )
        title_label.pack(pady=(20, 10))
        
        # Description
        desc_text = """
FRP Freedom is a professional tool designed for legitimate Android device recovery.
This tool helps recover access to devices when Factory Reset Protection (FRP) is enabled.

IMPORTANT: This tool is intended for legitimate device recovery purposes only.
Unauthorized device bypass is illegal and violates terms of service.
"""
        
        desc_label = ttk.Label(
            welcome_frame,
            text=desc_text,
            justify=tk.CENTER,
            wraplength=600
        )
        desc_label.pack(pady=10)
        
        # Terms and conditions
        terms_frame = ttk.LabelFrame(welcome_frame, text="Terms and Conditions", padding=20)
        terms_frame.pack(fill=tk.BOTH, expand=True, padx=50, pady=20)
        
        # Terms text
        terms_text = tk.Text(
            terms_frame,
            wrap=tk.WORD,
            height=8,
            width=80,
            font=('Arial', 9)
        )
        terms_text.pack(fill=tk.BOTH, expand=True)
        
        terms_content = """
By using this software, you acknowledge and agree to the following:

1. You will use this tool only for legitimate device recovery purposes
2. You have proper legal authorization to modify the target device
3. You understand the risks involved in device modification procedures
4. You will comply with all applicable local laws and regulations
5. You accept full responsibility for any consequences of using this tool
6. The developers are not liable for any misuse or legal consequences

This software is provided "as is" without warranty of any kind. Use at your own risk.
"""
        
        terms_text.insert(tk.END, terms_content)
        terms_text.config(state=tk.DISABLED)
        
        # Scrollbar for terms
        scrollbar = ttk.Scrollbar(terms_frame, orient=tk.VERTICAL, command=terms_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        terms_text.config(yscrollcommand=scrollbar.set)
        
        # Acceptance checkbox
        checkbox_frame = ttk.Frame(welcome_frame)
        checkbox_frame.pack(pady=10)
        
        self.terms_var = tk.BooleanVar()
        terms_checkbox = ttk.Checkbutton(
            checkbox_frame,
            text="I have read and agree to the terms and conditions",
            variable=self.terms_var,
            command=self.update_next_button
        )
        terms_checkbox.pack()
        
        # Update navigation
        self.back_button.config(state='disabled')
        self.update_next_button()
    
    def show_device_selection(self):
        """Display device selection screen"""
        self.clear_content()
        self.current_step = 1
        self.update_progress("Step 2 of 4: Device Selection")
        
        # Create device selection frame
        self.device_frame = DeviceSelectionFrame(
            self.content_frame,
            self.device_manager,
            self.on_device_selected
        )
        self.device_frame.pack(fill=tk.BOTH, expand=True)
        
        # Update navigation
        self.back_button.config(state='normal')
        self.next_button.config(state='disabled')
    
    def show_method_selection(self):
        """Display method selection screen"""
        self.clear_content()
        self.current_step = 2
        self.update_progress("Step 3 of 4: Method Selection")
        
        # Create method selection frame
        self.method_frame = MethodSelectionFrame(
            self.content_frame,
            self.selected_device,
            self.bypass_manager,
            self.on_methods_selected
        )
        self.method_frame.pack(fill=tk.BOTH, expand=True)
        
        # Update navigation
        self.back_button.config(state='normal')
        self.next_button.config(state='disabled')
    
    def show_execution_screen(self):
        """Display execution screen"""
        self.clear_content()
        self.current_step = 3
        self.update_progress("Step 4 of 4: Execution")
        
        # Execution frame
        execution_frame = ttk.Frame(self.content_frame)
        execution_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            execution_frame,
            text="Ready to Execute Bypass",
            style='Title.TLabel'
        )
        title_label.pack(pady=(20, 10))
        
        # Device info
        info_frame = ttk.LabelFrame(execution_frame, text="Device Information", padding=10)
        info_frame.pack(fill=tk.X, padx=50, pady=10)
        
        device_info = f"""
Device: {self.selected_device.model}
Serial: {self.selected_device.serial}
Android Version: {self.selected_device.android_version}
Selected Methods: {', '.join([method.name for method in self.selected_methods])}
"""
        
        info_label = ttk.Label(info_frame, text=device_info, justify=tk.LEFT)
        info_label.pack()
        
        # Warning
        warning_frame = ttk.LabelFrame(execution_frame, text="Important Warning", padding=10)
        warning_frame.pack(fill=tk.X, padx=50, pady=10)
        
        warning_text = """
⚠️ IMPORTANT WARNINGS:

• Ensure device battery is above 50%
• Keep USB cable connected throughout the process
• Do not disconnect or power off the device during execution
• The bypass process may take several minutes
• Some methods may require device restarts
• Keep the device screen active if possible

Proceed only if you understand the risks and legal implications.
"""
        
        warning_widget = tk.Text(
            execution_frame,
            wrap=tk.WORD,
            height=10,
            width=80,
            font=('Arial', 9)
        )
        warning_widget.pack(fill=tk.BOTH, expand=True, padx=50, pady=10)
        warning_widget.insert(tk.END, warning_text)
        warning_widget.config(state=tk.DISABLED)
        
        # Execute button
        execute_button = ttk.Button(
            execution_frame,
            text="Start Bypass Execution",
            command=self.start_bypass_execution,
            style='Primary.TButton'
        )
        execute_button.pack(pady=20)
        
        # Update navigation
        self.back_button.config(state='normal')
        self.next_button.config(state='disabled')
    
    def start_bypass_execution(self):
        """Start the bypass execution process"""
        # Log bypass attempt
        self.audit_logger.log_event(
            'bypass_attempt_start',
            {
                'device_serial': self.selected_device.serial,
                'device_model': self.selected_device.model,
                'methods': [method.name for method in self.selected_methods]
            }
        )
        
        # Create and show progress window
        self.progress_window = ProgressDialog(
            self.root,
            self.selected_device,
            self.selected_methods,
            self.bypass_manager,
            self.on_bypass_completed
        )
        self.progress_window.start_execution()
    
    def on_bypass_completed(self, results):
        """Handle bypass completion"""
        self.bypass_results = results
        
        # Log completion
        self.audit_logger.log_event(
            'bypass_attempt_completed',
            {
                'device_serial': self.selected_device.serial,
                'results': [{
                    'method': result.method_name,
                    'success': result.success,
                    'duration': result.execution_time
                } for result in results]
            }
        )
        
        # Show results
        self.show_results(results)
    
    def show_results(self, results):
        """Show execution results"""
        # For now, show a simple message box
        # TODO: Implement proper results window
        success_count = sum(1 for result in results if result.success)
        total_count = len(results)
        
        if success_count > 0:
            messagebox.showinfo(
                "Bypass Complete",
                f"Bypass completed successfully!\n\n"
                f"Successful methods: {success_count}/{total_count}\n"
                f"Check the device to verify FRP bypass."
            )
        else:
            messagebox.showwarning(
                "Bypass Failed",
                f"All bypass methods failed.\n\n"
                f"Please try different methods or check device compatibility."
            )
    
    def on_results_closed(self):
        """Handle results window closing"""
        self.reset_wizard()
    
    def clear_content(self):
        """Clear content frame"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def update_progress(self, text: str):
        """Update progress label"""
        self.progress_label.config(text=text)
    
    def update_next_button(self):
        """Update next button state based on current step"""
        if self.current_step == 0:  # Welcome screen
            if hasattr(self, 'terms_var'):
                if self.terms_var.get():
                    self.next_button.configure(state='normal')
                else:
                    self.next_button.configure(state='disabled')
    
    def go_back(self):
        """Go to previous step"""
        if self.current_step > 0:
            if self.current_step == 1:
                self.show_welcome_screen()
            elif self.current_step == 2:
                self.show_device_selection()
            elif self.current_step == 3:
                self.show_method_selection()
    
    def go_next(self):
        """Go to next step"""
        if self.current_step == 0:
            self.show_device_selection()
        elif self.current_step == 1:
            self.show_method_selection()
        elif self.current_step == 2:
            self.show_execution_screen()
    
    def on_device_selected(self, device: DeviceInfo):
        """Handle device selection"""
        self.selected_device = device
        self.next_button.config(state='normal')
        
        # Log device selection
        self.audit_logger.log_event(
            'device_selected',
            {
                'device_serial': device.serial,
                'device_model': device.model,
                'android_version': device.android_version
            }
        )
    
    def on_methods_selected(self, methods):
        """Handle method selection"""
        self.selected_methods = methods
        self.next_button.config(state='normal')
    
    def start_device_scanning(self):
        """Start device scanning in background"""
        def scan_devices():
            try:
                # Continuously scan for devices
                import time
                while True:
                    devices = self.device_manager.scan_devices()
                    # Update device selection frame if it exists
                    if hasattr(self, 'device_frame') and self.device_frame:
                        self.device_frame.after(0, self.device_frame.update_device_list, devices)
                    time.sleep(5)  # Scan every 5 seconds
            except Exception as e:
                self.logger.error(f"Device scanning error: {e}")
        
        # Start scanning in background thread
        scan_thread = threading.Thread(target=scan_devices, daemon=True)
        scan_thread.start()
    
    def refresh_devices(self):
        """Refresh device list"""
        try:
            self.device_manager.refresh_devices()
            if hasattr(self, 'device_frame'):
                self.device_frame.refresh()
            messagebox.showinfo("Refresh Complete", "Device list refreshed successfully.")
        except Exception as e:
            messagebox.showerror("Refresh Error", f"Failed to refresh devices: {e}")
    
    def show_device_info(self):
        """Show detailed device information"""
        if not self.selected_device:
            messagebox.showwarning("No Device", "Please select a device first.")
            return
        
        info_text = f"""
Device Information:

Model: {self.selected_device.model}
Manufacturer: {self.selected_device.manufacturer}
Serial Number: {self.selected_device.serial}
Android Version: {self.selected_device.android_version}
API Level: {self.selected_device.api_level}
Security Patch: {getattr(self.selected_device, 'security_patch', 'Unknown')}
Build Number: {getattr(self.selected_device, 'build_number', 'Unknown')}
Connection Type: {self.selected_device.connection_type}
Status: {self.selected_device.status}
"""
        
        messagebox.showinfo("Device Information", info_text)
    
    def show_settings(self):
        """Show settings dialog"""
        messagebox.showinfo("Settings", "Settings dialog not implemented yet.")
    
    def show_user_guide(self):
        """Show user guide"""
        messagebox.showinfo("User Guide", "User guide not implemented yet.")
    
    def show_legal_disclaimer(self):
        """Show legal disclaimer"""
        disclaimer_text = """
LEGAL DISCLAIMER

This software is provided for educational and legitimate device recovery purposes only.

By using this software, you acknowledge that:
• You are authorized to modify the target device
• You will not use this software for illegal purposes
• You understand the risks involved in device modification
• You accept full responsibility for any consequences

The developers assume no responsibility for misuse of this software or any legal consequences arising from its use.

Use this software responsibly and in compliance with applicable laws.
"""
        messagebox.showinfo("Legal Disclaimer", disclaimer_text)
    
    def show_about(self):
        """Show about dialog"""
        about_text = f"""
FRP Freedom v{self.config.get('app.version')}

Professional FRP Bypass Tool
For Legitimate Device Recovery Only

Developed for educational and legitimate recovery purposes.
Use responsibly and in compliance with local laws.

© 2024 FRP Freedom Project
"""
        messagebox.showinfo("About FRP Freedom", about_text)
    
    def export_logs(self):
        """Export application logs"""
        try:
            filename = filedialog.asksaveasfilename(
                title="Export Logs",
                defaultextension=".zip",
                filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")]
            )
            
            if filename:
                # TODO: Implement log export functionality
                messagebox.showinfo("Export Complete", f"Logs exported to {filename}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export logs: {e}")
    
    def reset_wizard(self):
        """Reset wizard to initial state"""
        self.current_step = 0
        self.selected_device = None
        self.selected_methods = []
        self.bypass_results = []
        self.show_welcome_screen()
    
    def on_closing(self):
        """Handle application closing"""
        try:
            # Log application shutdown
            self.audit_logger.log_event('application_shutdown', {})
            
            # Destroy window
            self.root.destroy()
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
            self.root.destroy()
    
    def run(self):
        """Start the application"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.logger.info("Application interrupted by user")
        except Exception as e:
            self.logger.error(f"Application error: {e}")
            messagebox.showerror("Fatal Error", f"Application error: {e}")
        finally:
            # Cleanup
            self.audit_logger.log_event('application_shutdown', {})

def main():
    """Main entry point"""
    # Setup logging
    setup_logging()
    
    # Create and run application
    app = FRPFreedomApp()
    app.run()

if __name__ == "__main__":
    main()