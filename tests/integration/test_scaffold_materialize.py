"""
Integration tests for scaffold materialization via the eval-creation CLI path.

Tests cover:
- Creating an external eval via generate_all_templates() materializes both the
  script and http scaffold files in scripts/, with header comment and version
  marker, parseable as valid Python.
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
def test_external_eval_creates_both_scaffold_files(eval_root: Path) -> None:
    """generate_all_templates with eval_type='external' creates both script and http scaffolds."""
    eval_name = "test_ext_eval"
    generate_all_templates(eval_root, eval_name, eval_type="external")

    scripts_dir = eval_root / eval_name / "scripts"
    assert (scripts_dir / "sut_script_scaffold.py").exists(), "script scaffold not found"
    assert (scripts_dir / "sut_http_scaffold.py").exists(), "http scaffold not found"


@pytest.mark.integration
@pytest.mark.parametrize("filename", ["sut_script_scaffold.py", "sut_http_scaffold.py"])
def test_external_eval_scaffold_has_header_comment(eval_root: Path, filename: str) -> None:
    """Materialized scaffolds must contain source_module and content_hash header."""
    eval_name = f"test_ext_header_{filename.split('_')[1]}"
    generate_all_templates(eval_root, eval_name, eval_type="external")

    content = (eval_root / eval_name / "scripts" / filename).read_text(encoding="utf-8")

    assert "source_module" in content, "Missing source_module header"
    assert "content_hash" in content, "Missing content_hash header"
    assert "sha256:" in content, "Missing sha256 hash marker"


@pytest.mark.integration
@pytest.mark.parametrize("filename", ["sut_script_scaffold.py", "sut_http_scaffold.py"])
def test_external_eval_scaffold_is_valid_python(eval_root: Path, filename: str) -> None:
    """Materialized scaffold files must be syntactically valid Python."""
    eval_name = f"test_ext_syntax_{filename.split('_')[1]}"
    generate_all_templates(eval_root, eval_name, eval_type="external")

    source = (eval_root / eval_name / "scripts" / filename).read_text(encoding="utf-8")
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
def test_external_eval_config_scaffolds_both_subjects_script_active(eval_root: Path) -> None:
    """test_subjects[0] is the script variant (engine only reads index 0); http is present but inert."""
    eval_name = "test_ext_dual_subjects"
    generate_all_templates(eval_root, eval_name, eval_type="external")

    config_path = eval_root / eval_name / "config" / "eval_config.json"
    with open(config_path) as f:
        config = json.load(f)

    subjects = config["test_subjects"]
    assert len(subjects) == 2

    assert subjects[0]["system_id"] == "sut-script"
    assert subjects[0]["protocol"] == "script"
    command = subjects[0]["config"]["command"]
    assert len(command) == 2
    assert command[1].endswith("sut_script_scaffold.py")
    assert Path(command[1]).is_absolute()
    assert len(subjects[0]["judges"]) > 0, "active subject must carry the judges list"

    assert subjects[1]["system_id"] == "sut-http"
    assert subjects[1]["protocol"] == "http"
    assert subjects[1]["config"]["endpoint"]
    assert subjects[1]["judges"] == [], (
        "inactive subject must have no judges - JudgeRunnerStep pools judges "
        "across every test_subjects entry, so a non-empty list here would "
        "double-run judges against the active subject's records"
    )


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
