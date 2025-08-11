#!/usr/bin/env python3
"""
Method Selection Frame for FRP Freedom
Implements the method selection step of the wizard with AI recommendations
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging
from typing import List, Callable, Optional

from ..core.device_manager import DeviceInfo
from ..bypass.bypass_manager import BypassManager
from ..bypass.types import BypassMethod
from ..ai import AIEngine

class MethodSelectionFrame(ttk.Frame):
    """Frame for bypass method selection with AI recommendations"""
    
    def __init__(self, parent, device: DeviceInfo, bypass_manager: BypassManager, 
                 selection_callback: Callable[[List[BypassMethod]], None]):
        super().__init__(parent)
        self.device = device
        self.bypass_manager = bypass_manager
        self.selection_callback = selection_callback
        self.logger = logging.getLogger(__name__)
        
        self.available_methods: List[BypassMethod] = []
        self.selected_methods: List[BypassMethod] = []
        self.ai_analysis = None
        
        # Check if device is None
        if self.device is None:
            self.show_no_device_error()
            return
            
        self.setup_widgets()
        self.load_methods()
    
    def setup_widgets(self):
        """Setup the method selection interface"""
        # Configure grid weights
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header frame
        header_frame = ttk.Frame(self)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        header_frame.grid_columnconfigure(1, weight=1)
        
        # Device info
        device_label = ttk.Label(header_frame, text="Selected Device:", font=('TkDefaultFont', 10, 'bold'))
        device_label.grid(row=0, column=0, sticky=tk.W)
        
        device_info = f"{self.device.brand} {self.device.model} (Android {self.device.android_version})"
        device_info_label = ttk.Label(header_frame, text=device_info)
        device_info_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        # AI analysis button
        self.ai_button = ttk.Button(header_frame, text="Get AI Analysis", command=self.get_ai_analysis)
        self.ai_button.grid(row=0, column=2, padx=(10, 0))
        
        # Main content frame
        content_frame = ttk.Frame(self)
        content_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=(0, 10))
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)
        
        # Create notebook for different views
        self.notebook = ttk.Notebook(content_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Method list tab
        self.create_method_list_tab()
        
        # AI recommendations tab
        self.create_ai_recommendations_tab()
        
        # Method details tab
        self.create_method_details_tab()
        
        # Bottom frame for actions
        bottom_frame = ttk.Frame(content_frame)
        bottom_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Selection info
        self.selection_label = ttk.Label(bottom_frame, text="No methods selected")
        self.selection_label.pack(side=tk.LEFT)
        
        # Action buttons
        button_frame = ttk.Frame(bottom_frame)
        button_frame.pack(side=tk.RIGHT)
        
        self.clear_button = ttk.Button(button_frame, text="Clear Selection", command=self.clear_selection)
        self.clear_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.select_all_button = ttk.Button(button_frame, text="Select Recommended", command=self.select_recommended)
        self.select_all_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.confirm_button = ttk.Button(button_frame, text="Confirm Selection", command=self.confirm_selection)
        self.confirm_button.pack(side=tk.LEFT)
    
    def create_method_list_tab(self):
        """Create the method list tab"""
        list_frame = ttk.Frame(self.notebook)
        self.notebook.add(list_frame, text="Available Methods")
        
        # Configure grid
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(1, weight=1)
        
        # Instructions
        instructions = ttk.Label(list_frame, text="Select bypass methods to attempt (in order):")
        instructions.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        # Method treeview
        columns = ('Method', 'Category', 'Risk', 'Success Rate', 'Time', 'Description')
        self.method_tree = ttk.Treeview(list_frame, columns=columns, show='headings', selectmode='extended')
        
        # Configure columns
        self.method_tree.heading('Method', text='Method')
        self.method_tree.heading('Category', text='Category')
        self.method_tree.heading('Risk', text='Risk Level')
        self.method_tree.heading('Success Rate', text='Success Rate')
        self.method_tree.heading('Time', text='Est. Time (min)')
        self.method_tree.heading('Description', text='Description')
        
        self.method_tree.column('Method', width=150)
        self.method_tree.column('Category', width=80)
        self.method_tree.column('Risk', width=80)
        self.method_tree.column('Success Rate', width=100)
        self.method_tree.column('Time', width=100)
        self.method_tree.column('Description', width=300)
        
        self.method_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.method_tree.yview)
        scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S), pady=5)
        self.method_tree.configure(yscrollcommand=scrollbar.set)
        
        # Bind events
        self.method_tree.bind('<<TreeviewSelect>>', self.on_method_select)
        self.method_tree.bind('<Double-1>', self.toggle_method_selection)
    
    def create_ai_recommendations_tab(self):
        """Create the AI recommendations tab"""
        ai_frame = ttk.Frame(self.notebook)
        self.notebook.add(ai_frame, text="AI Recommendations")
        
        # Configure grid
        ai_frame.grid_columnconfigure(0, weight=1)
        ai_frame.grid_rowconfigure(1, weight=1)
        
        # Header
        header_label = ttk.Label(ai_frame, text="AI Analysis & Recommendations", font=('TkDefaultFont', 12, 'bold'))
        header_label.grid(row=0, column=0, pady=10)
        
        # Analysis text area
        self.ai_text = tk.Text(ai_frame, wrap=tk.WORD, font=('TkDefaultFont', 10), state='disabled')
        self.ai_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=(0, 10))
        
        # Scrollbar for text
        ai_scrollbar = ttk.Scrollbar(ai_frame, orient=tk.VERTICAL, command=self.ai_text.yview)
        ai_scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S), pady=(0, 10))
        self.ai_text.configure(yscrollcommand=ai_scrollbar.set)
        
        # Initial message
        self.ai_text.configure(state='normal')
        self.ai_text.insert('1.0', "Click 'Get AI Analysis' to receive intelligent recommendations for this device.")
        self.ai_text.configure(state='disabled')
    
    def create_method_details_tab(self):
        """Create the method details tab"""
        details_frame = ttk.Frame(self.notebook)
        self.notebook.add(details_frame, text="Method Details")
        
        # Configure grid
        details_frame.grid_columnconfigure(0, weight=1)
        details_frame.grid_rowconfigure(1, weight=1)
        
        # Header
        self.details_header = ttk.Label(details_frame, text="Select a method to view details", font=('TkDefaultFont', 12, 'bold'))
        self.details_header.grid(row=0, column=0, pady=10)
        
        # Details text area
        self.details_text = tk.Text(details_frame, wrap=tk.WORD, font=('TkDefaultFont', 10), state='disabled')
        self.details_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=(0, 10))
        
        # Scrollbar for details
        details_scrollbar = ttk.Scrollbar(details_frame, orient=tk.VERTICAL, command=self.details_text.yview)
        details_scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S), pady=(0, 10))
        self.details_text.configure(yscrollcommand=details_scrollbar.set)
    
    def load_methods(self):
        """Load available methods for the selected device"""
        try:
            self.available_methods = self.bypass_manager.get_recommended_methods(self.device)
            self.populate_method_tree()
            self.logger.info(f"Loaded {len(self.available_methods)} methods for device {self.device.serial}")
        except Exception as e:
            self.logger.error(f"Failed to load methods: {e}")
            messagebox.showerror("Error", f"Failed to load bypass methods: {e}")
    
    def populate_method_tree(self):
        """Populate the method tree with available methods"""
        # Clear existing items
        for item in self.method_tree.get_children():
            self.method_tree.delete(item)
        
        # Add methods
        for method in self.available_methods:
            values = (
                method.name,
                method.category.title(),
                method.risk_level.title(),
                f"{method.success_rate:.1%}",
                f"{method.estimated_time}",
                method.description
            )
            self.method_tree.insert('', 'end', values=values, tags=(method.name,))
        
        # Configure tags for risk levels
        self.method_tree.tag_configure('low_risk', background='#e8f5e8')
        self.method_tree.tag_configure('medium_risk', background='#fff3cd')
        self.method_tree.tag_configure('high_risk', background='#f8d7da')
    
    def get_ai_analysis(self):
        """Get AI analysis for the device"""
        def run_analysis():
            try:
                self.ai_button.configure(state='disabled', text='Analyzing...')
                
                # Get AI analysis
                analysis = self.bypass_manager.get_ai_device_analysis(self.device)
                self.ai_analysis = analysis
                
                # Update UI in main thread
                self.after(0, self.display_ai_analysis, analysis)
                
            except Exception as e:
                self.logger.error(f"AI analysis failed: {e}")
                self.after(0, self.display_ai_error, str(e))
            finally:
                self.after(0, lambda: self.ai_button.configure(state='normal', text='Get AI Analysis'))
        
        # Run analysis in background thread
        analysis_thread = threading.Thread(target=run_analysis, daemon=True)
        analysis_thread.start()
    
    def display_ai_analysis(self, analysis):
        """Display AI analysis results"""
        self.ai_text.configure(state='normal')
        self.ai_text.delete('1.0', tk.END)
        
        # Format analysis text
        profile = analysis.get('device_profile', {})
        
        analysis_text = f"""AI DEVICE ANALYSIS
{'=' * 50}

