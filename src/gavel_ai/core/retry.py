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
    error_message_template: str = "Operation failed after {max_retries} retries - {error}",
) -> Any:
    """
    Execute async function with exponential backoff retry.

    Args:
        func: Async callable to execute
        retry_config: RetryConfig instance (defaults to standard config)
        transient_exceptions: Tuple of exception types to retry on
        error_message_template: Template for error message on final failure

    Returns:
        Result from successful function call

    Raises:
        ProcessorError: On non-transient errors or max retries exceeded
    """
    config = retry_config or RetryConfig()
    last_error: Optional[Exception] = None

    for attempt in range(config.max_retries + 1):
        try:
            result = await func()
            return result

        except transient_exceptions as e:
            last_error = e

            if attempt < config.max_retries:
                delay = config.calculate_delay(attempt)
                await asyncio.sleep(delay)
            else:
                # Max retries exceeded
                error_msg = error_message_template.format(
                    max_retries=config.max_retries, error=str(e)
                )
                raise ProcessorError(error_msg) from e

        except ProcessorError:
            # Re-raise ProcessorError as-is
            raise

        except Exception as e:
            # Non-transient error - fail immediately
            raise ProcessorError(f"Non-transient error: {e}") from e

    # Should never reach here, but satisfy type checker
    if last_error:
        raise ProcessorError("Retry logic failed unexpectedly") from last_error
    raise ProcessorError("Retry logic failed unexpectedly - no error recorded")
