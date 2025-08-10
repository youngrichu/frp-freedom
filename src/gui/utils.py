#!/usr/bin/env python3
"""
GUI Utilities for FRP Freedom
Common widgets, dialogs, and helper functions
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
from typing import Callable, Optional, Any, Dict, List
import logging
from datetime import datetime

class ProgressDialog:
    """Modal progress dialog with cancellation support"""
    
    def __init__(self, parent, title: str, message: str, cancellable: bool = True):
        self.parent = parent
        self.title = title
        self.message = message
        self.cancellable = cancellable
        self.cancelled = False
        self.dialog = None
        
        self.create_dialog()
    
    def create_dialog(self):
        """Create the progress dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(self.title)
        self.dialog.geometry("400x150")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (150 // 2)
        self.dialog.geometry(f"400x150+{x}+{y}")
        
        # Configure grid
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
        
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(0, weight=1)
        
        # Message label
        self.message_label = ttk.Label(
            main_frame,
            text=self.message,
            font=('Arial', 11)
        )
        self.message_label.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(
            main_frame,
            mode='indeterminate'
        )
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        self.progress_bar.start()
        
        # Cancel button
        if self.cancellable:
            self.cancel_button = ttk.Button(
                main_frame,
                text="Cancel",
                command=self.cancel
            )
            self.cancel_button.grid(row=2, column=0)
        
        # Handle dialog close
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel if self.cancellable else lambda: None)
    
    def update_message(self, message: str):
        """Update the progress message"""
        if self.dialog and self.message_label:
            self.message_label.configure(text=message)
    
    def cancel(self):
        """Cancel the operation"""
        self.cancelled = True
        self.close()
    
    def close(self):
        """Close the dialog"""
        if self.dialog:
            self.progress_bar.stop()
            self.dialog.destroy()
            self.dialog = None
    
    def is_cancelled(self) -> bool:
        """Check if operation was cancelled"""
        return self.cancelled

