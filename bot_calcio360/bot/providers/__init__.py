"""Provider package."""
from .base import BaseProvider
from .demo import DemoProvider

try:
    from .api_football import ApiFootballProvider
except Exception:  # pragma: no cover
    ApiFootballProvider = None

__all__ = ["BaseProvider", "DemoProvider", "ApiFootballProvider"]
