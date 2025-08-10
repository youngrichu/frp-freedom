#!/usr/bin/env python3
"""
Bypass Execution Frame for FRP Freedom
Implements the bypass execution step with progress tracking
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import logging
from typing import List, Callable, Optional
from datetime import datetime

from ..core.device_manager import DeviceInfo
from ..bypass.bypass_manager import BypassManager, BypassMethod, BypassResult
from ..core.logger import AuditLogger

class BypassExecutionFrame(ttk.Frame):
    """Frame for bypass execution with progress tracking"""
    
    def __init__(self, parent, bypass_manager: BypassManager, device: DeviceInfo, 
                 methods: List[BypassMethod], completion_callback: Callable[[bool, List[BypassResult]], None]):
        super().__init__(parent)
        self.bypass_manager = bypass_manager
        self.device = device
        self.methods = methods
        self.completion_callback = completion_callback
        self.logger = logging.getLogger(__name__)
        self.audit_logger = AuditLogger(self.bypass_manager.config)
        
        self.execution_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.is_cancelled = False
        self.current_method_index = 0
        self.results: List[BypassResult] = []
        
        self.setup_widgets()
        
    def setup_widgets(self):
        """Setup the execution widgets"""
        # Configure grid
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        
        # Header
        self.create_header()
        
        # Progress section
        self.create_progress_section()
        
        # Log output section
        self.create_log_section()
        
        # Footer with controls
        self.create_footer()
    
    def create_header(self):
        """Create header with execution info"""
        header_frame = ttk.Frame(self)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        header_frame.columnconfigure(0, weight=1)
        
        title_label = ttk.Label(
            header_frame,
            text="Executing FRP Bypass",
            font=('Arial', 14, 'bold')
        )
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        # Device and method info
        device_info_label = ttk.Label(
            header_frame,
            text=f"Device: {self.device.brand} {self.device.model} (Android {self.device.android_version})",
            font=('Arial', 10)
        )
        device_info_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        methods_info_label = ttk.Label(
            header_frame,
            text=f"Methods: {len(self.methods)} selected",
            font=('Arial', 10)
        )
        methods_info_label.grid(row=2, column=0, sticky=tk.W, pady=(2, 0))
        
        # Warning message
        warning_frame = ttk.Frame(header_frame)
        warning_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        warning_label = ttk.Label(
            warning_frame,
            text="⚠️ WARNING: Do not disconnect the device during bypass execution!",
            font=('Arial', 10, 'bold'),
            foreground='red'
        )
        warning_label.pack()
    
    def create_progress_section(self):
        """Create progress tracking section"""
        progress_frame = ttk.LabelFrame(self, text="Progress", padding="10")
        progress_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(1, weight=1)
        
        # Overall progress
        ttk.Label(progress_frame, text="Overall:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        self.overall_progress = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            maximum=len(self.methods)
        )
        self.overall_progress.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        self.overall_label = ttk.Label(progress_frame, text="0/0")
        self.overall_label.grid(row=0, column=2, sticky=tk.W)
        
        # Current method progress
        ttk.Label(progress_frame, text="Current:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        
        self.current_progress = ttk.Progressbar(
            progress_frame,
            mode='indeterminate'
        )
        self.current_progress.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 10), pady=(5, 0))
        
        self.current_label = ttk.Label(progress_frame, text="Ready")
        self.current_label.grid(row=1, column=2, sticky=tk.W, pady=(5, 0))
        
        # Status and timing
        status_frame = ttk.Frame(progress_frame)
        status_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        status_frame.columnconfigure(1, weight=1)
        
        ttk.Label(status_frame, text="Status:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        self.status_label = ttk.Label(
            status_frame,
            text="Ready to start",
            font=('Arial', 10, 'bold')
        )
        self.status_label.grid(row=0, column=1, sticky=tk.W)
        
        self.time_label = ttk.Label(
            status_frame,
            text="Elapsed: 00:00",
            font=('Arial', 9)
        )
        self.time_label.grid(row=0, column=2, sticky=tk.E)
    
    def create_log_section(self):
        """Create log output section"""
        log_frame = ttk.LabelFrame(self, text="Execution Log", padding="10")
        log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Log text widget with scrollbar
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=15,
            font=('Consolas', 9),
            wrap=tk.WORD,
            state='disabled'
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure text tags for different log levels
        self.log_text.tag_configure('INFO', foreground='black')
        self.log_text.tag_configure('SUCCESS', foreground='green', font=('Consolas', 9, 'bold'))
        self.log_text.tag_configure('WARNING', foreground='orange')
        self.log_text.tag_configure('ERROR', foreground='red', font=('Consolas', 9, 'bold'))
        self.log_text.tag_configure('DEBUG', foreground='gray')
        self.log_text.tag_configure('STEP', foreground='blue', font=('Consolas', 9, 'bold'))
    
    def create_footer(self):
        """Create footer with control buttons"""
        footer_frame = ttk.Frame(self)
        footer_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        footer_frame.columnconfigure(0, weight=1)
        
        # Button frame
        button_frame = ttk.Frame(footer_frame)
        button_frame.grid(row=0, column=1, sticky=tk.E)
        
        self.start_button = ttk.Button(
            button_frame,
            text="Start Bypass",
            command=self.start_execution
        )
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=self.cancel_execution,
            state='disabled'
        )
        self.cancel_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.save_log_button = ttk.Button(
            button_frame,
            text="Save Log",
            command=self.save_log,
            state='disabled'
        )
        self.save_log_button.pack(side=tk.LEFT)
    
    def log_message(self, message: str, level: str = 'INFO'):
        """Add a message to the log display"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, formatted_message, level)
        self.log_text.configure(state='disabled')
        self.log_text.see(tk.END)
        
        # Also log to file
        if level == 'ERROR':
            self.logger.error(message)
        elif level == 'WARNING':
            self.logger.warning(message)
        else:
            self.logger.info(message)
    
    def update_progress(self, method_index: int, method_name: str, step: str):
        """Update progress indicators"""
        # Update overall progress
        self.overall_progress['value'] = method_index
        self.overall_label.configure(text=f"{method_index}/{len(self.methods)}")
        
        # Update current method
        self.current_label.configure(text=f"{method_name}: {step}")
        
        # Update status
        if method_index < len(self.methods):
            self.status_label.configure(text=f"Executing method {method_index + 1} of {len(self.methods)}")
        else:
            self.status_label.configure(text="Execution completed")
    
    def update_timer(self, start_time: float):
        """Update the elapsed time display"""
        if self.is_running:
            elapsed = time.time() - start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            self.time_label.configure(text=f"Elapsed: {minutes:02d}:{seconds:02d}")
            
            # Schedule next update
            self.after(1000, lambda: self.update_timer(start_time))
    
    def start_execution(self):
        """Start the bypass execution"""
        if self.is_running:
            return
        
        # Confirm start
        if not messagebox.askyesno(
            "Confirm Execution",
            "Are you sure you want to start the FRP bypass?\n\n"
            "This process may take several minutes and should not be interrupted."
        ):
            return
        
        # Reset state
        self.is_running = True
        self.is_cancelled = False
        self.current_method_index = 0
        self.results.clear()
        
        # Update UI
        self.start_button.configure(state='disabled')
        self.cancel_button.configure(state='normal')
        self.current_progress.start()
        
        # Clear log
        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')
        
        # Log start
        self.log_message("=" * 60, 'STEP')
        self.log_message("FRP BYPASS EXECUTION STARTED", 'STEP')
        self.log_message("=" * 60, 'STEP')
        self.log_message(f"Device: {self.device.brand} {self.device.model}")
        self.log_message(f"Android Version: {self.device.android_version}")
        self.log_message(f"Methods to execute: {len(self.methods)}")
        self.log_message("")
        
        # Audit log
        self.audit_logger.log_bypass_attempt(
            device_id=self.device.serial_number,
            methods=[method.name for method in self.methods]
        )
        
        # Start execution thread
        self.execution_thread = threading.Thread(target=self._execute_bypass, daemon=True)
        self.execution_thread.start()
        
        # Start timer
        start_time = time.time()
        self.update_timer(start_time)
    
    def cancel_execution(self):
        """Cancel the bypass execution"""
        if not self.is_running:
            return
        
        if messagebox.askyesno(
            "Cancel Execution",
            "Are you sure you want to cancel the bypass execution?\n\n"
            "This may leave the device in an unstable state."
        ):
            self.is_cancelled = True
            self.log_message("Cancellation requested by user", 'WARNING')
    
    def _execute_bypass(self):
        """Execute bypass methods in background thread"""
        try:
            for i, method in enumerate(self.methods):
                if self.is_cancelled:
                    self.log_message("Execution cancelled by user", 'WARNING')
                    break
                
                self.current_method_index = i
                
                # Update UI on main thread
                self.after(0, lambda idx=i, name=method.name: 
                          self.update_progress(idx, name, "Starting"))
                
                self.log_message(f"Starting method {i + 1}/{len(self.methods)}: {method.name}", 'STEP')
                self.log_message(f"Description: {method.description}")
                self.log_message(f"Estimated time: {method.estimated_time_minutes} minutes")
                self.log_message(f"Success rate: {method.success_rate}%")
                self.log_message("")
                
                try:
                    # Execute the method
                    self.after(0, lambda idx=i, name=method.name: 
                              self.update_progress(idx, name, "Executing"))
                    
                    result = self.bypass_manager.execute_method(method, self.device)
                    self.results.append(result)
                    
                    if result.success:
                        self.log_message(f"✓ Method '{method.name}' completed successfully!", 'SUCCESS')
                        if result.message:
                            self.log_message(f"Result: {result.message}", 'SUCCESS')
                        
                        # If successful, we might want to stop here
                        if self._should_stop_on_success():
                            self.log_message("FRP bypass successful! Stopping execution.", 'SUCCESS')
                            break
                    else:
                        self.log_message(f"✗ Method '{method.name}' failed", 'ERROR')
                        if result.error:
                            self.log_message(f"Error: {result.error}", 'ERROR')
                        if result.message:
                            self.log_message(f"Details: {result.message}", 'WARNING')
                
                except Exception as e:
                    error_msg = f"Exception during method '{method.name}': {str(e)}"
                    self.log_message(error_msg, 'ERROR')
                    self.logger.exception(error_msg)
                    
                    # Create failed result
                    result = BypassResult(
                        success=False,
                        method=method.name,
                        error=str(e),
                        execution_time=0
                    )
                    self.results.append(result)
                
                self.log_message("")
                
                # Small delay between methods
                if not self.is_cancelled and i < len(self.methods) - 1:
                    time.sleep(1)
            
            # Execution completed
            self._execution_completed()
            
        except Exception as e:
            self.logger.exception(f"Fatal error during bypass execution: {e}")
            self.after(0, lambda: self.log_message(f"Fatal error: {str(e)}", 'ERROR'))
            self.after(0, self._execution_completed)
    
    def _should_stop_on_success(self) -> bool:
        """Determine if execution should stop after first success"""
        # For now, continue with all methods to gather data
        # In production, you might want to stop after first success
        return False
    
    def _execution_completed(self):
        """Handle execution completion"""
        self.is_running = False
        
        # Update UI
        self.start_button.configure(state='normal')
        self.cancel_button.configure(state='disabled')
        self.save_log_button.configure(state='normal')
        self.current_progress.stop()
        
        # Update progress
        self.update_progress(len(self.methods), "Completed", "Done")
        
        # Log summary
        self.log_message("=" * 60, 'STEP')
        self.log_message("EXECUTION SUMMARY", 'STEP')
        self.log_message("=" * 60, 'STEP')
        
        successful_methods = [r for r in self.results if r.success]
        failed_methods = [r for r in self.results if not r.success]
        
        self.log_message(f"Total methods executed: {len(self.results)}")
        self.log_message(f"Successful: {len(successful_methods)}", 'SUCCESS' if successful_methods else 'INFO')
        self.log_message(f"Failed: {len(failed_methods)}", 'ERROR' if failed_methods else 'INFO')
        
        if successful_methods:
            self.log_message("\nSuccessful methods:", 'SUCCESS')
            for result in successful_methods:
                self.log_message(f"  ✓ {result.method}", 'SUCCESS')
        
        if failed_methods:
            self.log_message("\nFailed methods:", 'ERROR')
            for result in failed_methods:
                self.log_message(f"  ✗ {result.method}: {result.error or 'Unknown error'}", 'ERROR')
        
        overall_success = len(successful_methods) > 0
        
        if overall_success:
            self.log_message("\n🎉 FRP BYPASS SUCCESSFUL!", 'SUCCESS')
            self.status_label.configure(text="Bypass successful!")
        else:
            self.log_message("\n❌ FRP BYPASS FAILED", 'ERROR')
            self.status_label.configure(text="Bypass failed")
        
        # Audit log
        self.audit_logger.log_bypass_result(
            device_id=self.device.serial_number,
            success=overall_success,
            methods_used=[r.method for r in self.results],
            execution_time=sum(r.execution_time for r in self.results)
        )
        
        # Show completion dialog
        if overall_success:
            messagebox.showinfo(
                "Bypass Successful",
                f"FRP bypass completed successfully!\n\n"
                f"Successful methods: {len(successful_methods)}\n"
                f"Total execution time: {sum(r.execution_time for r in self.results):.1f} seconds"
            )
        else:
            messagebox.showerror(
                "Bypass Failed",
                f"FRP bypass failed.\n\n"
                f"All {len(self.results)} methods were unsuccessful.\n"
                f"Please check the log for details."
            )
        
        # Notify completion
        self.completion_callback(overall_success, self.results)
    
    def save_log(self):
        """Save execution log to file"""
        from tkinter import filedialog
        
        filename = filedialog.asksaveasfilename(
            title="Save Execution Log",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialname=f"frp_bypass_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get(1.0, tk.END))
                
                messagebox.showinfo("Log Saved", f"Execution log saved to:\n{filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save log:\n{str(e)}")
    
    def get_results(self) -> List[BypassResult]:
        """Get execution results"""
        return self.results.copy()