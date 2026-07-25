"""Error boundary utilities for Velo.
Provides safe execution wrappers to prevent crashes in non-critical paths.
"""

from __future__ import annotations

import functools
import traceback
from typing import Any, Callable, TypeVar

from velo.logging import get_logger

logger = get_logger()

F = TypeVar("F", bound=Callable[..., Any])


def safe_thread(name: str = "") -> Callable[[F], F]:
    """
    Decorator for thread run methods. Catches and logs exceptions
    so a single thread failure doesn't crash the application.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception:
                logger.error("Thread '%s' crashed: %s", name or func.__name__, traceback.format_exc())
                return None
        return wrapper  # type: ignore
    return decorator


def safe_call(func: F, default: Any = None, log_level: str = "error") -> Callable[..., Any]:
    """
    Wraps a function to catch exceptions and return a default value.
    Useful for non-critical operations like UI updates.
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            getattr(logger, log_level)("Error in %s: %s", func.__name__, e)
            return default
    return wrapper
