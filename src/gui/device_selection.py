#!/usr/bin/env python3
"""
Device Selection Frame for FRP Freedom
Implements the device selection step of the wizard
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging
from typing import List, Callable, Optional

from ..core.device_manager import DeviceManager, DeviceInfo

class DeviceSelectionFrame(ttk.Frame):
    """Frame for device selection and information display"""
    
    def __init__(self, parent, device_manager: DeviceManager, selection_callback: Callable[[DeviceInfo], None]):
        super().__init__(parent)
        self.device_manager = device_manager
        self.selection_callback = selection_callback
        self.logger = logging.getLogger(__name__)
        
        self.devices: List[DeviceInfo] = []
        self.selected_device: Optional[DeviceInfo] = None
        
        self.setup_widgets()
        self.refresh_devices()
    
    def setup_widgets(self):
        """Setup the device selection widgets"""
        # Configure grid
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        
        # Header
        header_frame = ttk.Frame(self)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        header_frame.columnconfigure(1, weight=1)
        
        title_label = ttk.Label(
            header_frame,
            text="Select Device",
            font=('Arial', 14, 'bold')
        )
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        # Refresh button
        refresh_button = ttk.Button(
            header_frame,
            text="🔄 Refresh",
            command=self.refresh_devices
        )
        refresh_button.grid(row=0, column=2, padx=(10, 0))
        
        # Instructions
        instructions_label = ttk.Label(
            header_frame,
            text="Connect your device via USB and ensure USB Debugging is enabled (if possible)",
            font=('Arial', 10)
        )
        instructions_label.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))
        
        # Main content area
        content_frame = ttk.Frame(self)
        content_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        # Create notebook for different views
        self.notebook = ttk.Notebook(content_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Device list tab
        self.create_device_list_tab()
        
        # Device details tab
        self.create_device_details_tab()
        
        # Connection help tab
        self.create_connection_help_tab()
    
    def create_device_list_tab(self):
        """Create the device list tab"""
        list_frame = ttk.Frame(self.notebook)
        self.notebook.add(list_frame, text="Connected Devices")
        
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(1, weight=1)
        
        # Status label
        self.status_label = ttk.Label(
            list_frame,
            text="Scanning for devices...",
            font=('Arial', 10)
        )
        self.status_label.grid(row=0, column=0, pady=(0, 10), sticky=tk.W)
        
        # Device treeview
        columns = ('Serial', 'Model', 'Brand', 'Android', 'Connection', 'FRP Status')
        self.device_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)
        
        # Configure columns
        self.device_tree.heading('Serial', text='Serial Number')
        self.device_tree.heading('Model', text='Model')
        self.device_tree.heading('Brand', text='Brand')
        self.device_tree.heading('Android', text='Android Version')
        self.device_tree.heading('Connection', text='Connection')
        self.device_tree.heading('FRP Status', text='FRP Status')
        
        # Column widths
        self.device_tree.column('Serial', width=120)
        self.device_tree.column('Model', width=150)
        self.device_tree.column('Brand', width=100)
        self.device_tree.column('Android', width=100)
        self.device_tree.column('Connection', width=80)
        self.device_tree.column('FRP Status', width=80)
        
        self.device_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.device_tree.yview)
        scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.device_tree.configure(yscrollcommand=scrollbar.set)
        
        # Bind selection event
        self.device_tree.bind('<<TreeviewSelect>>', self.on_device_select)
        
        # Action buttons
        button_frame = ttk.Frame(list_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0), sticky=(tk.W, tk.E))
        
        self.select_button = ttk.Button(
            button_frame,
            text="Select Device",
            command=self.confirm_device_selection,
            state='disabled'
        )
        self.select_button.pack(side=tk.LEFT)
        
        self.info_button = ttk.Button(
            button_frame,
            text="Device Info",
            command=self.show_device_info,
            state='disabled'
        )
        self.info_button.pack(side=tk.LEFT, padx=(10, 0))
    
    def create_device_details_tab(self):
        """Create the device details tab"""
        details_frame = ttk.Frame(self.notebook)
        self.notebook.add(details_frame, text="Device Details")
        
        details_frame.columnconfigure(0, weight=1)
        details_frame.rowconfigure(0, weight=1)
        
        # Scrollable text widget for device details
        self.details_text = tk.Text(
            details_frame,
            wrap=tk.WORD,
            font=('Courier', 10),
            state='disabled'
        )
        self.details_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for details
        details_scrollbar = ttk.Scrollbar(details_frame, orient=tk.VERTICAL, command=self.details_text.yview)
        details_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.details_text.configure(yscrollcommand=details_scrollbar.set)
        
        # Initially show placeholder text
        self.update_device_details(None)
    
    def create_connection_help_tab(self):
        """Create the connection help tab"""
        help_frame = ttk.Frame(self.notebook)
        self.notebook.add(help_frame, text="Connection Help")
        
        help_frame.columnconfigure(0, weight=1)
        help_frame.rowconfigure(0, weight=1)
        
        help_text = """
