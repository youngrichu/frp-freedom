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
        """Setup main window properties"""
        self.root.title(f"FRP Freedom v{self.config.get('app.version')}")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        # Center window on screen
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (800 // 2)
        y = (self.root.winfo_screenheight() // 2) - (600 // 2)
        self.root.geometry(f"800x600+{x}+{y}")
        
        # Set icon if available
        try:
            icon_path = Path(__file__).parent.parent.parent / "assets" / "icon.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except Exception:
            pass
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_styles(self):
        """Setup custom styles for the application"""
        self.style = ttk.Style()
        
        # Configure custom styles
        self.style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        self.style.configure('Subtitle.TLabel', font=('Arial', 12))
        self.style.configure('Warning.TLabel', foreground='red', font=('Arial', 10, 'bold'))
        self.style.configure('Success.TLabel', foreground='green', font=('Arial', 10, 'bold'))
        self.style.configure('Info.TLabel', foreground='blue', font=('Arial', 10))
        
        # Button styles
        self.style.configure('Primary.TButton', font=('Arial', 10, 'bold'))
        self.style.configure('Secondary.TButton', font=('Arial', 10))
        self.style.configure('Danger.TButton', foreground='white', background='red')
    
    def create_widgets(self):
        """Create main window widgets"""
        # Main container
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=1)
        
        # Header frame
        self.create_header()
        
        # Content frame (will contain different wizard steps)
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.rowconfigure(0, weight=1)
        
        # Footer frame
        self.create_footer()
        
        # Initialize with welcome screen
        self.show_welcome_screen()
    
    def create_header(self):
        """Create application header"""
        header_frame = ttk.Frame(self.main_frame)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        header_frame.columnconfigure(1, weight=1)
        
        # Logo/Icon (placeholder)
        logo_label = ttk.Label(header_frame, text="🔓", font=('Arial', 24))
        logo_label.grid(row=0, column=0, padx=(0, 10))
        
        # Title and subtitle
        title_frame = ttk.Frame(header_frame)
        title_frame.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        title_label = ttk.Label(title_frame, text="FRP Freedom", style='Title.TLabel')
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        subtitle_label = ttk.Label(
            title_frame, 
            text="Professional FRP Bypass Tool - For Legitimate Device Recovery Only",
            style='Subtitle.TLabel'
        )
        subtitle_label.grid(row=1, column=0, sticky=tk.W)
        
        # Status indicator
        self.status_label = ttk.Label(header_frame, text="Ready", style='Info.TLabel')
        self.status_label.grid(row=0, column=2, padx=(10, 0))
    
    def create_footer(self):
        """Create application footer with navigation buttons"""
        footer_frame = ttk.Frame(self.main_frame)
        footer_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        footer_frame.columnconfigure(1, weight=1)
        
        # Navigation buttons
        self.back_button = ttk.Button(
            footer_frame, 
            text="← Back", 
            command=self.go_back,
            style='Secondary.TButton'
        )
        self.back_button.grid(row=0, column=0, padx=(0, 10))
        
        # Progress indicator
        self.progress_label = ttk.Label(footer_frame, text="Step 1 of 4: Welcome")
        self.progress_label.grid(row=0, column=1)
        
        self.next_button = ttk.Button(
            footer_frame, 
            text="Next →", 
            command=self.go_next,
            style='Primary.TButton'
        )
        self.next_button.grid(row=0, column=2, padx=(10, 0))
        
        # Initially disable back button
        self.back_button.configure(state='disabled')
    
    def setup_menu(self):
        """Setup application menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export Logs", command=self.export_logs)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Device Information", command=self.show_device_info)
        tools_menu.add_command(label="Refresh Devices", command=self.refresh_devices)
        tools_menu.add_separator()
        tools_menu.add_command(label="Settings", command=self.show_settings)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="User Guide", command=self.show_user_guide)
        help_menu.add_command(label="Legal Disclaimer", command=self.show_legal_disclaimer)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self.show_about)
    
    def show_welcome_screen(self):
        """Show welcome screen (Step 1)"""
        self.clear_content()
        self.current_step = 0
        self.update_progress("Step 1 of 4: Welcome")
        
        # Welcome content
        welcome_frame = ttk.Frame(self.content_frame)
        welcome_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=20, pady=20)
        welcome_frame.columnconfigure(0, weight=1)
        
        # Welcome message
        welcome_text = """
Welcome to FRP Freedom - Professional FRP Bypass Tool

This tool is designed for legitimate device recovery purposes only.
Please ensure you have legal ownership of the device before proceeding.

⚠️  IMPORTANT LEGAL NOTICE:
• Only use this tool on devices you legally own
• Bypassing FRP on stolen devices is illegal
• You are responsible for compliance with local laws
• This tool logs all activities for audit purposes

Supported Features:
✓ Android 5.0 - 15.0 compatibility
✓ Multiple bypass methods (ADB, Interface, System, Hardware)
✓ Wide OEM support (Samsung, LG, Huawei, Xiaomi, etc.)
✓ Secure operation with audit logging
✓ Comprehensive setup guide and documentation

Before proceeding, please:
1. Ensure your device is connected via USB
2. Enable USB Debugging if possible
3. Review the setup guide (SETUP_GUIDE.md) for detailed instructions
4. Read and accept the terms of use
"""
        
        text_widget = tk.Text(
            welcome_frame, 
            wrap=tk.WORD, 
            height=20, 
            font=('Arial', 10),
            state='disabled',
            bg=self.root.cget('bg')
        )
        text_widget.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 20))
        
        # Enable text widget to insert content
        text_widget.configure(state='normal')
        text_widget.insert('1.0', welcome_text)
        text_widget.configure(state='disabled')
        
        # Terms acceptance
        self.terms_var = tk.BooleanVar()
        terms_check = ttk.Checkbutton(
            welcome_frame,
            text="I have read and accept the terms of use and legal disclaimer",
            variable=self.terms_var,
            command=self.update_next_button
        )
        terms_check.grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
        
        # Ownership confirmation
        self.ownership_var = tk.BooleanVar()
        ownership_check = ttk.Checkbutton(
            welcome_frame,
            text="I confirm that I am the legal owner of the device I intend to unlock",
            variable=self.ownership_var,
            command=self.update_next_button
        )
        ownership_check.grid(row=2, column=0, sticky=tk.W)
        
        # Update button states
        self.update_next_button()
    
    def show_device_selection(self):
        """Show device selection screen (Step 2)"""
        self.clear_content()
        self.current_step = 1
        self.update_progress("Step 2 of 4: Device Selection")
        
        # Create device selection frame
        self.device_selection_frame = DeviceSelectionFrame(
            self.content_frame, 
            self.device_manager,
            self.on_device_selected
        )
        self.device_selection_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Update button states
        self.back_button.configure(state='normal')
        self.next_button.configure(state='disabled')
    
    def show_method_selection(self):
        """Show method selection screen (Step 3)"""
        if not self.selected_device:
            messagebox.showerror("Error", "No device selected")
            return
        
        self.clear_content()
        self.current_step = 2
        self.update_progress("Step 3 of 4: Method Selection")
        
        # Create method selection frame
        self.method_selection_frame = MethodSelectionFrame(
            self.content_frame,
            self.bypass_manager,
            self.selected_device,
            self.on_methods_selected
        )
        self.method_selection_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Update button states
        self.back_button.configure(state='normal')
        self.next_button.configure(state='disabled')
    
    def show_execution_screen(self):
        """Show bypass execution screen (Step 4)"""
        if not self.selected_methods:
            messagebox.showerror("Error", "No bypass methods selected")
            return
        
        self.clear_content()
        self.current_step = 3
        self.update_progress("Step 4 of 4: Bypass Execution")
        
        # Create execution frame
        execution_frame = ttk.Frame(self.content_frame)
        execution_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=20, pady=20)
        execution_frame.columnconfigure(0, weight=1)
        
        # Execution summary
        summary_label = ttk.Label(
            execution_frame,
            text=f"Ready to execute {len(self.selected_methods)} bypass method(s) on {self.selected_device.model}",
            style='Title.TLabel'
        )
        summary_label.grid(row=0, column=0, pady=(0, 20))
        
        # Warning message
        warning_text = """
⚠️  FINAL WARNING:

• Ensure the device is properly connected
• Do not disconnect the device during the process
• The bypass process may take several minutes
• Some methods may require device restarts
• Keep the device screen active if possible

Proceed only if you understand the risks and have confirmed device ownership.
"""
        
        warning_widget = tk.Text(
            execution_frame,
            wrap=tk.WORD,
            height=10,
            font=('Arial', 10),
            state='disabled',
            bg='#fff3cd',
            fg='#856404'
        )
        warning_widget.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        warning_widget.configure(state='normal')
        warning_widget.insert('1.0', warning_text)
        warning_widget.configure(state='disabled')
        
        # Execute button
        execute_button = ttk.Button(
            execution_frame,
            text="🚀 Start FRP Bypass",
            command=self.start_bypass_execution,
            style='Primary.TButton'
        )
        execute_button.grid(row=2, column=0, pady=10)
        
        # Update button states
        self.back_button.configure(state='normal')
        self.next_button.configure(state='disabled')
    
    def start_bypass_execution(self):
        """Start the bypass execution process"""
        # Log bypass attempt
        self.audit_logger.log_event(
            'bypass_attempt_start',
            {
                'device_serial': self.selected_device.serial,
                'device_model': self.selected_device.model,
                'methods': [method.name for method in self.selected_methods],
                'user_confirmed_ownership': True
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
        
        # Disable main window during execution
        self.root.configure(state='disabled')
    
    def on_bypass_completed(self, results):
        """Handle bypass completion"""
        self.bypass_results = results
        
        # Re-enable main window
        self.root.configure(state='normal')
        
        # Log bypass completion
        self.audit_logger.log_event(
            'bypass_attempt_complete',
            {
                'device_serial': self.selected_device.serial,
                'results': [{'method': r['method'], 'result': r['result'].name} for r in results]
            }
        )
        
        # Show results window
        # self.results_window = ResultsWindow(  # Not implemented yet
        # TODO: Implement results window
        #     self.root,
        #     self.selected_device,
        #     results,
        #     self.on_results_closed
        # )
        print(f"Bypass completed with results: {results}")
    
    def on_results_closed(self):
        """Handle results window closure"""
        # Reset to welcome screen
        self.reset_wizard()
    
    def clear_content(self):
        """Clear the content frame"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def update_progress(self, text: str):
        """Update progress label"""
        self.progress_label.configure(text=text)
    
    def update_next_button(self):
        """Update next button state based on current step"""
        if self.current_step == 0:  # Welcome screen
            if hasattr(self, 'terms_var') and hasattr(self, 'ownership_var'):
                if self.terms_var.get() and self.ownership_var.get():
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
        self.next_button.configure(state='normal')
        
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
        if methods:
            self.next_button.configure(state='normal')
        else:
            self.next_button.configure(state='disabled')
    
    def start_device_scanning(self):
        """Start background device scanning"""
        def scan_devices():
            while True:
                try:
                    devices = self.device_manager.scan_devices()
                    # Update device list if device selection frame exists
                    if hasattr(self, 'device_selection_frame'):
                        self.root.after(0, self.device_selection_frame.update_device_list, devices)
                except Exception as e:
                    self.logger.error(f"Device scanning error: {e}")
                
                # Wait before next scan
                import time
                time.sleep(3)
        
        # Start scanning in background thread
        scan_thread = threading.Thread(target=scan_devices, daemon=True)
        scan_thread.start()
    
    def refresh_devices(self):
        """Manually refresh device list"""
        if hasattr(self, 'device_selection_frame'):
            devices = self.device_manager.scan_devices()
            self.device_selection_frame.update_device_list(devices)
    
    def show_device_info(self):
        """Show detailed device information"""
        if self.selected_device:
            info_window = tk.Toplevel(self.root)
            info_window.title("Device Information")
            info_window.geometry("500x400")
            info_window.transient(self.root)
            info_window.grab_set()
            
            # Device info content
            info_text = f"""
Device Information:

Serial: {self.selected_device.serial}
Model: {self.selected_device.model}
Brand: {self.selected_device.brand}
Android Version: {self.selected_device.android_version}
API Level: {self.selected_device.api_level}
Connection: {self.selected_device.connection_type}
FRP Status: {self.selected_device.frp_enabled}
Bootloader: {self.selected_device.bootloader_status}
Root Status: {self.selected_device.root_status}
"""
            
            text_widget = tk.Text(info_window, wrap=tk.WORD, font=('Courier', 10))
            text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text_widget.insert('1.0', info_text)
            text_widget.configure(state='disabled')
        else:
            messagebox.showinfo("Information", "No device selected")
    
    def show_settings(self):
        """Show settings window"""
        messagebox.showinfo("Settings", "Settings window not implemented yet")
    
    def show_user_guide(self):
        """Show user guide"""
        messagebox.showinfo("User Guide", "User guide not implemented yet")
    
    def show_legal_disclaimer(self):
        """Show legal disclaimer"""
        disclaimer_text = self.config.get('legal.disclaimer', 'Legal disclaimer not available')
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
                defaultextension=".log",
                filetypes=[("Log files", "*.log"), ("All files", "*.*")]
            )
            
            if filename:
                # Copy log file to selected location
                import shutil
                log_path = Path.home() / ".frp_freedom" / "logs" / "app.log"
                if log_path.exists():
                    shutil.copy2(log_path, filename)
                    messagebox.showinfo("Success", f"Logs exported to {filename}")
                else:
                    messagebox.showerror("Error", "Log file not found")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export logs: {e}")
    
    def reset_wizard(self):
        """Reset wizard to initial state"""
        self.current_step = 0
        self.selected_device = None
        self.selected_methods = []
        self.bypass_results = []
        self.show_welcome_screen()
    
    def on_closing(self):
        """Handle application closing"""
        # Log application exit
        self.audit_logger.log_event('application_exit', {})
        
        # Confirm exit if bypass is in progress
        if hasattr(self, 'progress_window') and self.progress_window.winfo_exists():
            if messagebox.askokcancel("Quit", "Bypass operation in progress. Are you sure you want to quit?"):
                self.root.destroy()
        else:
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