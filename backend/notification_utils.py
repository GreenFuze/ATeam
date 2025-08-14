"""
Utility functions for sending notifications instead of using print statements
"""
import asyncio
from typing import Optional, Dict, Any
from notification_manager import notify_error, notify_warning, notify_info

async def notify_with_timeout(title, message, exception, context, timeout=3):
    try:
        await asyncio.wait_for(
            notify_error(title, message, exception, context),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        print(f"⏰ notify_error timed out after {timeout} seconds")


def send_error_sync(title, message, exception=None, context=None):
    try:
        # Require a running loop; schedule and return
        loop = asyncio.get_running_loop()
        loop.create_task(notify_with_timeout(title, message, exception, context))
    except RuntimeError:
        # No running loop; fail-fast to console
        print(f"❌ ERROR: {title} - {message}")
        if exception:
            import traceback
            print(f"Exception: {exception}")
            print(traceback.format_exc())


def send_warning_sync(title: str, message: str, context: Optional[Dict[str, Any]] = None):
    """Synchronous wrapper for sending warning notifications"""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(notify_warning(title, message, context))
    except RuntimeError:
        print(f"⚠️ WARNING: {title} - {message}")


def send_info_sync(title: str, message: str, context: Optional[Dict[str, Any]] = None):
    """Synchronous wrapper for sending info notifications"""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(notify_info(title, message, context))
    except RuntimeError:
        print(f"ℹ️ INFO: {title} - {message}")


# Convenience functions that match common error patterns
def log_error(component: str, message: str, exception: Optional[Exception] = None, context: Optional[Dict[str, Any]] = None):
    """Log an error with component context"""
    send_error_sync(f"{component} Error", message, exception, context)

def log_warning(component: str, message: str, context: Optional[Dict[str, Any]] = None):
    """Log a warning with component context"""
    send_warning_sync(f"{component} Warning", message, context)

def log_info(component: str, message: str, context: Optional[Dict[str, Any]] = None):
    """Log an info message with component context"""
    send_info_sync(f"{component} Info", message, context) 