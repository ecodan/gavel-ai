import pytest

pytestmark = pytest.mark.unit
"""
Unit tests for judge_runner helper functions:
- _render_judge_template
- _build_render_context
- _load_markdown_judge_config
"""

import tempfile
from pathlib import Path

import pytest

from gavel_ai.core.exceptions import ConfigError
from gavel_ai.core.steps.judge_runner import (
    _build_render_context,
    _load_markdown_judge_config,
    _render_judge_template,
)
from gavel_ai.models.runtime import Scenario


class TestRenderJudgeTemplate:
    """Tests for _render_judge_template."""

    def test_substitutes_known_key(self) -> None:
        result = _render_judge_template("Hello {{name}}", {"name": "world"})
        assert result == "Hello world"

    def test_unknown_key_passes_through(self) -> None:
        result = _render_judge_template("Hello {{unknown}}", {"name": "world"})
        assert result == "Hello {{unknown}}"

    def test_multiple_keys(self) -> None:
        result = _render_judge_template("{{a}} and {{b}}", {"a": "foo", "b": "bar"})
        assert result == "foo and bar"

    def test_same_key_multiple_times(self) -> None:
        result = _render_judge_template("{{x}} {{x}}", {"x": "val"})
        assert result == "val val"

    def test_non_string_value_coerced(self) -> None:
        result = _render_judge_template("Score: {{n}}", {"n": 42})
        assert result == "Score: 42"

    def test_empty_context_returns_template_unchanged(self) -> None:
        template = "No {{placeholders}} here actually"
        result = _render_judge_template(template, {})
        assert result == template

    def test_empty_template(self) -> None:
        assert _render_judge_template("", {"key": "val"}) == ""


class TestBuildRenderContext:
    """Tests for _build_render_context."""

    def test_dict_input_unpacked(self) -> None:
        scenario = Scenario(id="s1", input={"question": "What?", "lang": "en"})
        ctx = _build_render_context(scenario)
        assert ctx["question"] == "What?"
        assert ctx["lang"] == "en"

    def test_string_input_added_as_input_key(self) -> None:
        scenario = Scenario(id="s1", input="plain string")
        ctx = _build_render_context(scenario)
        assert ctx["input"] == "plain string"

    def test_metadata_merged_in(self) -> None:
        scenario = Scenario(
            id="s1",
            input={"q": "hi"},
            metadata={"category": "test", "level": "hard"},
        )
        ctx = _build_render_context(scenario)
        assert ctx["q"] == "hi"
        assert ctx["category"] == "test"
        assert ctx["level"] == "hard"

    def test_empty_metadata_ignored(self) -> None:
        scenario = Scenario(id="s1", input="text", metadata={})
        ctx = _build_render_context(scenario)
        assert ctx == {"input": "text"}

    def test_input_keys_not_overwritten_by_metadata(self) -> None:
        scenario = Scenario(
            id="s1",
            input={"key": "from_input"},
            metadata={"key": "from_metadata"},
        )
        ctx = _build_render_context(scenario)
        # metadata overwrites input (dict.update order)
        assert ctx["key"] == "from_metadata"


class TestLoadMarkdownJudgeConfig:
    """Tests for _load_markdown_judge_config."""

    def _write_md(self, tmpdir: Path, content: str, filename: str = "judge.md") -> str:
        (tmpdir / filename).write_text(content, encoding="utf-8")
        return filename

    def test_all_four_sections_parsed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            eval_dir = Path(tmpdir)
            content = """\
## Criteria
The response must be accurate and concise.

## Evaluation Steps
- Check factual accuracy
- Verify completeness
- Assess tone

## Threshold
0.75

## Guidelines
Be strict about factual claims.
"""
            path = self._write_md(eval_dir, content)
            result = _load_markdown_judge_config(path, eval_dir)

            assert result["criteria"] == "The response must be accurate and concise."
            assert result["evaluation_steps"] == [
                "Check factual accuracy",
                "Verify completeness",
                "Assess tone",
            ]
            assert result["threshold"] == 0.75
            assert "strict about factual claims" in result["guidelines"]

    def test_missing_sections_silently_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            eval_dir = Path(tmpdir)
            content = "## Criteria\nOnly this section.\n"
            path = self._write_md(eval_dir, content)
            result = _load_markdown_judge_config(path, eval_dir)

            assert "criteria" in result
            assert "threshold" not in result
            assert "evaluation_steps" not in result
            assert "guidelines" not in result

    def test_threshold_parsed_as_float(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            eval_dir = Path(tmpdir)
            content = "## Threshold\n0.9\n"
            path = self._write_md(eval_dir, content)
            result = _load_markdown_judge_config(path, eval_dir)

            assert isinstance(result["threshold"], float)
            assert result["threshold"] == 0.9

    def test_path_traversal_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            eval_dir = Path(tmpdir) / "eval"
            eval_dir.mkdir()
            with pytest.raises(ConfigError, match="Path traversal not allowed"):
                _load_markdown_judge_config("../outside.md", eval_dir)

    def test_missing_file_raises_config_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            eval_dir = Path(tmpdir)
            with pytest.raises(ConfigError, match="markdown_path file not found"):
                _load_markdown_judge_config("nonexistent.md", eval_dir)

    def test_evaluation_steps_strips_list_markers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            eval_dir = Path(tmpdir)
            content = "## Evaluation Steps\n- Step one\n* Step two\n  Step three\n"
            path = self._write_md(eval_dir, content)
            result = _load_markdown_judge_config(path, eval_dir)

            steps = result["evaluation_steps"]
            assert steps == ["Step one", "Step two", "Step three"]

    def test_empty_file_returns_empty_dict(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            eval_dir = Path(tmpdir)
            path = self._write_md(eval_dir, "")
            result = _load_markdown_judge_config(path, eval_dir)
            assert result == {}
