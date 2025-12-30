"""Tests for retry logic utilities."""

import pytest
from unittest.mock import AsyncMock

from gavel_ai.core.exceptions import ProcessorError
from gavel_ai.core.retry import RetryConfig, retry_with_backoff


class TestRetryConfig:
    """Test retry configuration."""

    def test_default_config(self):
        """Test default retry configuration."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 30.0
        assert config.backoff_factor == 2.0
        assert config.jitter is True

    def test_calculate_delay_exponential(self):
        """Test exponential backoff calculation."""
        config = RetryConfig(jitter=False)
        assert config.calculate_delay(0) == 1.0  # 1 * 2^0
        assert config.calculate_delay(1) == 2.0  # 1 * 2^1
        assert config.calculate_delay(2) == 4.0  # 1 * 2^2

    def test_calculate_delay_max_cap(self):
        """Test delay is capped at max_delay."""
        config = RetryConfig(max_delay=5.0, jitter=False)
        assert config.calculate_delay(10) == 5.0


class TestRetryWithBackoff:
    """Test retry_with_backoff function."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """Test function succeeds on first attempt."""
        mock_func = AsyncMock(return_value="success")
        result = await retry_with_backoff(mock_func)
        assert result == "success"
        mock_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_success_after_retries(self):
        """Test function succeeds after transient failures."""
        mock_func = AsyncMock(side_effect=[TimeoutError(), TimeoutError(), "success"])
        result = await retry_with_backoff(
            mock_func, retry_config=RetryConfig(max_retries=3, initial_delay=0.01)
        )
        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test raises error when max retries exceeded."""
        mock_func = AsyncMock(side_effect=TimeoutError("Always fails"))
        with pytest.raises(ProcessorError, match="failed after 2 retries"):
            await retry_with_backoff(
                mock_func, retry_config=RetryConfig(max_retries=2, initial_delay=0.01)
            )

    @pytest.mark.asyncio
    async def test_non_transient_error_fails_immediately(self):
        """Test non-transient errors fail without retry."""
        mock_func = AsyncMock(side_effect=ValueError("Non-transient"))
        with pytest.raises(ProcessorError, match="Non-transient"):
            await retry_with_backoff(mock_func)
        mock_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_processor_error_propagated(self):
        """Test ProcessorError is propagated without wrapping."""
        mock_func = AsyncMock(side_effect=ProcessorError("Already wrapped"))
        with pytest.raises(ProcessorError, match="Already wrapped"):
            await retry_with_backoff(mock_func)
