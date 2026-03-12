"""Retry utility with exponential backoff for transient failures."""

import asyncio
import functools
import random
import time
from typing import Callable, Type

from loguru import logger

from src.constants import (
    MAX_RETRIES,
    RETRY_BACKOFF_FACTOR,
    RETRY_BASE_DELAY,
    RETRY_MAX_DELAY,
)


def retry_on_exception(
    max_retries: int = MAX_RETRIES,
    base_delay: float = RETRY_BASE_DELAY,
    max_delay: float = RETRY_MAX_DELAY,
    backoff_factor: float = RETRY_BACKOFF_FACTOR,
    retryable_exceptions: tuple[Type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
        OSError,
    ),
    description: str = "operation",
) -> Callable:
    """Decorator for sync functions with exponential backoff retry.

    Args:
        max_retries: Maximum number of retry attempts after the initial call.
        base_delay: Initial delay in seconds before the first retry.
        max_delay: Upper bound on delay between retries.
        backoff_factor: Multiplier applied to delay on each successive retry.
        retryable_exceptions: Exception types that trigger a retry.
        description: Human-readable label for log messages.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exception = exc
                    if attempt < max_retries:
                        delay = min(
                            base_delay * (backoff_factor ** attempt), max_delay
                        )
                        delay *= 0.5 + random.random()  # jitter
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} for "
                            f"{description}: {exc}. Waiting {delay:.1f}s"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_retries} retries exhausted for "
                            f"{description}: {exc}"
                        )
            raise last_exception  # type: ignore[misc]

        return wrapper

    return decorator


def async_retry_on_exception(
    max_retries: int = MAX_RETRIES,
    base_delay: float = RETRY_BASE_DELAY,
    max_delay: float = RETRY_MAX_DELAY,
    backoff_factor: float = RETRY_BACKOFF_FACTOR,
    retryable_exceptions: tuple[Type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
        OSError,
    ),
    description: str = "operation",
) -> Callable:
    """Decorator for async functions with exponential backoff retry.

    Same parameters as retry_on_exception but awaits the target and
    uses asyncio.sleep instead of time.sleep.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exception = exc
                    if attempt < max_retries:
                        delay = min(
                            base_delay * (backoff_factor ** attempt), max_delay
                        )
                        delay *= 0.5 + random.random()  # jitter
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} for "
                            f"{description}: {exc}. Waiting {delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_retries} retries exhausted for "
                            f"{description}: {exc}"
                        )
            raise last_exception  # type: ignore[misc]

        return wrapper

    return decorator