class InfoDialog:
    """Custom info dialog with rich content support"""
    
    def __init__(self, parent, title: str, content: str, width: int = 500, height: int = 400):
        self.parent = parent
        self.title = title
        self.content = content
        self.width = width
        self.height = height
        
        self.create_dialog()
    
    def create_dialog(self):
        """Create the info dialog"""
        dialog = tk.Toplevel(self.parent)
        dialog.title(self.title)
        dialog.geometry(f"{self.width}x{self.height}")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (self.width // 2)
        y = (dialog.winfo_screenheight() // 2) - (self.height // 2)
        dialog.geometry(f"{self.width}x{self.height}+{x}+{y}")
        
        # Configure grid
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(0, weight=1)
        
        # Main frame
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # Content text widget
        text_widget = tk.Text(
            main_frame,
            wrap=tk.WORD,
            font=('Arial', 10),
            state='disabled',
            bg='#f8f9fa'
        )
        text_widget.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 15))
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(text_widget, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Insert content
        text_widget.configure(state='normal')
        text_widget.insert(1.0, self.content)
        text_widget.configure(state='disabled')
        
        # Close button
        close_button = ttk.Button(
            main_frame,
            text="Close",
            command=dialog.destroy
        )
        close_button.grid(row=1, column=0)
        
        # Focus and wait
        dialog.focus_set()
        dialog.wait_window()

class DeviceInfoWidget(ttk.Frame):
    """Reusable device information display widget"""
    
    def __init__(self, parent, device_info: Dict[str, Any] = None, **kwargs):
        super().__init__(parent, **kwargs)
        self.device_info = device_info or {}
        
        self.setup_widgets()
        if device_info:
            self.update_device_info(device_info)
    
    def setup_widgets(self):
        """Setup the device info widgets"""
        # Configure grid
        self.columnconfigure(1, weight=1)
        
        # Device icon
        self.icon_label = ttk.Label(self, text="📱", font=('Arial', 24))
        self.icon_label.grid(row=0, column=0, rowspan=4, padx=(0, 15), pady=5)
        
        # Device details
        self.brand_label = ttk.Label(self, text="Brand: Unknown", font=('Arial', 10, 'bold'))
        self.brand_label.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        self.model_label = ttk.Label(self, text="Model: Unknown", font=('Arial', 10))
        self.model_label.grid(row=1, column=1, sticky=tk.W, pady=2)
        
        self.android_label = ttk.Label(self, text="Android: Unknown", font=('Arial', 10))
        self.android_label.grid(row=2, column=1, sticky=tk.W, pady=2)
        
        self.status_label = ttk.Label(self, text="Status: Unknown", font=('Arial', 10))
        self.status_label.grid(row=3, column=1, sticky=tk.W, pady=2)
    
    def update_device_info(self, device_info: Dict[str, Any]):
        """Update the displayed device information"""
        self.device_info = device_info
        
        brand = device_info.get('brand', 'Unknown')
        model = device_info.get('model', 'Unknown')
        android_version = device_info.get('android_version', 'Unknown')
        connection_type = device_info.get('connection_type', 'Unknown')
        
        self.brand_label.configure(text=f"Brand: {brand}")
        self.model_label.configure(text=f"Model: {model}")
        self.android_label.configure(text=f"Android: {android_version}")
        self.status_label.configure(text=f"Connection: {connection_type}")
        
        # Update icon based on brand
        icon = self.get_brand_icon(brand)
        self.icon_label.configure(text=icon)
    
    def get_brand_icon(self, brand: str) -> str:
        """Get appropriate icon for device brand"""
        brand_icons = {
            'samsung': '📱',
            'google': '📱',
            'huawei': '📱',
            'xiaomi': '📱',
            'oneplus': '📱',
            'lg': '📱',
            'sony': '📱',
            'motorola': '📱',
            'htc': '📱'
        }
        
        return brand_icons.get(brand.lower(), '📱')

class StatusBar(ttk.Frame):
    """Application status bar"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.setup_widgets()
    
    def setup_widgets(self):
        """Setup status bar widgets"""
        # Configure grid
        self.columnconfigure(1, weight=1)
        
        # Status label
        self.status_label = ttk.Label(self, text="Ready", font=('Arial', 9))
        self.status_label.grid(row=0, column=0, sticky=tk.W, padx=5)
        
        # Separator
        ttk.Separator(self, orient='vertical').grid(row=0, column=1, sticky=(tk.N, tk.S), padx=5)
        
        # Connection status
        self.connection_label = ttk.Label(self, text="No device", font=('Arial', 9))
        self.connection_label.grid(row=0, column=2, sticky=tk.W, padx=5)
        
        # Time label
        self.time_label = ttk.Label(self, text="", font=('Arial', 9))
        self.time_label.grid(row=0, column=3, sticky=tk.E, padx=5)
        
        # Update time
        self.update_time()
    
    def set_status(self, status: str):
        """Set the main status text"""
        self.status_label.configure(text=status)
    
    def set_connection_status(self, status: str, color: str = None):
        """Set the connection status"""
        self.connection_label.configure(text=status)
        if color:
            self.connection_label.configure(foreground=color)
    
    def update_time(self):
        """Update the time display"""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_label.configure(text=current_time)
        
        # Schedule next update
        self.after(1000, self.update_time)

class ToolTip:
    """Simple tooltip implementation"""
    
    def __init__(self, widget, text: str, delay: int = 500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window = None
        self.timer_id = None
        
        self.widget.bind('<Enter>', self.on_enter)
        self.widget.bind('<Leave>', self.on_leave)
        self.widget.bind('<Motion>', self.on_motion)
    
    def on_enter(self, event):
        """Handle mouse enter"""
        self.schedule_tooltip()
    
    def on_leave(self, event):
        """Handle mouse leave"""
        self.cancel_tooltip()
        self.hide_tooltip()
    
    def on_motion(self, event):
        """Handle mouse motion"""
        self.cancel_tooltip()
        self.schedule_tooltip()
    
    def schedule_tooltip(self):
        """Schedule tooltip display"""
        self.cancel_tooltip()
        self.timer_id = self.widget.after(self.delay, self.show_tooltip)
    
    def cancel_tooltip(self):
        """Cancel scheduled tooltip"""
        if self.timer_id:
            self.widget.after_cancel(self.timer_id)
            self.timer_id = None
    
    def show_tooltip(self):
        """Show the tooltip"""
        if self.tooltip_window:
            return
        
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25
        
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        
        label = ttk.Label(
            self.tooltip_window,
            text=self.text,
            background='#ffffe0',
            relief='solid',
            borderwidth=1,
            font=('Arial', 9)
        )
        label.pack()
    
    def hide_tooltip(self):
        """Hide the tooltip"""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class AsyncTaskRunner:
    """Helper for running async tasks with progress dialog"""
    
    def __init__(self, parent):
        self.parent = parent
        self.logger = logging.getLogger(__name__)
    
    def run_task(self, task_func: Callable, 
                 progress_title: str = "Processing",
                 progress_message: str = "Please wait...",
                 success_callback: Callable[[Any], None] = None,
                 error_callback: Callable[[Exception], None] = None,
                 cancellable: bool = True) -> None:
        """Run a task asynchronously with progress dialog"""
        
        # Create progress dialog
        progress = ProgressDialog(self.parent, progress_title, progress_message, cancellable)
        
        result = {'value': None, 'error': None, 'completed': False}
        
        def task_wrapper():
            """Wrapper for the task function"""
            try:
                result['value'] = task_func()
                result['completed'] = True
            except Exception as e:
                result['error'] = e
                result['completed'] = True
                self.logger.exception(f"Task failed: {e}")
        
        def check_completion():
            """Check if task is completed"""
            if result['completed']:
                progress.close()
                
                if result['error']:
                    if error_callback:
                        error_callback(result['error'])
                    else:
                        messagebox.showerror("Error", f"Task failed: {result['error']}")
                else:
                    if success_callback:
                        success_callback(result['value'])
            elif progress.is_cancelled():
                # Task was cancelled
                progress.close()
            else:
                # Check again in 100ms
                self.parent.after(100, check_completion)
        
        # Start task in background thread
        task_thread = threading.Thread(target=task_wrapper, daemon=True)
        task_thread.start()
        
        # Start checking for completion
        self.parent.after(100, check_completion)

def center_window(window, width: int, height: int):
    """Center a window on the screen"""
    window.update_idletasks()
    x = (window.winfo_screenwidth() // 2) - (width // 2)
    y = (window.winfo_screenheight() // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")

def show_error_dialog(parent, title: str, message: str, details: str = None):
    """Show an error dialog with optional details"""
    if details:
        # Create custom dialog with details
        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.geometry("500x400")
        dialog.transient(parent)
        dialog.grab_set()
        
        center_window(dialog, 500, 400)
        
        # Configure grid
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(1, weight=1)
        
        # Main frame
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Error message
        message_label = ttk.Label(
            main_frame,
            text=message,
            font=('Arial', 11),
            wraplength=450
        )
        message_label.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        
        # Details text widget
        details_frame = ttk.LabelFrame(main_frame, text="Details", padding="10")
        details_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 15))
        details_frame.columnconfigure(0, weight=1)
        details_frame.rowconfigure(0, weight=1)
        
        details_text = tk.Text(
            details_frame,
            wrap=tk.WORD,
            font=('Consolas', 9),
            state='disabled'
        )
        details_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(details_text, orient="vertical", command=details_text.yview)
        details_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Insert details
        details_text.configure(state='normal')
        details_text.insert(1.0, details)
        details_text.configure(state='disabled')
        
        # Close button
        close_button = ttk.Button(
            main_frame,
            text="Close",
            command=dialog.destroy
        )
        close_button.grid(row=2, column=0)
        
        dialog.focus_set()
        dialog.wait_window()
    else:
        # Use standard messagebox
        messagebox.showerror(title, message)

def show_confirmation_dialog(parent, title: str, message: str, details: str = None) -> bool:
    """Show a confirmation dialog with optional details"""
    if details:
        # Create custom dialog
        result = {'confirmed': False}
        
        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.geometry("450x300")
        dialog.transient(parent)
        dialog.grab_set()
        
        center_window(dialog, 450, 300)
        
        # Configure grid
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(1, weight=1)
        
        # Main frame
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Message
        message_label = ttk.Label(
            main_frame,
            text=message,
            font=('Arial', 11),
            wraplength=400
        )
        message_label.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        
        # Details
        if details:
            details_label = ttk.Label(
                main_frame,
                text=details,
                font=('Arial', 10),
                wraplength=400,
                foreground='gray'
            )
            details_label.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, sticky=tk.E)
        
        def on_yes():
            result['confirmed'] = True
            dialog.destroy()
        
        def on_no():
            result['confirmed'] = False
            dialog.destroy()
        
        no_button = ttk.Button(button_frame, text="No", command=on_no)
        no_button.pack(side=tk.LEFT, padx=(0, 10))
        
        yes_button = ttk.Button(button_frame, text="Yes", command=on_yes)
        yes_button.pack(side=tk.LEFT)
        
        dialog.focus_set()
        dialog.wait_window()
        
        return result['confirmed']
    else:
        # Use standard messagebox
        return messagebox.askyesno(title, message)

def add_tooltip(widget, text: str, delay: int = 500):
    """Add a tooltip to a widget"""
    return ToolTip(widget, text, delay)

def validate_input(value: str, input_type: str) -> tuple[bool, str]:
    """Validate input based on type"""
    if input_type == 'email':
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(pattern, value):
            return True, ""
        else:
            return False, "Invalid email format"
    
    elif input_type == 'phone':
        # Simple phone validation
        cleaned = re.sub(r'[^0-9+]', '', value)
        if len(cleaned) >= 10:
            return True, ""
        else:
            return False, "Invalid phone number"
    
    elif input_type == 'date':
        try:
            datetime.strptime(value, '%Y-%m-%d')
            return True, ""
        except ValueError:
            return False, "Invalid date format (use YYYY-MM-DD)"
    
    elif input_type == 'required':
        if value.strip():
            return True, ""
        else:
            return False, "This field is required"
    
    return True, ""