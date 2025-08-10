#!/usr/bin/env python3
"""
Ownership Verification Dialog for FRP Freedom
Implements ethical ownership verification before bypass execution
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import re
import logging
from typing import Optional, Callable
from datetime import datetime
import hashlib
import json

from ..core.device_manager import DeviceInfo
from ..core.logger import AuditLogger

class OwnershipVerificationDialog:
    """Dialog for verifying device ownership"""
    
    def __init__(self, parent, device: DeviceInfo, callback: Callable[[bool, dict], None], config=None):
        self.parent = parent
        self.device = device
        self.callback = callback
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.audit_logger = AuditLogger(config) if config else None
        
        self.dialog = None
        self.verification_data = {}
        self.verification_passed = False
        
        self.create_dialog()
    
    def create_dialog(self):
        """Create the ownership verification dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Device Ownership Verification")
        self.dialog.geometry("600x700")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (700 // 2)
        self.dialog.geometry(f"600x700+{x}+{y}")
        
        # Configure grid
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(1, weight=1)
        
        # Create content
        self.create_header()
        self.create_verification_form()
        self.create_footer()
        
        # Handle dialog close
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_cancel)
    
    def create_header(self):
        """Create dialog header"""
        header_frame = ttk.Frame(self.dialog)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=20, pady=20)
        header_frame.columnconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(
            header_frame,
            text="🔒 Device Ownership Verification",
            font=('Arial', 16, 'bold')
        )
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        # Subtitle
        subtitle_label = ttk.Label(
            header_frame,
            text="Please verify that you are the legitimate owner of this device",
            font=('Arial', 11)
        )
        subtitle_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # Device info
        device_frame = ttk.LabelFrame(header_frame, text="Device Information", padding="10")
        device_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(15, 0))
        device_frame.columnconfigure(1, weight=1)
        
        # Device details
        details = [
            ("Brand:", self.device.brand or "Unknown"),
            ("Model:", self.device.model or "Unknown"),
            ("Serial Number:", self.device.serial_number or "Unknown"),
            ("Android Version:", self.device.android_version or "Unknown"),
            ("IMEI:", getattr(self.device, 'imei', 'Not available'))
        ]
        
        for i, (label, value) in enumerate(details):
            ttk.Label(device_frame, text=label, font=('Arial', 10, 'bold')).grid(
                row=i, column=0, sticky=tk.W, padx=(0, 10), pady=2
            )
            ttk.Label(device_frame, text=value, font=('Arial', 10)).grid(
                row=i, column=1, sticky=tk.W, pady=2
            )
    
    def create_verification_form(self):
        """Create the verification form"""
        form_frame = ttk.Frame(self.dialog)
        form_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=20)
        form_frame.columnconfigure(0, weight=1)
        
        # Create notebook for different verification methods
        self.notebook = ttk.Notebook(form_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create verification tabs
        self.create_purchase_verification_tab()
        self.create_account_verification_tab()
        self.create_document_verification_tab()
        self.create_declaration_tab()
    
    def create_purchase_verification_tab(self):
        """Create purchase verification tab"""
        self.purchase_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.purchase_frame, text="📄 Purchase Info")
        
        # Configure grid
        self.purchase_frame.columnconfigure(0, weight=1)
        
        # Instructions
        instructions = ttk.Label(
            self.purchase_frame,
            text="Provide purchase information to verify ownership:",
            font=('Arial', 11, 'bold')
        )
        instructions.pack(anchor=tk.W, pady=(10, 15))
        
        # Purchase date
        date_frame = ttk.Frame(self.purchase_frame)
        date_frame.pack(fill=tk.X, pady=5)
        date_frame.columnconfigure(1, weight=1)
        
        ttk.Label(date_frame, text="Purchase Date:", width=15).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.purchase_date_var = tk.StringVar()
        purchase_date_entry = ttk.Entry(date_frame, textvariable=self.purchase_date_var, width=20)
        purchase_date_entry.grid(row=0, column=1, sticky=tk.W)
        ttk.Label(date_frame, text="(YYYY-MM-DD)", font=('Arial', 9), foreground='gray').grid(row=0, column=2, sticky=tk.W, padx=(5, 0))
        
        # Purchase location
        location_frame = ttk.Frame(self.purchase_frame)
        location_frame.pack(fill=tk.X, pady=5)
        location_frame.columnconfigure(1, weight=1)
        
        ttk.Label(location_frame, text="Store/Retailer:", width=15).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.purchase_location_var = tk.StringVar()
        ttk.Entry(location_frame, textvariable=self.purchase_location_var).grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Receipt/Invoice number
        receipt_frame = ttk.Frame(self.purchase_frame)
        receipt_frame.pack(fill=tk.X, pady=5)
        receipt_frame.columnconfigure(1, weight=1)
        
        ttk.Label(receipt_frame, text="Receipt/Invoice:", width=15).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.receipt_number_var = tk.StringVar()
        ttk.Entry(receipt_frame, textvariable=self.receipt_number_var).grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Purchase price
        price_frame = ttk.Frame(self.purchase_frame)
        price_frame.pack(fill=tk.X, pady=5)
        price_frame.columnconfigure(1, weight=1)
        
        ttk.Label(price_frame, text="Purchase Price:", width=15).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.purchase_price_var = tk.StringVar()
        price_entry = ttk.Entry(price_frame, textvariable=self.purchase_price_var, width=15)
        price_entry.grid(row=0, column=1, sticky=tk.W)
        ttk.Label(price_frame, text="(approximate)", font=('Arial', 9), foreground='gray').grid(row=0, column=2, sticky=tk.W, padx=(5, 0))
    
    def create_account_verification_tab(self):
        """Create account verification tab"""
        self.account_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.account_frame, text="👤 Account Info")
        
        # Configure grid
        self.account_frame.columnconfigure(0, weight=1)
        
        # Instructions
        instructions = ttk.Label(
            self.account_frame,
            text="Provide account information associated with this device:",
            font=('Arial', 11, 'bold')
        )
        instructions.pack(anchor=tk.W, pady=(10, 15))
        
        # Google account
        google_frame = ttk.Frame(self.account_frame)
        google_frame.pack(fill=tk.X, pady=5)
        google_frame.columnconfigure(1, weight=1)
        
        ttk.Label(google_frame, text="Google Account:", width=15).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.google_account_var = tk.StringVar()
        ttk.Entry(google_frame, textvariable=self.google_account_var).grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Samsung account (if applicable)
        samsung_frame = ttk.Frame(self.account_frame)
        samsung_frame.pack(fill=tk.X, pady=5)
        samsung_frame.columnconfigure(1, weight=1)
        
        ttk.Label(samsung_frame, text="Samsung Account:", width=15).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.samsung_account_var = tk.StringVar()
        ttk.Entry(samsung_frame, textvariable=self.samsung_account_var).grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Phone number
        phone_frame = ttk.Frame(self.account_frame)
        phone_frame.pack(fill=tk.X, pady=5)
        phone_frame.columnconfigure(1, weight=1)
        
        ttk.Label(phone_frame, text="Phone Number:", width=15).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.phone_number_var = tk.StringVar()
        ttk.Entry(phone_frame, textvariable=self.phone_number_var).grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Recovery email
        recovery_frame = ttk.Frame(self.account_frame)
        recovery_frame.pack(fill=tk.X, pady=5)
        recovery_frame.columnconfigure(1, weight=1)
        
        ttk.Label(recovery_frame, text="Recovery Email:", width=15).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.recovery_email_var = tk.StringVar()
        ttk.Entry(recovery_frame, textvariable=self.recovery_email_var).grid(row=0, column=1, sticky=(tk.W, tk.E))
    
    def create_document_verification_tab(self):
        """Create document verification tab"""
        self.document_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.document_frame, text="📎 Documents")
        
        # Configure grid
        self.document_frame.columnconfigure(0, weight=1)
        
        # Instructions
        instructions = ttk.Label(
            self.document_frame,
            text="Upload supporting documents (optional but recommended):",
            font=('Arial', 11, 'bold')
        )
        instructions.pack(anchor=tk.W, pady=(10, 15))
        
        # Document upload section
        self.documents = []
        
        # Purchase receipt
        receipt_frame = ttk.LabelFrame(self.document_frame, text="Purchase Receipt/Invoice", padding="10")
        receipt_frame.pack(fill=tk.X, pady=5)
        receipt_frame.columnconfigure(1, weight=1)
        
        self.receipt_file_var = tk.StringVar(value="No file selected")
        ttk.Label(receipt_frame, textvariable=self.receipt_file_var).grid(row=0, column=0, sticky=tk.W)
        
        receipt_button = ttk.Button(
            receipt_frame,
            text="Browse...",
            command=lambda: self.browse_file("receipt", self.receipt_file_var)
        )
        receipt_button.grid(row=0, column=1, sticky=tk.E)
        
        # Warranty card
        warranty_frame = ttk.LabelFrame(self.document_frame, text="Warranty Card/Certificate", padding="10")
        warranty_frame.pack(fill=tk.X, pady=5)
        warranty_frame.columnconfigure(1, weight=1)
        
        self.warranty_file_var = tk.StringVar(value="No file selected")
        ttk.Label(warranty_frame, textvariable=self.warranty_file_var).grid(row=0, column=0, sticky=tk.W)
        
        warranty_button = ttk.Button(
            warranty_frame,
            text="Browse...",
            command=lambda: self.browse_file("warranty", self.warranty_file_var)
        )
        warranty_button.grid(row=0, column=1, sticky=tk.E)
        
        # ID document
        id_frame = ttk.LabelFrame(self.document_frame, text="Government ID (for verification)", padding="10")
        id_frame.pack(fill=tk.X, pady=5)
        id_frame.columnconfigure(1, weight=1)
        
        self.id_file_var = tk.StringVar(value="No file selected")
        ttk.Label(id_frame, textvariable=self.id_file_var).grid(row=0, column=0, sticky=tk.W)
        
        id_button = ttk.Button(
            id_frame,
            text="Browse...",
            command=lambda: self.browse_file("id", self.id_file_var)
        )
        id_button.grid(row=0, column=1, sticky=tk.E)
        
        # Privacy notice
        privacy_label = ttk.Label(
            self.document_frame,
            text="Note: Documents are processed locally and not transmitted anywhere.",
            font=('Arial', 9, 'italic'),
            foreground='gray'
        )
        privacy_label.pack(anchor=tk.W, pady=(10, 0))
    
    def create_declaration_tab(self):
        """Create legal declaration tab"""
        self.declaration_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.declaration_frame, text="⚖️ Declaration")
        
        # Configure grid
        self.declaration_frame.columnconfigure(0, weight=1)
        self.declaration_frame.rowconfigure(1, weight=1)
        
        # Instructions
        instructions = ttk.Label(
            self.declaration_frame,
            text="Please read and accept the following declaration:",
            font=('Arial', 11, 'bold')
        )
        instructions.pack(anchor=tk.W, pady=(10, 15))
        
        # Declaration text
        declaration_text = tk.Text(
            self.declaration_frame,
            height=15,
            wrap=tk.WORD,
            font=('Arial', 10),
            state='disabled',
            bg='#f0f0f0'
        )
        declaration_text.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(declaration_text, orient="vertical", command=declaration_text.yview)
        declaration_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Declaration content
        declaration_content = """
LEGAL DECLARATION AND TERMS OF USE

By proceeding with this FRP bypass operation, I hereby declare and confirm that:

1. OWNERSHIP VERIFICATION
   • I am the legitimate owner of the device being processed
   • I have legal authority to modify this device
   • The device was not stolen, lost, or obtained through illegal means
   • I have provided accurate information regarding device ownership

2. LEGITIMATE USE
   • I am using this tool for legitimate device recovery purposes only
   • I have forgotten my Google account credentials or lost access to my account
   • I am not attempting to bypass security on a device that does not belong to me
   • I understand this tool is intended for personal device recovery only

3. LEGAL COMPLIANCE
   • I understand that bypassing FRP on devices I do not own may violate local laws
   • I am solely responsible for ensuring my use complies with applicable laws
   • I will not use this tool for any illegal or unauthorized purposes
   • I acknowledge that misuse of this tool may result in legal consequences

4. RISK ACKNOWLEDGMENT
   • I understand that device modification carries inherent risks
   • I accept full responsibility for any damage to my device
   • I understand that this process may void my device warranty
   • I acknowledge that the bypass process may fail or cause device malfunction

5. DATA AND PRIVACY
   • I understand that this process may result in data loss
   • I have backed up any important data before proceeding
   • I consent to the logging of this bypass attempt for security purposes
   • I understand that verification information is processed locally only

6. NO WARRANTY
   • This tool is provided "as is" without any warranties
   • The developers are not liable for any damages or consequences
   • I use this tool at my own risk and discretion
   • No guarantee is made regarding bypass success or device functionality

By checking the boxes below and proceeding, I confirm that I have read, understood, and agree to be bound by these terms. I declare under penalty of perjury that the information provided is true and accurate to the best of my knowledge.

Date: {date}
Device Serial: {serial}
""".format(
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            serial=self.device.serial_number or "Unknown"
        )
        
        declaration_text.configure(state='normal')
        declaration_text.insert(1.0, declaration_content)
        declaration_text.configure(state='disabled')
        
        # Checkboxes
        checkbox_frame = ttk.Frame(self.declaration_frame)
        checkbox_frame.pack(fill=tk.X)
        
        self.ownership_var = tk.BooleanVar()
        ownership_check = ttk.Checkbutton(
            checkbox_frame,
            text="I confirm that I am the legitimate owner of this device",
            variable=self.ownership_var,
            command=self.update_verification_status
        )
        ownership_check.pack(anchor=tk.W, pady=2)
        
        self.legal_var = tk.BooleanVar()
        legal_check = ttk.Checkbutton(
            checkbox_frame,
            text="I agree to the terms and conditions stated above",
            variable=self.legal_var,
            command=self.update_verification_status
        )
        legal_check.pack(anchor=tk.W, pady=2)
        
        self.responsibility_var = tk.BooleanVar()
        responsibility_check = ttk.Checkbutton(
            checkbox_frame,
            text="I accept full responsibility for the consequences of this action",
            variable=self.responsibility_var,
            command=self.update_verification_status
        )
        responsibility_check.pack(anchor=tk.W, pady=2)
    
    def create_footer(self):
        """Create dialog footer"""
        footer_frame = ttk.Frame(self.dialog)
        footer_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=20, pady=20)
        footer_frame.columnconfigure(0, weight=1)
        
        # Status label
        self.status_label = ttk.Label(
            footer_frame,
            text="Please complete all verification steps",
            font=('Arial', 10),
            foreground='orange'
        )
        self.status_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # Buttons
        button_frame = ttk.Frame(footer_frame)
        button_frame.grid(row=1, column=0, sticky=tk.E)
        
        cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=self.on_cancel
        )
        cancel_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.verify_button = ttk.Button(
            button_frame,
            text="Verify & Proceed",
            command=self.on_verify,
            state='disabled'
        )
        self.verify_button.pack(side=tk.LEFT)
    
    def browse_file(self, doc_type: str, var: tk.StringVar):
        """Browse for document file"""
        filename = filedialog.askopenfilename(
            title=f"Select {doc_type.title()} Document",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.gif *.bmp"),
                ("PDF files", "*.pdf"),
                ("All files", "*.*")
            ]
        )
        
        if filename:
            # Store file info
            self.documents.append({
                'type': doc_type,
                'path': filename,
                'name': filename.split('/')[-1]
            })
            
            var.set(filename.split('/')[-1])
            self.update_verification_status()
    
    def update_verification_status(self):
        """Update verification status and enable/disable verify button"""
        # Check if all required declarations are checked
        declarations_complete = (
            self.ownership_var.get() and
            self.legal_var.get() and
            self.responsibility_var.get()
        )
        
        # Check if at least some verification info is provided
        info_provided = (
            self.purchase_date_var.get().strip() or
            self.purchase_location_var.get().strip() or
            self.google_account_var.get().strip() or
            self.phone_number_var.get().strip() or
            len(self.documents) > 0
        )
        
        if declarations_complete and info_provided:
            self.verify_button.configure(state='normal')
            self.status_label.configure(
                text="✓ Verification requirements met",
                foreground='green'
            )
            self.verification_passed = True
        elif declarations_complete:
            self.verify_button.configure(state='disabled')
            self.status_label.configure(
                text="Please provide at least some ownership information",
                foreground='orange'
            )
            self.verification_passed = False
        else:
            self.verify_button.configure(state='disabled')
            self.status_label.configure(
                text="Please accept all declarations to proceed",
                foreground='red'
            )
            self.verification_passed = False
    
    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def validate_date(self, date_str: str) -> bool:
        """Validate date format (YYYY-MM-DD)"""
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(pattern, date_str):
            return False
        
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    def collect_verification_data(self) -> dict:
        """Collect all verification data"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'device_info': {
                'serial': self.device.serial_number,
                'brand': self.device.brand,
                'model': self.device.model,
                'android_version': self.device.android_version
            },
            'purchase_info': {
                'date': self.purchase_date_var.get().strip(),
                'location': self.purchase_location_var.get().strip(),
                'receipt': self.receipt_number_var.get().strip(),
                'price': self.purchase_price_var.get().strip()
            },
            'account_info': {
                'google_account': self.google_account_var.get().strip(),
                'samsung_account': self.samsung_account_var.get().strip(),
                'phone_number': self.phone_number_var.get().strip(),
                'recovery_email': self.recovery_email_var.get().strip()
            },
            'documents': self.documents,
            'declarations': {
                'ownership_confirmed': self.ownership_var.get(),
                'terms_accepted': self.legal_var.get(),
                'responsibility_accepted': self.responsibility_var.get()
            }
        }
        
        # Generate verification hash
        data_str = json.dumps(data, sort_keys=True)
        data['verification_hash'] = hashlib.sha256(data_str.encode()).hexdigest()[:16]
        
        return data
    
    def on_verify(self):
        """Handle verification confirmation"""
        # Validate inputs
        errors = []
        
        # Validate email addresses
        google_email = self.google_account_var.get().strip()
        if google_email and not self.validate_email(google_email):
            errors.append("Invalid Google account email format")
        
        samsung_email = self.samsung_account_var.get().strip()
        if samsung_email and not self.validate_email(samsung_email):
            errors.append("Invalid Samsung account email format")
        
        recovery_email = self.recovery_email_var.get().strip()
        if recovery_email and not self.validate_email(recovery_email):
            errors.append("Invalid recovery email format")
        
        # Validate purchase date
        purchase_date = self.purchase_date_var.get().strip()
        if purchase_date and not self.validate_date(purchase_date):
            errors.append("Invalid purchase date format (use YYYY-MM-DD)")
        
        if errors:
            messagebox.showerror("Validation Error", "\n".join(errors))
            return
        
        # Collect verification data
        self.verification_data = self.collect_verification_data()
        
        # Log verification attempt
        self.audit_logger.log_ownership_verification(
            device_id=self.device.serial_number,
            verification_method="manual_form",
            verification_data=self.verification_data,
            success=True
        )
        
        # Show final confirmation
        if messagebox.askyesno(
            "Final Confirmation",
            "You have confirmed ownership of this device and accepted all terms.\n\n"
            "This verification will be logged for audit purposes.\n\n"
            "Proceed with FRP bypass?"
        ):
            self.verification_passed = True
            self.dialog.destroy()
            self.callback(True, self.verification_data)
        
    def on_cancel(self):
        """Handle dialog cancellation"""
        # Log cancellation
        self.audit_logger.log_ownership_verification(
            device_id=self.device.serial_number,
            verification_method="manual_form",
            verification_data={},
            success=False
        )
        
        self.verification_passed = False
        self.dialog.destroy()
        self.callback(False, {})
    
    def show(self):
        """Show the dialog and wait for result"""
        self.dialog.wait_window()
        return self.verification_passed, self.verification_data

def show_ownership_verification(parent, device: DeviceInfo, config=None) -> tuple[bool, dict]:
    """Show ownership verification dialog and return result"""
    result = {'verified': False, 'data': {}}
    
    def callback(verified: bool, data: dict):
        result['verified'] = verified
        result['data'] = data
    
    dialog = OwnershipVerificationDialog(parent, device, callback, config)
    dialog.show()
    
    return result['verified'], result['data']