Device Connection Guide

📱 ADB Connection (Recommended):
1. Enable Developer Options:
   • Go to Settings → About Phone
   • Tap "Build Number" 7 times
   • Developer Options will appear in Settings

2. Enable USB Debugging:
   • Go to Settings → Developer Options
   • Enable "USB Debugging"
   • Connect device via USB cable
   • Accept the debugging authorization prompt

🔧 Fastboot Connection:
1. Power off the device completely
2. Hold Volume Down + Power buttons simultaneously
3. Device should enter fastboot/download mode
4. Connect via USB cable

⚠️ If Device is FRP Locked:
• ADB may not be available
• Try fastboot/download mode
• Some methods work without debugging
• Hardware-based methods may be required

🔍 Troubleshooting:
• Try different USB cables
• Use USB 2.0 ports if available
• Install device drivers if on Windows
• Restart ADB service: adb kill-server && adb start-server
• Check if device appears in Device Manager (Windows)

📋 Supported Connection Types:
✓ ADB (Android Debug Bridge)
✓ Fastboot (Bootloader mode)
✓ Download mode (Samsung, LG, etc.)
✓ EDL mode (Qualcomm devices)
✓ Recovery mode (limited functionality)

💡 Tips:
• Keep device screen active during process
• Ensure stable USB connection
• Close other Android tools (Android Studio, etc.)
• Use original or high-quality USB cables
"""
        
        help_text_widget = tk.Text(
            help_frame,
            wrap=tk.WORD,
            font=('Arial', 10),
            state='disabled',
            bg=self.cget('bg')
        )
        help_text_widget.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Add scrollbar
        help_scrollbar = ttk.Scrollbar(help_frame, orient=tk.VERTICAL, command=help_text_widget.yview)
        help_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        help_text_widget.configure(yscrollcommand=help_scrollbar.set)
        
        # Insert help text
        help_text_widget.configure(state='normal')
        help_text_widget.insert('1.0', help_text)
        help_text_widget.configure(state='disabled')
    
    def refresh_devices(self):
        """Refresh the device list"""
        def scan_in_background():
            try:
                self.after(0, lambda: self.status_label.configure(text="Scanning for devices..."))
                devices = self.device_manager.scan_devices()
                self.after(0, lambda: self.update_device_list(devices))
            except Exception as e:
                self.logger.error(f"Error scanning devices: {e}")
                self.after(0, lambda: self.status_label.configure(text=f"Error: {e}"))
        
        # Run scan in background thread
        scan_thread = threading.Thread(target=scan_in_background, daemon=True)
        scan_thread.start()
    
    def update_device_list(self, devices: List[DeviceInfo]):
        """Update the device list display"""
        self.devices = devices
        
        # Clear existing items
        for item in self.device_tree.get_children():
            self.device_tree.delete(item)
        
        # Update status
        if not devices:
            self.status_label.configure(text="No devices found. Please connect a device and try again.")
        else:
            self.status_label.configure(text=f"Found {len(devices)} device(s)")
        
        # Add devices to tree
        for device in devices:
            # Determine FRP status display
            frp_status = "Unknown"
            if device.frp_enabled is not None:
                frp_status = "Enabled" if device.frp_enabled else "Disabled"
            
            # Add device to tree
            item_id = self.device_tree.insert('', 'end', values=(
                device.serial[:12] + "..." if len(device.serial) > 15 else device.serial,
                device.model or "Unknown",
                device.brand or "Unknown",
                device.android_version or "Unknown",
                device.connection_type.upper(),
                frp_status
            ))
            
            # Store device reference
            self.device_tree.set(item_id, 'device_obj', device)
    
    def on_device_select(self, event):
        """Handle device selection in tree"""
        selection = self.device_tree.selection()
        if selection:
            item_id = selection[0]
            # Find the device object
            for device in self.devices:
                if device.serial in self.device_tree.item(item_id)['values'][0]:
                    self.selected_device = device
                    break
            
            # Enable buttons
            self.select_button.configure(state='normal')
            self.info_button.configure(state='normal')
            
            # Update device details tab
            self.update_device_details(self.selected_device)
        else:
            self.selected_device = None
            self.select_button.configure(state='disabled')
            self.info_button.configure(state='disabled')
            self.update_device_details(None)
    
    def update_device_details(self, device: Optional[DeviceInfo]):
        """Update the device details tab"""
        self.details_text.configure(state='normal')
        self.details_text.delete('1.0', tk.END)
        
        if device:
            details = f"""
