"""Shared resource lookup helpers."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from platform_services.storage import get_project_root, get_runtime_root


_FONT_CACHE = None

_ASSET_FONT_CANDIDATES = [
    ("assets", "fonts", "NotoSansSC-Regular.otf"),
    ("assets", "fonts", "NotoSansCJKsc-Regular.otf"),
    ("assets", "fonts", "SourceHanSansSC-Regular.otf"),
    ("assets", "fonts", "msyh.ttc"),
]

_WINDOWS_FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
    "C:/Windows/Fonts/simkai.ttf",
    "C:/Windows/Fonts/dengl.ttf",
]


def _iter_resource_roots():
    seen = set()
    for root in (get_runtime_root(), get_project_root()):
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        yield root


def find_resource(*parts: str) -> str | None:
    for root in _iter_resource_roots():
        candidate = root.joinpath(*parts)
        if candidate.exists():
            return str(candidate)
    return None


def get_desktop_icon_path() -> str | None:
    return find_resource("title.ico")


def get_chinese_font() -> str | None:
    global _FONT_CACHE
    if _FONT_CACHE is not None:
        return _FONT_CACHE

    for parts in _ASSET_FONT_CANDIDATES:
        path = find_resource(*parts)
        if path:
            print(f"[字体] 使用内置中文字体: {path}")
            _FONT_CACHE = path
            return _FONT_CACHE

    for path in _WINDOWS_FONT_CANDIDATES:
        if os.path.exists(path):
            print(f"[字体] 找到系统中文字体: {path}")
            _FONT_CACHE = path
            return _FONT_CACHE

    print("[字体] 警告: 未找到可用中文字体，中文可能显示异常")
    _FONT_CACHE = None
    return _FONT_CACHE
