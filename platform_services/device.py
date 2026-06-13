"""Device and viewport helpers for responsive UI."""
from __future__ import annotations

from dataclasses import dataclass

try:
    from kivy.core.window import Window
except Exception:  # pragma: no cover - Kivy unavailable in some tests
    Window = None


@dataclass(frozen=True)
class ViewportMetrics:
    width: float
    height: float
    shortest: float
    longest: float
    is_landscape: bool
    is_tablet_like: bool
    breakpoint: str
    scale: float


def _resolve_size(size=None):
    if size and len(size) >= 2:
        width = float(size[0])
        height = float(size[1])
    elif Window is not None:
        width = float(Window.width)
        height = float(Window.height)
    else:
        width, height = 1280.0, 860.0
    return max(1.0, width), max(1.0, height)


def get_viewport_metrics(size=None) -> ViewportMetrics:
    width, height = _resolve_size(size)
    shortest = min(width, height)
    longest = max(width, height)
    is_landscape = width >= height
    is_tablet_like = shortest >= 700

    if shortest < 640 or width < 760:
        breakpoint = "compact"
    elif width < 1180:
        breakpoint = "medium"
    else:
        breakpoint = "wide"

    width_scale = width / 1280.0
    height_scale = height / 860.0
    scale = max(0.80, min(1.35, min(width_scale, height_scale)))

    return ViewportMetrics(
        width=width,
        height=height,
        shortest=shortest,
        longest=longest,
        is_landscape=is_landscape,
        is_tablet_like=is_tablet_like,
        breakpoint=breakpoint,
        scale=scale,
    )


def scaled(value, metrics: ViewportMetrics | None = None, min_value=None, max_value=None) -> int:
    metrics = metrics or get_viewport_metrics()
    result = float(value) * metrics.scale
    if min_value is not None:
        result = max(float(min_value), result)
    if max_value is not None:
        result = min(float(max_value), result)
    return int(round(result))


def use_horizontal_game_layout(size=None) -> bool:
    metrics = get_viewport_metrics(size)
    return (
        metrics.is_landscape
        and metrics.is_tablet_like
        and metrics.width >= 1360
        and metrics.height >= 820
        and metrics.width >= metrics.height * 1.24
    )
