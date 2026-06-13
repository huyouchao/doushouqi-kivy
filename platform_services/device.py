"""Device and viewport helpers for responsive UI."""
from __future__ import annotations

from dataclasses import dataclass

try:
    from kivy.core.window import Window
except Exception:  # pragma: no cover - Kivy unavailable in some tests
    Window = None

try:
    from kivy.metrics import Metrics
except Exception:  # pragma: no cover - Kivy unavailable in some tests
    Metrics = None


@dataclass(frozen=True)
class ViewportMetrics:
    width: float
    height: float
    shortest: float
    longest: float
    width_dp: float
    height_dp: float
    shortest_dp: float
    longest_dp: float
    density: float
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
    density = float(getattr(Metrics, "density", 1.0) or 1.0) if Metrics is not None else 1.0
    width_dp = width / max(1.0, density)
    height_dp = height / max(1.0, density)
    shortest_dp = min(width_dp, height_dp)
    longest_dp = max(width_dp, height_dp)
    is_landscape = width >= height
    is_tablet_like = shortest_dp >= 600

    if shortest_dp < 600 or width_dp < 520:
        breakpoint = "compact"
    elif width_dp < 960:
        breakpoint = "medium"
    else:
        breakpoint = "wide"

    if width_dp < 600:
        base_width, base_height = 420.0, 900.0
    elif width_dp < 960:
        base_width, base_height = 720.0, 1024.0
    else:
        base_width, base_height = 1280.0, 860.0
    logical_scale = max(0.84, min(1.35, min(width_dp / base_width, height_dp / base_height)))
    if density > 1.10 and (width_dp < 960 or shortest_dp < 720):
        scale = logical_scale * density
    else:
        scale = logical_scale

    return ViewportMetrics(
        width=width,
        height=height,
        shortest=shortest,
        longest=longest,
        width_dp=width_dp,
        height_dp=height_dp,
        shortest_dp=shortest_dp,
        longest_dp=longest_dp,
        density=density,
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
        and metrics.width_dp >= 960
        and metrics.height_dp >= 600
        and metrics.width_dp >= metrics.height_dp * 1.24
    )
