#!/usr/bin/env python3
"""
AI Notification System for FRP Freedom
Provides intelligent notifications and alerts based on AI analysis
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import logging

class NotificationType(Enum):
    """Types of AI notifications"""
    INFO = "info"
    WARNING = "warning"
    SUCCESS = "success"
    ERROR = "error"
    AI_INSIGHT = "ai_insight"
    RECOMMENDATION = "recommendation"

@dataclass
class AINotification:
    """AI notification data structure"""
    id: str
    title: str
    message: str
    notification_type: NotificationType
    timestamp: float
    priority: int = 1  # 1=low, 2=medium, 3=high
    action_callback: Optional[Callable] = None
    action_text: Optional[str] = None
    auto_dismiss: bool = True
    dismiss_after: int = 5000  # milliseconds
    data: Optional[Dict] = None

class AINotificationSystem:
    """AI-powered notification system"""
    
    def __init__(self, parent_window):
        self.parent_window = parent_window
        self.logger = logging.getLogger(__name__)
        self.notifications: List[AINotification] = []
        self.notification_widgets: Dict[str, tk.Toplevel] = {}
        self.notification_queue: List[AINotification] = []
        self.max_notifications = 3
        self.notification_position = 0
        
        # Start notification processor
        self.start_notification_processor()
    
    def show_notification(self, notification: AINotification):
        """Show an AI notification"""
        try:
            # Add to queue if too many notifications are showing
            if len(self.notification_widgets) >= self.max_notifications:
                self.notification_queue.append(notification)
                return
            
            # Create notification window
            self.create_notification_window(notification)
            
        except Exception as e:
            self.logger.error(f"Failed to show notification: {e}")
    
    def create_notification_window(self, notification: AINotification):
        """Create a notification window"""
        # Create toplevel window
        window = tk.Toplevel(self.parent_window)
        window.title("AI Notification")
        window.geometry("350x120")
        window.resizable(False, False)
        window.attributes('-topmost', True)
        
        # Position window
        self.position_notification_window(window)
        
        # Configure window style based on type
        self.configure_notification_style(window, notification.notification_type)
        
        # Create content frame
        content_frame = ttk.Frame(window, padding="10")
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Icon and title frame
        header_frame = ttk.Frame(content_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Icon
        icon = self.get_notification_icon(notification.notification_type)
        icon_label = ttk.Label(header_frame, text=icon, font=('Arial', 16))
        icon_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Title
        title_label = ttk.Label(
            header_frame,
            text=notification.title,
            font=('Arial', 11, 'bold')
        )
        title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Close button
        close_button = ttk.Button(
            header_frame,
            text="×",
            width=3,
            command=lambda: self.dismiss_notification(notification.id)
        )
        close_button.pack(side=tk.RIGHT)
        
        # Message
        message_label = ttk.Label(
            content_frame,
            text=notification.message,
            font=('Arial', 9),
            wraplength=300
        )
        message_label.pack(fill=tk.X, pady=(0, 10))
        
        # Action button (if provided)
        if notification.action_callback and notification.action_text:
            action_button = ttk.Button(
                content_frame,
                text=notification.action_text,
                command=lambda: self.handle_notification_action(notification)
            )
            action_button.pack(side=tk.RIGHT)
        
        # Store window reference
        self.notification_widgets[notification.id] = window
        
        # Auto-dismiss if enabled
        if notification.auto_dismiss:
            window.after(
                notification.dismiss_after,
                lambda: self.dismiss_notification(notification.id)
            )
    
    def position_notification_window(self, window):
        """Position notification window on screen"""
        # Get screen dimensions
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        
        # Calculate position (bottom-right corner)
        x = screen_width - 370  # window width + margin
        y = screen_height - 150 - (self.notification_position * 130)
        
        window.geometry(f"+{x}+{y}")
        self.notification_position += 1
    
    def configure_notification_style(self, window, notification_type: NotificationType):
        """Configure notification window style based on type"""
        colors = {
            NotificationType.INFO: '#e3f2fd',
            NotificationType.WARNING: '#fff3e0',
            NotificationType.SUCCESS: '#e8f5e8',
            NotificationType.ERROR: '#ffebee',
            NotificationType.AI_INSIGHT: '#f3e5f5',
            NotificationType.RECOMMENDATION: '#e0f2f1'
        }
        
        bg_color = colors.get(notification_type, '#f5f5f5')
        window.configure(bg=bg_color)
    
    def get_notification_icon(self, notification_type: NotificationType) -> str:
        """Get icon for notification type"""
        icons = {
            NotificationType.INFO: 'ℹ️',
            NotificationType.WARNING: '⚠️',
            NotificationType.SUCCESS: '✅',
            NotificationType.ERROR: '❌',
            NotificationType.AI_INSIGHT: '🤖',
            NotificationType.RECOMMENDATION: '💡'
        }
        
        return icons.get(notification_type, 'ℹ️')
    
    def dismiss_notification(self, notification_id: str):
        """Dismiss a notification"""
        try:
            if notification_id in self.notification_widgets:
                window = self.notification_widgets[notification_id]
                window.destroy()
                del self.notification_widgets[notification_id]
                
                # Reposition remaining notifications
                self.reposition_notifications()
                
                # Show next notification from queue
                self.show_next_from_queue()
                
        except Exception as e:
            self.logger.error(f"Failed to dismiss notification: {e}")
    
    def handle_notification_action(self, notification: AINotification):
        """Handle notification action button click"""
        try:
            if notification.action_callback:
                notification.action_callback(notification.data)
            
            # Dismiss notification after action
            self.dismiss_notification(notification.id)
            
        except Exception as e:
            self.logger.error(f"Failed to handle notification action: {e}")
    
    def reposition_notifications(self):
        """Reposition remaining notifications"""
        self.notification_position = 0
        for window in self.notification_widgets.values():
            self.position_notification_window(window)
    
    def show_next_from_queue(self):
        """Show next notification from queue"""
        if self.notification_queue and len(self.notification_widgets) < self.max_notifications:
            next_notification = self.notification_queue.pop(0)
            self.create_notification_window(next_notification)
    
    def start_notification_processor(self):
        """Start background notification processor"""
        def process_notifications():
            while True:
                try:
                    # Process any queued notifications
                    if self.notification_queue and len(self.notification_widgets) < self.max_notifications:
                        self.parent_window.after(0, self.show_next_from_queue)
                    
                    time.sleep(1)
                    
                except Exception as e:
                    self.logger.error(f"Notification processor error: {e}")
        
        processor_thread = threading.Thread(target=process_notifications, daemon=True)
        processor_thread.start()
    
    def create_ai_insight_notification(self, title: str, message: str, data: Optional[Dict] = None) -> AINotification:
        """Create an AI insight notification"""
        return AINotification(
            id=f"ai_insight_{int(time.time() * 1000)}",
            title=title,
            message=message,
            notification_type=NotificationType.AI_INSIGHT,
            timestamp=time.time(),
            priority=2,
            data=data,
            auto_dismiss=True,
            dismiss_after=8000
        )
    
    def create_recommendation_notification(self, title: str, message: str, 
                                         action_text: str = None, 
                                         action_callback: Callable = None,
                                         data: Optional[Dict] = None) -> AINotification:
        """Create a recommendation notification"""
        return AINotification(
            id=f"recommendation_{int(time.time() * 1000)}",
            title=title,
            message=message,
            notification_type=NotificationType.RECOMMENDATION,
            timestamp=time.time(),
            priority=2,
            action_text=action_text,
            action_callback=action_callback,
            data=data,
            auto_dismiss=False if action_callback else True,
            dismiss_after=10000
        )
    
    def create_success_notification(self, title: str, message: str) -> AINotification:
        """Create a success notification"""
        return AINotification(
            id=f"success_{int(time.time() * 1000)}",
            title=title,
            message=message,
            notification_type=NotificationType.SUCCESS,
            timestamp=time.time(),
            priority=1,
            auto_dismiss=True,
            dismiss_after=4000
        )
    
    def create_warning_notification(self, title: str, message: str) -> AINotification:
        """Create a warning notification"""
        return AINotification(
            id=f"warning_{int(time.time() * 1000)}",
            title=title,
            message=message,
            notification_type=NotificationType.WARNING,
            timestamp=time.time(),
            priority=2,
            auto_dismiss=True,
            dismiss_after=6000
        )
    
    def notify_method_recommendation(self, method_name: str, success_probability: float, 
                                   action_callback: Callable = None):
        """Notify about AI method recommendation"""
        notification = self.create_recommendation_notification(
            title="AI Method Recommendation",
            message=f"AI suggests trying '{method_name}' with {success_probability:.1%} success probability.",
            action_text="Try Method" if action_callback else None,
            action_callback=action_callback,
            data={'method_name': method_name, 'success_probability': success_probability}
        )
        self.show_notification(notification)
    
    def notify_device_analysis_complete(self, vulnerability_score: float, 
                                      recommended_methods: List[str]):
        """Notify when AI device analysis is complete"""
        notification = self.create_ai_insight_notification(
            title="AI Device Analysis Complete",
            message=f"Vulnerability score: {vulnerability_score:.2f}. Found {len(recommended_methods)} recommended methods.",
            data={'vulnerability_score': vulnerability_score, 'methods': recommended_methods}
        )
        self.show_notification(notification)
    
    def notify_method_failure_insight(self, failed_method: str, suggested_alternative: str,
                                    action_callback: Callable = None):
        """Notify about method failure with AI insights"""
        notification = self.create_recommendation_notification(
            title="Method Failed - AI Suggestion",
            message=f"'{failed_method}' failed. AI suggests trying '{suggested_alternative}' next.",
            action_text="Try Alternative",
            action_callback=action_callback,
            data={'failed_method': failed_method, 'suggested_alternative': suggested_alternative}
        )
        self.show_notification(notification)
    
    def notify_learning_update(self, insights: str):
        """Notify about AI learning updates"""
        notification = self.create_ai_insight_notification(
            title="AI Learning Update",
            message=insights
        )
        self.show_notification(notification)
    
    def clear_all_notifications(self):
        """Clear all notifications"""
        for notification_id in list(self.notification_widgets.keys()):
            self.dismiss_notification(notification_id)
        
        self.notification_queue.clear()
        self.notification_position = 0