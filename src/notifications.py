# notifications.py
import logging
import sys
import os
from typing import Optional, Dict, Any
import json


class NotificationManager:
    """Cross-platform notification manager with LLM integration"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.setup_platform_specific()
        self.llm_context = {}  # Store LLM-related context

    def setup_platform_specific(self):
        """Setup platform-specific notification system"""
        try:
            if os.name == 'nt':  # Windows
                from win10toast import ToastNotifier
                self.toaster = ToastNotifier()
                self.platform = 'windows'
            else:  # Linux/Mac
                self.platform = 'other'
                # You could add linux/mac specific notifiers here
        except ImportError:
            self.platform = 'fallback'
            self.logger.warning("win10toast not available, using fallback notifications")

    def show_notification(self, title: str, message: str, duration: int = 5,
                          llm_data: Optional[Dict[str, Any]] = None):
        """Show platform-appropriate notification with LLM context"""
        try:
            # Store LLM context if provided
            if llm_data:
                self.llm_context = llm_data
                title = self._enhance_title_with_llm_context(title, llm_data)
                message = self._enhance_message_with_llm_context(message, llm_data)

            if self.platform == 'windows':
                self.toaster.show_toast(
                    title,
                    message,
                    duration=duration,
                    threaded=True
                )
            else:
                # Fallback for other platforms
                self._fallback_notification(title, message)

            self.logger.info(f"Notification shown: {title} - LLM Context: {bool(llm_data)}")

        except Exception as e:
            self.logger.error(f"Notification failed: {e}")
            self._fallback_notification(title, message)

    def _enhance_title_with_llm_context(self, title: str, llm_data: Dict[str, Any]) -> str:
        """Enhance notification title with LLM context"""
        model = llm_data.get('model', 'Unknown')
        if llm_data.get('is_completion', False):
            return f"🤖 {title} ({model})"
        return f"🤖 {title}"

    def _enhance_message_with_llm_context(self, message: str, llm_data: Dict[str, Any]) -> str:
        """Enhance notification message with LLM context"""
        enhancements = []

        if 'tokens_used' in llm_data:
            enhancements.append(f"Tokens: {llm_data['tokens_used']}")

        if 'response_time' in llm_data:
            enhancements.append(f"Time: {llm_data['response_time']:.2f}s")

        if 'cost' in llm_data:
            enhancements.append(f"Cost: ${llm_data['cost']:.4f}")

        if enhancements:
            message += f"\n📊 {' | '.join(enhancements)}"

        return message

    def notify_llm_start(self, task: str, model: str = "Unknown"):
        """Notify when LLM processing starts"""
        self.show_notification(
            "LLM Processing Started",
            f"Task: {task}\nModel: {model}",
            duration=3
        )

    def notify_llm_completion(self, task: str, llm_data: Dict[str, Any]):
        """Notify when LLM processing completes"""
        self.show_notification(
            "LLM Processing Complete",
            f"Task: {task}\nClick to view results",
            duration=8,
            llm_data=llm_data
        )

    def notify_llm_error(self, error: str, task: str = "Unknown"):
        """Notify when LLM processing encounters an error"""
        self.show_notification(
            "LLM Processing Error",
            f"Task: {task}\nError: {error}",
            duration=10
        )

    def notify_llm_stream_update(self, chunk: str, task: str):
        """Notify for streaming LLM updates (minimal notification)"""
        # Only show streaming updates if they're significant
        if len(chunk.strip()) > 20:  # Only notify for substantial chunks
            preview = chunk[:50] + "..." if len(chunk) > 50 else chunk
            self.show_notification(
                "LLM Stream Update",
                f"Task: {task}\nUpdate: {preview}",
                duration=3
            )

    def _fallback_notification(self, title: str, message: str):
        """Fallback notification method"""
        print(f"🔔 {title}: {message}")


# Global instance
_notification_manager = NotificationManager()


def show_notification(title: str, message: str, duration: int = 5,
                      llm_data: Optional[Dict[str, Any]] = None):
    """Global function to show notifications"""
    _notification_manager.show_notification(title, message, duration, llm_data)


def notify_llm_start(task: str, model: str = "Unknown"):
    """Notify when LLM processing starts"""
    _notification_manager.notify_llm_start(task, model)


def notify_llm_completion(task: str, llm_data: Dict[str, Any]):
    """Notify when LLM processing completes"""
    _notification_manager.notify_llm_completion(task, llm_data)


def notify_llm_error(error: str, task: str = "Unknown"):
    """Notify when LLM processing encounters an error"""
    _notification_manager.notify_llm_error(error, task)


def notify_llm_stream_update(chunk: str, task: str):
    """Notify for streaming LLM updates"""
    _notification_manager.notify_llm_stream_update(chunk, task)