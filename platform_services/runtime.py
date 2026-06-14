"""Platform detection and desktop window helpers."""
from __future__ import annotations

import ctypes
import os

try:
    from kivy.utils import platform as kivy_platform
except Exception:  # pragma: no cover - Kivy unavailable in some tests
    kivy_platform = None


def get_platform_name() -> str:
    if kivy_platform:
        return str(kivy_platform)
    if os.name == "nt":
        return "win"
    return os.name


def is_android() -> bool:
    return get_platform_name() == "android"


def is_windows() -> bool:
    return get_platform_name() == "win"


def supports_native_file_dialogs() -> bool:
    return is_windows() and not is_android()


def enable_high_dpi() -> None:
    """Enable high-DPI mode on Windows desktop."""
    if not is_windows():
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def center_window(size=None) -> None:
    """Center the Kivy window on desktop platforms when supported."""
    if is_android():
        return

    try:
        from kivy.core.window import Window
    except Exception:
        return

    if not hasattr(Window, "left") or not hasattr(Window, "top"):
        return

    try:
        if is_windows():
            user32 = ctypes.windll.user32
            screen_w = int(user32.GetSystemMetrics(0))
            screen_h = int(user32.GetSystemMetrics(1))
        else:
            screen_w, screen_h = Window.system_size
        width, height = size or Window.size
        Window.left = max(0, int((screen_w - width) / 2))
        Window.top = max(0, int((screen_h - height) / 2))
    except Exception:
        pass


def apply_desktop_window_setup(default_size) -> None:
    """Apply desktop-only startup window behavior."""
    if is_android():
        return

    try:
        from kivy.core.window import Window
    except Exception:
        return

    if default_size:
        Window.size = default_size
    center_window(Window.size)


def configure_soft_input_mode() -> None:
    """Configure mobile soft input behavior to reduce field occlusion."""
    try:
        from kivy.core.window import Window
    except Exception:
        return

    if is_android():
        try:
            Window.softinput_mode = "below_target"
        except Exception:
            pass
