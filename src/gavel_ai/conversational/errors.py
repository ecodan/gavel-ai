"""
Error types and classification for conversational evaluation.
"""

import asyncio
from typing import Tuple

from gavel_ai.core.exceptions import GavelError


class ConversationalError(GavelError):
    """Base exception for all conversational evaluation errors."""
    pass


class TurnGenerationError(ConversationalError):
    """Errors during user turn generation."""
    pass


class RateLimitError(ConversationalError):
    """API rate limit exceeded."""
    pass


class AuthError(ConversationalError):
    """Authentication failure."""
    pass


def classify_error(error: Exception) -> Tuple[str, bool]:
    """
    Classify error as transient or permanent.

    Returns:
        (error_type: str, is_transient: bool)
    """
    error_type = type(error).__name__.lower()
    error_str = str(error).lower()

    # 1. Timeouts (Transient)
    if isinstance(error, (asyncio.TimeoutError, TimeoutError)) or "timeout" in error_type or "timeout" in error_str:
        return ("timeout", True)

    # 2. Rate Limits (Transient)
    if isinstance(error, RateLimitError) or any(k in error_str for k in ["rate limit", "429", "too many requests"]):
        return ("rate_limit", True)

    # 3. Service Unavailable / Overloaded (Transient)
    if any(k in error_str for k in ["unavailable", "503", "502", "504", "overloaded", "server error", "500"]):
        # 500 is debatable but often transient in LLM APIs
        return ("service_unstable", True)

    # 4. Authentication / Authorization (Permanent)
    if isinstance(error, AuthError) or any(k in error_str for k in ["401", "403", "unauthorized", "prohibited", "invalid api key"]):
        return ("auth_error", False)

    # 5. Turn Generation specific (Permanent - logic/prompt issue)
    if isinstance(error, TurnGenerationError):
        return ("turn_generation", False)

    # 6. Invalid Request / Validation (Permanent)
    if isinstance(error, (ValueError, TypeError)) or any(k in error_str for k in ["400", "invalid_request", "bad request"]):
        return ("invalid_request", False)

    # 7. Network/Connection Issues (Transient)
    if any(keyword in error_type or keyword in error_str for keyword in ["connection", "network", "remote", "closed", "reset", "unreachable"]):
        return ("network_error", True)

    # Default: Unknown errors are treated as transient to allow retry, but logged
    return ("unknown", True)