Device Details:
{'=' * 50}

Basic Information:
  Serial Number: {device.serial}
  Model: {device.model or 'Unknown'}
  Brand: {device.brand or 'Unknown'}
  Product: {device.product or 'Unknown'}
  Device: {device.device or 'Unknown'}

System Information:
  Android Version: {device.android_version or 'Unknown'}
  API Level: {device.api_level or 'Unknown'}
  Build ID: {device.build_id or 'Unknown'}
  Security Patch: {device.security_patch or 'Unknown'}

Connection Information:
  Connection Type: {device.connection_type.upper()}
  ADB Status: {'Connected' if device.connection_type == 'adb' else 'Not Available'}
  Fastboot Status: {'Connected' if device.connection_type == 'fastboot' else 'Not Available'}

Security Status:
  FRP Status: {'Enabled' if device.frp_enabled else 'Disabled' if device.frp_enabled is not None else 'Unknown'}
  Bootloader: {device.bootloader_status or 'Unknown'}
  Root Status: {device.root_status or 'Unknown'}
  Encryption: {device.encryption_status or 'Unknown'}

Hardware Information:
  CPU Architecture: {device.cpu_arch or 'Unknown'}
  RAM: {device.ram_size or 'Unknown'}
  Storage: {device.storage_size or 'Unknown'}

Bypass Compatibility:
  ADB Methods: {'Available' if device.connection_type == 'adb' else 'Not Available'}
  Fastboot Methods: {'Available' if device.connection_type == 'fastboot' else 'Not Available'}
  Hardware Methods: {'May be Available' if device.brand else 'Unknown'}
  Interface Methods: {'Available' if device.connection_type == 'adb' else 'Limited'}

Notes:
• FRP bypass success depends on Android version and security patch level
• Newer devices may have additional security measures
• Some methods require specific device states (bootloader unlocked, etc.)
• Always ensure you have legal ownership before proceeding
"""
        else:
            details = """
Device Details:
{'=' * 50}

No device selected.

Please select a device from the "Connected Devices" tab to view detailed information.