Device: {self.device.brand} {self.device.model}
Android Version: {self.device.android_version}
FRP Status: {self.device.frp_status if self.device.frp_status else 'Unknown'}

SECURITY ASSESSMENT
{'-' * 30}
{analysis.get('security_assessment', 'No assessment available')}

FRP COMPLEXITY: {profile.get('frp_complexity', 'Unknown').upper()}
VULNERABILITY SCORE: {profile.get('vulnerability_score', 0):.2f}/1.0

RECOMMENDED METHODS
{'-' * 30}
"""
        
        recommended_methods = profile.get('recommended_methods', [])
        success_probs = profile.get('success_probabilities', {})
        
        if recommended_methods:
            for i, method_name in enumerate(recommended_methods[:5], 1):
                method = next((m for m in self.available_methods if m.name == method_name), None)
                if method:
                    prob = success_probs.get(method_name, 0.5)
                    analysis_text += f"{i}. {method.description}\n"
                    analysis_text += f"   Success Probability: {prob:.1%}\n"
                    analysis_text += f"   Risk Level: {method.risk_level.title()}\n\n"
        else:
            analysis_text += "No specific recommendations available.\n\n"
        
        analysis_text += f"""BYPASS STRATEGY
{'-' * 30}
{analysis.get('bypass_strategy', 'No strategy available')}

