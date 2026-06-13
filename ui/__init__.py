"""UI package exports."""

try:
    from .board_widget import BoardWidget
except ImportError:  # pragma: no cover - keep script-style imports working
    from board_widget import BoardWidget

__all__ = ["BoardWidget"]