If no devices are shown:
1. Ensure your device is connected via USB
2. Enable USB Debugging if possible
3. Try different USB ports or cables
4. Check the "Connection Help" tab for troubleshooting
"""
        
        self.details_text.insert('1.0', details)
        self.details_text.configure(state='disabled')
    
    def confirm_device_selection(self):
        """Confirm device selection and proceed"""
        if not self.selected_device:
            messagebox.showerror("Error", "No device selected")
            return
        
        # Show confirmation dialog
        device = self.selected_device
        message = f"""
Confirm Device Selection:

Serial: {device.serial}
Model: {device.model or 'Unknown'}
Brand: {device.brand or 'Unknown'}
Android: {device.android_version or 'Unknown'}
FRP Status: {'Enabled' if device.frp_enabled else 'Disabled' if device.frp_enabled is not None else 'Unknown'}

Proceed with this device?
"""
        
        if messagebox.askyesno("Confirm Selection", message):
            self.selection_callback(self.selected_device)
    
    def show_device_info(self):
        """Show detailed device information in a popup"""
        if not self.selected_device:
            messagebox.showerror("Error", "No device selected")
            return
        
        # Create info window
        info_window = tk.Toplevel(self)
        info_window.title(f"Device Info - {self.selected_device.model}")
        info_window.geometry("600x500")
        info_window.transient(self.winfo_toplevel())
        info_window.grab_set()
        
        # Center the window
        info_window.update_idletasks()
        x = (info_window.winfo_screenwidth() // 2) - (600 // 2)
        y = (info_window.winfo_screenheight() // 2) - (500 // 2)
        info_window.geometry(f"600x500+{x}+{y}")
        
        # Create notebook for different info categories
        info_notebook = ttk.Notebook(info_window)
        info_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Basic info tab
        basic_frame = ttk.Frame(info_notebook)
        info_notebook.add(basic_frame, text="Basic Info")
        
        basic_text = tk.Text(basic_frame, wrap=tk.WORD, font=('Courier', 10))
        basic_text.pack(fill=tk.BOTH, expand=True)
        
        device = self.selected_device
        basic_info = f"""
Basic Device Information:

Serial Number: {device.serial}
Model: {device.model or 'Unknown'}
Brand: {device.brand or 'Unknown'}
Product: {device.product or 'Unknown'}
Device: {device.device or 'Unknown'}
Android Version: {device.android_version or 'Unknown'}
API Level: {device.api_level or 'Unknown'}
Build ID: {device.build_id or 'Unknown'}
"""
        
        basic_text.insert('1.0', basic_info)
        basic_text.configure(state='disabled')
        
        # Security info tab
        security_frame = ttk.Frame(info_notebook)
        info_notebook.add(security_frame, text="Security")
        
        security_text = tk.Text(security_frame, wrap=tk.WORD, font=('Courier', 10))
        security_text.pack(fill=tk.BOTH, expand=True)
        
        security_info = f"""
Security Information:

FRP Status: {'Enabled' if device.frp_enabled else 'Disabled' if device.frp_enabled is not None else 'Unknown'}
Bootloader Status: {device.bootloader_status or 'Unknown'}
Root Status: {device.root_status or 'Unknown'}
Encryption Status: {device.encryption_status or 'Unknown'}
Security Patch: {device.security_patch or 'Unknown'}

Bypass Recommendations:
{'• ADB methods available' if device.connection_type == 'adb' else '• ADB methods not available'}
{'• Fastboot methods available' if device.connection_type == 'fastboot' else '• Fastboot methods not available'}
• Hardware methods may be available depending on chipset
• Interface methods {'available' if device.connection_type == 'adb' else 'limited'}
"""
        
        security_text.insert('1.0', security_info)
        security_text.configure(state='disabled')
        
        # Close button
        close_button = ttk.Button(info_window, text="Close", command=info_window.destroy)
        close_button.pack(pady=10)
    
    def get_selected_device(self) -> Optional[DeviceInfo]:
        """Get the currently selected device"""
        return self.selected_device