RECOMMENDATIONS
{'-' * 30}
• Start with the highest probability methods
• Consider risk levels based on your comfort level
• Have backup methods ready in case primary methods fail
• Monitor device responses carefully during execution
"""
        
        self.ai_text.insert('1.0', analysis_text)
        self.ai_text.configure(state='disabled')
        
        # Switch to AI tab
        self.notebook.select(1)
    
    def display_ai_error(self, error_msg):
        """Display AI analysis error"""
        self.ai_text.configure(state='normal')
        self.ai_text.delete('1.0', tk.END)
        self.ai_text.insert('1.0', f"AI Analysis Error:\n\n{error_msg}\n\nPlease try again or proceed with manual method selection.")
        self.ai_text.configure(state='disabled')
    
    def on_method_select(self, event):
        """Handle method selection in tree"""
        selection = self.method_tree.selection()
        if selection:
            item = selection[0]
            method_name = self.method_tree.item(item)['values'][0]
            method = next((m for m in self.available_methods if m.name == method_name), None)
            if method:
                self.show_method_details(method)
    
    def show_method_details(self, method: BypassMethod):
        """Show detailed information about a method"""
        self.details_header.configure(text=f"Method Details: {method.name}")
        
        self.details_text.configure(state='normal')
        self.details_text.delete('1.0', tk.END)
        
        details_text = f"""METHOD: {method.name}
{'=' * 50}

DESCRIPTION
{method.description}

CATEGORY: {method.category.title()}
RISK LEVEL: {method.risk_level.title()}
SUCCESS RATE: {method.success_rate:.1%}
ESTIMATED TIME: {method.estimated_time} minutes

