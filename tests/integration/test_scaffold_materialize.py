"""
Integration tests for scaffold materialization via the eval-creation CLI path.

Tests cover:
- Creating an external eval via generate_all_templates() materializes a scaffold file
  in scripts/, with header comment and version marker, parseable as valid Python.
- Creating a local eval does NOT produce a scaffold file.
"""

import ast
import json
from pathlib import Path
from typing import Generator

import pytest

from gavel_ai.cli.scaffolding import generate_all_templates


@pytest.fixture()
def eval_root(tmp_path: Path) -> Generator[Path, None, None]:
    """Provide a temporary eval root directory."""
    root = tmp_path / "evals"
    root.mkdir()
    yield root


@pytest.mark.integration
def test_external_eval_creates_scaffold_file(eval_root: Path) -> None:
    """generate_all_templates with eval_type='external' creates scripts/sut_scaffold.py."""
    eval_name = "test_ext_eval"
    generate_all_templates(eval_root, eval_name, eval_type="external")

    scaffold_path = eval_root / eval_name / "scripts" / "sut_scaffold.py"
    assert scaffold_path.exists(), f"scaffold file not found: {scaffold_path}"


@pytest.mark.integration
def test_external_eval_scaffold_has_header_comment(eval_root: Path) -> None:
    """Materialized scaffold must contain source_module and content_hash header."""
    eval_name = "test_ext_header"
    generate_all_templates(eval_root, eval_name, eval_type="external")

    content = (eval_root / eval_name / "scripts" / "sut_scaffold.py").read_text(encoding="utf-8")

    assert "source_module" in content, "Missing source_module header"
    assert "content_hash" in content, "Missing content_hash header"
    assert "sha256:" in content, "Missing sha256 hash marker"


@pytest.mark.integration
def test_external_eval_scaffold_is_valid_python(eval_root: Path) -> None:
    """Materialized scaffold file must be syntactically valid Python."""
    eval_name = "test_ext_syntax"
    generate_all_templates(eval_root, eval_name, eval_type="external")

    source = (eval_root / eval_name / "scripts" / "sut_scaffold.py").read_text(encoding="utf-8")
    # ast.parse raises SyntaxError if invalid
    ast.parse(source)


@pytest.mark.integration
def test_local_eval_does_not_create_scaffold_file(eval_root: Path) -> None:
    """generate_all_templates with eval_type='local' must NOT create a scaffold file."""
    eval_name = "test_local_eval"
    generate_all_templates(eval_root, eval_name, eval_type="local")

    scripts_dir = eval_root / eval_name / "scripts"
    if scripts_dir.exists():
        scaffold_files = list(scripts_dir.glob("*_scaffold.py"))
        assert not scaffold_files, f"Unexpected scaffold files in local eval: {scaffold_files}"
    # If scripts/ doesn't exist at all, that's also fine
    # (the test passes by the absence of scaffold files)


@pytest.mark.integration
def test_external_eval_creates_eval_config_with_external_type(eval_root: Path) -> None:
    """The generated eval_config.json must have test_subject_type='external'."""
    eval_name = "test_ext_config"
    generate_all_templates(eval_root, eval_name, eval_type="external")

    config_path = eval_root / eval_name / "config" / "eval_config.json"
    assert config_path.exists(), "eval_config.json not created"

    with open(config_path) as f:
        config = json.load(f)

    assert config["test_subject_type"] == "external"


@pytest.mark.integration
def test_external_eval_creates_scenarios(eval_root: Path) -> None:
    """External eval scaffold also creates a scenarios.json with sample scenarios."""
    eval_name = "test_ext_scenarios"
    generate_all_templates(eval_root, eval_name, eval_type="external")

    scenarios_path = eval_root / eval_name / "data" / "scenarios.json"
    assert scenarios_path.exists(), "scenarios.json not created"

    with open(scenarios_path) as f:
        scenarios = json.load(f)

    assert len(scenarios) > 0, "scenarios.json should contain at least one scenario"
