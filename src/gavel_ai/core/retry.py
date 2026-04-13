"""
Retry logic utilities for transient error handling.

Per Architecture Decision 7: Exponential backoff with jitter for transient failures.
"""

import asyncio
import random
from typing import Any, Callable, Optional, Tuple, Type

from gavel_ai.core.exceptions import ProcessorError


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
    ):
        """
        Initialize retry configuration.

        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds before first retry
            max_delay: Maximum delay in seconds between retries
            backoff_factor: Multiplicative factor for exponential backoff
            jitter: Whether to add randomness to delay (prevents thundering herd)
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt number.

        Args:
            attempt: Retry attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        delay = self.initial_delay * (self.backoff_factor**attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            # Add ±25% jitter
            jitter_amount = delay * 0.25
            delay += random.uniform(-jitter_amount, jitter_amount)
            delay = max(0, delay)  # Ensure non-negative

        return delay


async def retry_with_backoff(
    func: Callable[[], Any],
    retry_config: Optional[RetryConfig] = None,
    transient_exceptions: Tuple[Type[Exception], ...] = (TimeoutError,),
    transient_predicate: Optional[Callable[[Exception], bool]] = None,
    error_class: Type[Exception] = ProcessorError,
    error_message_template: str = "Operation failed after {max_retries} retries - {error}",
) -> Any:
    """
    Execute async function with exponential backoff retry.

    Args:
        func: Async callable to execute
        retry_config: RetryConfig instance (defaults to standard config)
        transient_exceptions: Tuple of exception types that are candidates for retry
        transient_predicate: Optional callable that receives a matching exception and
            returns True if it should actually be retried. Use this when an exception
            type is only sometimes transient (e.g. tenacity.RetryError wraps both
            rate-limit errors and auth errors; the predicate can distinguish them).
            If the predicate returns False, the exception is re-raised immediately.
        error_class: Exception class to raise when all retries are exhausted.
            Defaults to ProcessorError. Pass JudgeError, etc. for other callers.
        error_message_template: Template for error message on final failure.
            Supports {max_retries} and {error} placeholders.

    Returns:
        Result from successful function call

    Raises:
        error_class: When all retries are exhausted
        Original exception: On non-transient errors (re-raised as-is)
    """
    config = retry_config or RetryConfig()

    for attempt in range(config.max_retries + 1):
        try:
            return await func()

        except transient_exceptions as e:
            # If a predicate is provided, let it decide whether this specific
            # instance is actually transient (e.g. rate limit vs auth failure)
            if transient_predicate is not None and not transient_predicate(e):
                raise

            if attempt < config.max_retries:
                delay = config.calculate_delay(attempt)
                await asyncio.sleep(delay)
            else:
                error_msg = error_message_template.format(
                    max_retries=config.max_retries, error=str(e)
                )
                raise error_class(error_msg) from e

        except Exception:
            # Non-transient — re-raise original without wrapping
            raise
