import pytest

pytestmark = pytest.mark.unit
"""
Simple tests for conversational generate command functionality.
"""

from unittest.mock import AsyncMock, patch

from gavel_ai.cli.commands.conv import generate


class TestConversationalGenerateCommandsSimple:
    """Simple tests for conversational generate command."""

    def test_generate_command_execution(self):
        """Test basic execution flow of generate command."""
        with patch("gavel_ai.cli.commands.conv.LocalFileSystemEvalContext"):
            with patch("gavel_ai.cli.commands.conv.LocalRunContext"):
                with patch("gavel_ai.cli.commands.conv.GenerateStep") as mock_step_cls:
                    mock_step_inst = mock_step_cls.return_value
                    mock_step_inst.execute = AsyncMock(return_value=None)

                    # Execute generate command
                    generate(eval_name="test_eval")

                    # Verify execution
                    mock_step_inst.execute.assert_called_once()
