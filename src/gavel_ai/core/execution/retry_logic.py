"""
Retry logic for LLM calls and turn generation.
"""

import asyncio
import logging
import random
from typing import Any, Callable, Tuple

from gavel_ai.conversational.errors import classify_error
from gavel_ai.core.exceptions import ProcessorError
from gavel_ai.models.config import RetryConfig

logger = logging.getLogger(__name__)


async def call_with_retry(
    func: Callable,
    retry_config: RetryConfig,
) -> Tuple[Any, int]:
    """
    Call function with exponential backoff retry.
    
    Args:
        func: Async function to call
        retry_config: RetryConfig instance
        
    Returns:
        Tuple of (result of the function call, number of retries performed)
        
    Raises:
        The last exception if all retries fail, or immediate exception if non-transient.
    """
    max_retries = retry_config.max_retries
    initial_delay = retry_config.initial_delay_ms / 1000.0
    max_delay = retry_config.max_delay_ms / 1000.0
    backoff_factor = retry_config.backoff_factor

    last_error = None

    for attempt in range(max_retries + 1):
        try:
            result = await func()
            return result, attempt
        except Exception as e:
            error_type, is_transient = classify_error(e)

            if not is_transient or attempt >= max_retries:
                if not is_transient:
                    logger.error(f"Non-transient error detected: {error_type}. Failing immediately.")
                else:
                    logger.error(f"Max retries ({max_retries}) exceeded for {error_type}.")
                raise

            delay = min(
                initial_delay * (backoff_factor**attempt) + random.uniform(0, 0.1 * initial_delay),
                max_delay,
            )
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries + 1} failed ({error_type}), "
                f"retrying in {delay:.1f}s: {str(e)}"
            )
            last_error = e
            await asyncio.sleep(delay)

    if last_error:
        raise last_error
    raise ProcessorError("Retry loop ended without result or error")
