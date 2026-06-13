"""Unified save/load dialog helpers."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from platform_services.runtime import supports_native_file_dialogs
from platform_services.storage import ensure_dir, get_saves_dir


_INVALID_FILENAME_CHARS = r'[<>:"/\\|?*\x00-\x1f]'


def sanitize_filename(filename: str, fallback_stem: str = "save") -> str:
    name = str(filename or "").strip()
    name = re.sub(_INVALID_FILENAME_CHARS, "_", name)
    name = name.rstrip(" .")
    if not name:
        name = fallback_stem

    path = Path(name)
    stem = path.stem.strip() or fallback_stem
    suffix = path.suffix if path.suffix.lower() == ".json" else ".json"
    return f"{stem}{suffix}"


def _open_windows_save_dialog(initial_dir: str, initial_name: str) -> str:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    filepath = filedialog.asksaveasfilename(
        title="保存对局",
        defaultextension=".json",
        filetypes=[("JSON 存档", "*.json")],
        initialdir=initial_dir,
        initialfile=initial_name,
    )
    root.destroy()
    return filepath


def _open_windows_load_dialog(initial_dir: str) -> str:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    filepath = filedialog.askopenfilename(
        title="读取存档",
        filetypes=[("JSON 存档", "*.json")],
        initialdir=initial_dir,
    )
    root.destroy()
    return filepath


def choose_save_path(initial_name: str, initial_dir: str | None = None) -> str:
    save_dir = Path(initial_dir or get_saves_dir())
    ensure_dir(save_dir)
    safe_name = sanitize_filename(initial_name, fallback_stem="doushouqi_save")
    if supports_native_file_dialogs():
        return _open_windows_save_dialog(str(save_dir), safe_name)
    return str(save_dir / safe_name)


def choose_load_path(initial_dir: str | None = None) -> str:
    save_dir = Path(initial_dir or get_saves_dir())
    ensure_dir(save_dir)
    if supports_native_file_dialogs():
        return _open_windows_load_dialog(str(save_dir))
    raise RuntimeError("当前平台暂未接入存档选择界面。")


def list_saved_games(save_dir: str | None = None) -> list[dict]:
    target_dir = Path(save_dir or get_saves_dir())
    ensure_dir(target_dir)
    entries = []
    sortable_items = []
    for path in target_dir.glob("*.json"):
        try:
            sortable_items.append((path.stat().st_mtime, path))
        except OSError:
            continue

    for _mtime, path in sorted(sortable_items, key=lambda item: item[0], reverse=True):
        try:
            stat = path.stat()
        except OSError:
            continue
        entries.append(
            {
                "name": path.name,
                "path": str(path),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "size": stat.st_size,
            }
        )
    return entries
