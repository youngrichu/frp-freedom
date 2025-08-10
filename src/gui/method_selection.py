#!/usr/bin/env python3
"""
Method Selection Frame for FRP Freedom
Implements the bypass method selection step of the wizard
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import List, Callable, Dict, Any

from ..core.device_manager import DeviceInfo
from ..bypass.bypass_manager import BypassManager, BypassMethod

class MethodSelectionFrame(ttk.Frame):
    """Frame for bypass method selection"""
    
    def __init__(self, parent, bypass_manager: BypassManager, device: DeviceInfo, selection_callback: Callable[[List[BypassMethod]], None]):
        super().__init__(parent)
        self.bypass_manager = bypass_manager
        self.device = device
        self.selection_callback = selection_callback
        self.logger = logging.getLogger(__name__)
        
        self.available_methods: List[BypassMethod] = []
        self.selected_methods: List[BypassMethod] = []
        self.method_vars: Dict[str, tk.BooleanVar] = {}
        
        self.setup_widgets()
        self.load_available_methods()
    
    def setup_widgets(self):
        """Setup the method selection widgets"""
        # Configure grid
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        
        # Header
        header_frame = ttk.Frame(self)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        header_frame.columnconfigure(0, weight=1)
        
        title_label = ttk.Label(
            header_frame,
            text="Select Bypass Methods",
            font=('Arial', 14, 'bold')
        )
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        # Device info
        device_info_label = ttk.Label(
            header_frame,
            text=f"Device: {self.device.brand} {self.device.model} (Android {self.device.android_version})",
            font=('Arial', 10)
        )
        device_info_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # Instructions
        instructions_label = ttk.Label(
            header_frame,
            text="Select one or more bypass methods. Methods are ordered by success probability.",
            font=('Arial', 10)
        )
        instructions_label.grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        
        # Main content area with notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create tabs for different method categories
        self.create_recommended_tab()
        self.create_adb_tab()
        self.create_interface_tab()
        self.create_system_tab()
        self.create_hardware_tab()
        
        # Footer with selection summary and buttons
        self.create_footer()
    
    def create_recommended_tab(self):
        """Create the recommended methods tab"""
        self.recommended_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.recommended_frame, text="🌟 Recommended")
        
        self.recommended_frame.columnconfigure(0, weight=1)
        self.recommended_frame.rowconfigure(1, weight=1)
        
        # Info label
        info_label = ttk.Label(
            self.recommended_frame,
            text="These methods have the highest success rate for your device:",
            font=('Arial', 10, 'bold')
        )
        info_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # Scrollable frame for methods
        self.recommended_scroll_frame = self.create_scrollable_frame(self.recommended_frame)
        self.recommended_scroll_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    def create_adb_tab(self):
        """Create the ADB methods tab"""
        self.adb_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.adb_frame, text="🔧 ADB Methods")
        
        self.adb_frame.columnconfigure(0, weight=1)
        self.adb_frame.rowconfigure(1, weight=1)
        
        # Info label
        info_label = ttk.Label(
            self.adb_frame,
            text="ADB-based bypass methods (requires USB debugging):",
            font=('Arial', 10, 'bold')
        )
        info_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # Scrollable frame for methods
        self.adb_scroll_frame = self.create_scrollable_frame(self.adb_frame)
        self.adb_scroll_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    def create_interface_tab(self):
        """Create the interface methods tab"""
        self.interface_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.interface_frame, text="📱 Interface Methods")
        
        self.interface_frame.columnconfigure(0, weight=1)
        self.interface_frame.rowconfigure(1, weight=1)
        
        # Info label
        info_label = ttk.Label(
            self.interface_frame,
            text="UI-based bypass methods (exploits interface vulnerabilities):",
            font=('Arial', 10, 'bold')
        )
        info_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # Scrollable frame for methods
        self.interface_scroll_frame = self.create_scrollable_frame(self.interface_frame)
        self.interface_scroll_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    def create_system_tab(self):
        """Create the system methods tab"""
        self.system_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.system_frame, text="⚙️ System Methods")
        
        self.system_frame.columnconfigure(0, weight=1)
        self.system_frame.rowconfigure(1, weight=1)
        
        # Info label
        info_label = ttk.Label(
            self.system_frame,
            text="System-level bypass methods (requires root or unlocked bootloader):",
            font=('Arial', 10, 'bold')
        )
        info_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # Scrollable frame for methods
        self.system_scroll_frame = self.create_scrollable_frame(self.system_frame)
        self.system_scroll_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    def create_hardware_tab(self):
        """Create the hardware methods tab"""
        self.hardware_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.hardware_frame, text="🔩 Hardware Methods")
        
        self.hardware_frame.columnconfigure(0, weight=1)
        self.hardware_frame.rowconfigure(1, weight=1)
        
        # Info label
        info_label = ttk.Label(
            self.hardware_frame,
            text="Hardware-based bypass methods (chipset-specific exploits):",
            font=('Arial', 10, 'bold')
        )
        info_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # Scrollable frame for methods
        self.hardware_scroll_frame = self.create_scrollable_frame(self.hardware_frame)
        self.hardware_scroll_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    def create_scrollable_frame(self, parent):
        """Create a scrollable frame for method lists"""
        # Create canvas and scrollbar
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Grid the canvas and scrollbar
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Configure parent grid
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        
        return scrollable_frame
    
    def create_footer(self):
        """Create footer with selection summary and buttons"""
        footer_frame = ttk.Frame(self)
        footer_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(20, 0))
        footer_frame.columnconfigure(1, weight=1)
        
        # Selection summary
        self.selection_label = ttk.Label(
            footer_frame,
            text="No methods selected",
            font=('Arial', 10)
        )
        self.selection_label.grid(row=0, column=0, sticky=tk.W)
        
        # Buttons
        button_frame = ttk.Frame(footer_frame)
        button_frame.grid(row=0, column=2, sticky=tk.E)
        
        clear_button = ttk.Button(
            button_frame,
            text="Clear All",
            command=self.clear_selection
        )
        clear_button.pack(side=tk.LEFT, padx=(0, 10))
        
        auto_select_button = ttk.Button(
            button_frame,
            text="Auto Select",
            command=self.auto_select_methods
        )
        auto_select_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.confirm_button = ttk.Button(
            button_frame,
            text="Confirm Selection",
            command=self.confirm_selection,
            state='disabled'
        )
        self.confirm_button.pack(side=tk.LEFT)
    
    def load_available_methods(self):
        """Load available bypass methods for the device"""
        try:
            # Get recommended methods
            recommended = self.bypass_manager.get_recommended_methods(self.device)
            
            # Get all available methods by category
            all_methods = self.bypass_manager.get_available_methods()
            
            self.available_methods = all_methods
            
            # Populate method tabs
            self.populate_recommended_methods(recommended)
            self.populate_methods_by_category()
            
        except Exception as e:
            self.logger.error(f"Error loading bypass methods: {e}")
            messagebox.showerror("Error", f"Failed to load bypass methods: {e}")
    
    def populate_recommended_methods(self, recommended_methods: List[BypassMethod]):
        """Populate the recommended methods tab"""
        if not recommended_methods:
            no_methods_label = ttk.Label(
                self.recommended_scroll_frame,
                text="No recommended methods available for this device.",
                font=('Arial', 10, 'italic')
            )
            no_methods_label.pack(pady=20)
            return
        
        for i, method in enumerate(recommended_methods):
            self.create_method_widget(self.recommended_scroll_frame, method, i, recommended=True)
    
    def populate_methods_by_category(self):
        """Populate methods by category tabs"""
        # Group methods by category
        categories = {
            'adb': [],
            'interface': [],
            'system': [],
            'hardware': []
        }
        
        for method in self.available_methods:
            if 'adb' in method.name.lower():
                categories['adb'].append(method)
            elif 'interface' in method.name.lower() or 'ui' in method.name.lower():
                categories['interface'].append(method)
            elif 'system' in method.name.lower() or 'database' in method.name.lower() or 'partition' in method.name.lower():
                categories['system'].append(method)
            elif 'hardware' in method.name.lower() or 'edl' in method.name.lower() or 'download' in method.name.lower():
                categories['hardware'].append(method)
        
        # Populate each category
        frames = {
            'adb': self.adb_scroll_frame,
            'interface': self.interface_scroll_frame,
            'system': self.system_scroll_frame,
            'hardware': self.hardware_scroll_frame
        }
        
        for category, methods in categories.items():
            frame = frames[category]
            if not methods:
                no_methods_label = ttk.Label(
                    frame,
                    text=f"No {category} methods available for this device.",
                    font=('Arial', 10, 'italic')
                )
                no_methods_label.pack(pady=20)
            else:
                for i, method in enumerate(methods):
                    self.create_method_widget(frame, method, i)
    
    def create_method_widget(self, parent, method: BypassMethod, index: int, recommended: bool = False):
        """Create a widget for a bypass method"""
        # Method frame
        method_frame = ttk.LabelFrame(parent, text=method.name, padding="10")
        method_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Add recommended badge
        if recommended:
            badge_frame = ttk.Frame(method_frame)
            badge_frame.pack(fill=tk.X, pady=(0, 5))
            
            badge_label = ttk.Label(
                badge_frame,
                text="⭐ RECOMMENDED",
                font=('Arial', 8, 'bold'),
                foreground='gold'
            )
            badge_label.pack(side=tk.LEFT)
        
        # Method info frame
        info_frame = ttk.Frame(method_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        info_frame.columnconfigure(1, weight=1)
        
        # Checkbox
        var_key = f"{method.name}_{index}"
        self.method_vars[var_key] = tk.BooleanVar()
        
        checkbox = ttk.Checkbutton(
            info_frame,
            variable=self.method_vars[var_key],
            command=lambda m=method, k=var_key: self.on_method_toggle(m, k)
        )
        checkbox.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        # Method details
        details_frame = ttk.Frame(info_frame)
        details_frame.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Description
        desc_label = ttk.Label(
            details_frame,
            text=method.description,
            font=('Arial', 10),
            wraplength=400
        )
        desc_label.pack(anchor=tk.W)
        
        # Requirements and compatibility
        req_text = f"Requirements: {', '.join(method.requirements)}"
        req_label = ttk.Label(
            details_frame,
            text=req_text,
            font=('Arial', 9),
            foreground='gray'
        )
        req_label.pack(anchor=tk.W, pady=(2, 0))
        
        # Success rate and estimated time
        stats_frame = ttk.Frame(details_frame)
        stats_frame.pack(fill=tk.X, pady=(5, 0))
        
        success_label = ttk.Label(
            stats_frame,
            text=f"Success Rate: {method.success_rate}%",
            font=('Arial', 9),
            foreground='green' if method.success_rate >= 70 else 'orange' if method.success_rate >= 40 else 'red'
        )
        success_label.pack(side=tk.LEFT)
        
        time_label = ttk.Label(
            stats_frame,
            text=f"Est. Time: {method.estimated_time_minutes} min",
            font=('Arial', 9),
            foreground='gray'
        )
        time_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Risk level
        risk_color = {'low': 'green', 'medium': 'orange', 'high': 'red'}.get(method.risk_level, 'gray')
        risk_label = ttk.Label(
            stats_frame,
            text=f"Risk: {method.risk_level.upper()}",
            font=('Arial', 9),
            foreground=risk_color
        )
        risk_label.pack(side=tk.RIGHT)
        
        # Compatibility indicators
        compat_frame = ttk.Frame(details_frame)
        compat_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Check device compatibility
        is_compatible = self.check_method_compatibility(method)
        
        compat_label = ttk.Label(
            compat_frame,
            text="✓ Compatible" if is_compatible else "⚠ May not be compatible",
            font=('Arial', 9),
            foreground='green' if is_compatible else 'orange'
        )
        compat_label.pack(side=tk.LEFT)
        
        # Store method reference
        method_frame.method = method
        method_frame.var_key = var_key
    
    def check_method_compatibility(self, method: BypassMethod) -> bool:
        """Check if method is compatible with the device"""
        # Check Android version compatibility
        if self.device.android_version:
            try:
                device_version = float(self.device.android_version.split('.')[0])
                if hasattr(method, 'min_android_version') and device_version < method.min_android_version:
                    return False
                if hasattr(method, 'max_android_version') and device_version > method.max_android_version:
                    return False
            except (ValueError, AttributeError):
                pass
        
        # Check connection type requirements
        if 'adb' in method.requirements and self.device.connection_type != 'adb':
            return False
        if 'fastboot' in method.requirements and self.device.connection_type != 'fastboot':
            return False
        
        # Check root requirements
        if 'root' in method.requirements and self.device.root_status != 'rooted':
            return False
        
        # Check bootloader requirements
        if 'unlocked_bootloader' in method.requirements and 'unlocked' not in (self.device.bootloader_status or '').lower():
            return False
        
        return True
    
    def on_method_toggle(self, method: BypassMethod, var_key: str):
        """Handle method selection toggle"""
        if self.method_vars[var_key].get():
            if method not in self.selected_methods:
                self.selected_methods.append(method)
        else:
            if method in self.selected_methods:
                self.selected_methods.remove(method)
        
        self.update_selection_display()
    
    def update_selection_display(self):
        """Update the selection summary display"""
        count = len(self.selected_methods)
        
        if count == 0:
            self.selection_label.configure(text="No methods selected")
            self.confirm_button.configure(state='disabled')
        else:
            total_time = sum(method.estimated_time_minutes for method in self.selected_methods)
            self.selection_label.configure(
                text=f"{count} method(s) selected (Est. total time: {total_time} min)"
            )
            self.confirm_button.configure(state='normal')
        
        # Notify parent
        self.selection_callback(self.selected_methods)
    
    def clear_selection(self):
        """Clear all method selections"""
        for var in self.method_vars.values():
            var.set(False)
        
        self.selected_methods.clear()
        self.update_selection_display()
    
    def auto_select_methods(self):
        """Automatically select recommended methods"""
        self.clear_selection()
        
        # Get recommended methods
        recommended = self.bypass_manager.get_recommended_methods(self.device)
        
        if not recommended:
            messagebox.showinfo("Auto Select", "No recommended methods available for this device.")
            return
        
        # Select up to 3 recommended methods
        for method in recommended[:3]:
            # Find the corresponding checkbox
            for var_key, var in self.method_vars.items():
                if method.name in var_key:
                    var.set(True)
                    self.on_method_toggle(method, var_key)
                    break
        
        messagebox.showinfo(
            "Auto Select",
            f"Selected {len(self.selected_methods)} recommended method(s) for your device."
        )
    
    def confirm_selection(self):
        """Confirm method selection and proceed"""
        if not self.selected_methods:
            messagebox.showerror("Error", "No methods selected")
            return
        
        # Show confirmation dialog
        method_names = [method.name for method in self.selected_methods]
        total_time = sum(method.estimated_time_minutes for method in self.selected_methods)
        
        message = f"""
Confirm Method Selection:

Selected Methods:
{chr(10).join(f'• {name}' for name in method_names)}

Total Estimated Time: {total_time} minutes

Proceed with these methods?
"""
        
        if messagebox.askyesno("Confirm Selection", message):
            self.selection_callback(self.selected_methods)
    
    def get_selected_methods(self) -> List[BypassMethod]:
        """Get the currently selected methods"""
        return self.selected_methods.copy()