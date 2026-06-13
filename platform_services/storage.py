"""Storage helpers for desktop and future mobile builds."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

try:
    from kivy.app import App
except Exception:  # pragma: no cover - Kivy unavailable in some tests
    App = None


ACCOUNT_FILE_NAME = "user_accounts.json"
SAVE_DIR_NAME = "saves"
CACHE_DIR_NAME = "cache"


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_runtime_root() -> Path:
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return get_project_root()


def get_storage_fallback_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return get_project_root()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _get_kivy_user_data_dir() -> Path | None:
    if App is None:
        return None
    try:
        app = App.get_running_app()
    except Exception:
        return None
    if not app:
        return None
    path = getattr(app, "user_data_dir", None)
    if not path:
        return None
    return Path(path)


def get_data_root() -> str:
    root = _get_kivy_user_data_dir() or get_storage_fallback_root()
    return str(ensure_dir(root))


def _migrate_file_if_needed(target: Path, legacy: Path) -> None:
    if target.exists() or not legacy.exists() or target == legacy:
        return
    ensure_dir(target.parent)
    shutil.copy2(legacy, target)


def _migrate_dir_if_needed(target_dir: Path, legacy_dir: Path) -> None:
    if not legacy_dir.exists() or target_dir == legacy_dir:
        return
    ensure_dir(target_dir)
    for source in legacy_dir.iterdir():
        if not source.is_file():
            continue
        target = target_dir / source.name
        if not target.exists():
            shutil.copy2(source, target)


def get_accounts_file() -> str:
    data_root = Path(get_data_root())
    target = data_root / ACCOUNT_FILE_NAME
    legacy = get_project_root() / ACCOUNT_FILE_NAME
    _migrate_file_if_needed(target, legacy)
    return str(target)


def get_saves_dir() -> str:
    data_root = Path(get_data_root())
    target_dir = ensure_dir(data_root / SAVE_DIR_NAME)
    legacy_dir = get_project_root() / SAVE_DIR_NAME
    _migrate_dir_if_needed(target_dir, legacy_dir)
    return str(target_dir)


def get_cache_dir(name: str | None = None) -> str:
    cache_root = ensure_dir(Path(get_data_root()) / CACHE_DIR_NAME)
    if name:
        return str(ensure_dir(cache_root / name))
    return str(cache_root)