REQUIREMENTS
{'-' * 20}
"""
        
        for req in method.requirements:
            details_text += f"• {req}\n"
        
        details_text += f"\nSUPPORTED DEVICES\n{'-' * 20}\n"
        for device in method.supported_devices:
            details_text += f"• {device}\n"
        
        details_text += f"\nANDROID VERSIONS\n{'-' * 20}\n"
        for version in method.android_versions:
            details_text += f"• Android {version}\n"
        
        # Add AI-specific information if available
        if self.ai_analysis and 'device_profile' in self.ai_analysis:
            success_probs = self.ai_analysis['device_profile'].get('success_probabilities', {})
            if method.name in success_probs:
                ai_prob = success_probs[method.name]
                details_text += f"\nAI ANALYSIS\n{'-' * 20}\n"
                details_text += f"AI Success Probability: {ai_prob:.1%}\n"
                
                if ai_prob > method.success_rate:
                    details_text += "AI predicts higher success rate than baseline for this device.\n"
                elif ai_prob < method.success_rate:
                    details_text += "AI predicts lower success rate than baseline for this device.\n"
                else:
                    details_text += "AI prediction aligns with baseline success rate.\n"
        
        self.details_text.insert('1.0', details_text)
        self.details_text.configure(state='disabled')
        
        # Switch to details tab
        self.notebook.select(2)
    
    def toggle_method_selection(self, event):
        """Toggle method selection on double-click"""
        selection = self.method_tree.selection()
        if selection:
            item = selection[0]
            method_name = self.method_tree.item(item)['values'][0]
            method = next((m for m in self.available_methods if m.name == method_name), None)
            
            if method:
                if method in self.selected_methods:
                    self.selected_methods.remove(method)
                    self.method_tree.set(item, 'Method', method.name)
                else:
                    self.selected_methods.append(method)
                    self.method_tree.set(item, 'Method', f"✓ {method.name}")
                
                self.update_selection_display()
    
    def select_recommended(self):
        """Select AI recommended methods"""
        if not self.ai_analysis or 'device_profile' not in self.ai_analysis:
            messagebox.showinfo("Info", "Please run AI analysis first to get recommendations.")
            return
        
        recommended_names = self.ai_analysis['device_profile'].get('recommended_methods', [])
        self.selected_methods = [m for m in self.available_methods if m.name in recommended_names[:3]]  # Top 3
        
        # Update tree display
        for item in self.method_tree.get_children():
            method_name = self.method_tree.item(item)['values'][0].replace('✓ ', '')
            if any(m.name == method_name for m in self.selected_methods):
                self.method_tree.set(item, 'Method', f"✓ {method_name}")
            else:
                self.method_tree.set(item, 'Method', method_name)
        
        self.update_selection_display()
    
    def clear_selection(self):
        """Clear all selected methods"""
        self.selected_methods = []
        
        # Update tree display
        for item in self.method_tree.get_children():
            method_name = self.method_tree.item(item)['values'][0].replace('✓ ', '')
            self.method_tree.set(item, 'Method', method_name)
        
        self.update_selection_display()
    
    def update_selection_display(self):
        """Update the selection display"""
        count = len(self.selected_methods)
        if count == 0:
            self.selection_label.configure(text="No methods selected")
        elif count == 1:
            self.selection_label.configure(text="1 method selected")
        else:
            self.selection_label.configure(text=f"{count} methods selected")
    
    def confirm_selection(self):
        """Confirm method selection and proceed"""
        if not self.selected_methods:
            messagebox.showwarning("Warning", "Please select at least one bypass method.")
            return
        
        # Show confirmation dialog
        method_names = [m.name for m in self.selected_methods]
        message = f"""Confirm Method Selection:

Selected Methods (in order):
{chr(10).join(f'{i+1}. {name}' for i, name in enumerate(method_names))}

These methods will be attempted in the order shown.
Proceed with bypass execution?"""
        
        if messagebox.askyesno("Confirm Selection", message):
            self.selection_callback(self.selected_methods)
    
    def get_selected_methods(self) -> List[BypassMethod]:
        """Get the currently selected methods"""
        return self.selected_methods.copy()
    
    def show_no_device_error(self):
        """Show error when no device is selected"""
        error_frame = ttk.Frame(self)
        error_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Error message
        error_label = ttk.Label(
            error_frame, 
            text="No Device Selected", 
            font=('TkDefaultFont', 16, 'bold'),
            foreground='red'
        )
        error_label.pack(pady=(50, 20))
        
        message_label = ttk.Label(
            error_frame,
            text="Please go back and select a device before choosing bypass methods.",
            font=('TkDefaultFont', 12)
        )
        message_label.pack(pady=10)
        
        # Back button
        back_button = ttk.Button(
            error_frame,
            text="Go Back to Device Selection",
            command=lambda: self.master.master.go_back()  # Navigate back
        )
        back_button.pack(pady=20)