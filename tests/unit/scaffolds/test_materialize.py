"""
Unit tests for gavel_ai.scaffolds._materialize.

Tests cover:
- _materialize copies the correct template into eval_dir/scripts/{name}_scaffold.py
- File contains a header comment with source module path + version/hash marker
- ast.parse does not raise on the materialized file
- Unknown protocol raises ValueError
"""

import ast
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture()
def eval_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Provide a temporary eval directory."""
    d = tmp_path / "my_eval"
    d.mkdir()
    yield d


@pytest.mark.unit
def test_materialize_http_creates_file(eval_dir: Path) -> None:
    """_materialize with protocol='http' creates scripts/sut_scaffold.py."""
    from gavel_ai.scaffolds._materialize import _materialize

    dest = _materialize(eval_dir, protocol="http", name="sut")

    assert dest.exists()
    assert dest.name == "sut_scaffold.py"
    assert dest.parent == eval_dir / "scripts"


@pytest.mark.unit
def test_materialize_script_creates_file(eval_dir: Path) -> None:
    """_materialize with protocol='script' creates scripts/sut_scaffold.py."""
    from gavel_ai.scaffolds._materialize import _materialize

    dest = _materialize(eval_dir, protocol="script", name="sut")

    assert dest.exists()
    assert dest.name == "sut_scaffold.py"


@pytest.mark.unit
def test_materialize_http_header_comment(eval_dir: Path) -> None:
    """HTTP scaffold file contains source_module and content_hash header lines."""
    from gavel_ai.scaffolds._materialize import _materialize

    dest = _materialize(eval_dir, protocol="http", name="sut")
    content = dest.read_text(encoding="utf-8")

    assert "source_module" in content
    assert "content_hash" in content
    assert "sha256:" in content
    assert "http_scaffold" in content  # module path fragment


@pytest.mark.unit
def test_materialize_script_header_comment(eval_dir: Path) -> None:
    """Script scaffold file contains source_module and content_hash header lines."""
    from gavel_ai.scaffolds._materialize import _materialize

    dest = _materialize(eval_dir, protocol="script", name="sut")
    content = dest.read_text(encoding="utf-8")

    assert "source_module" in content
    assert "content_hash" in content
    assert "sha256:" in content
    assert "script_scaffold" in content


@pytest.mark.unit
def test_materialize_http_is_valid_python(eval_dir: Path) -> None:
    """Materialized HTTP scaffold must be syntactically valid Python."""
    from gavel_ai.scaffolds._materialize import _materialize

    dest = _materialize(eval_dir, protocol="http", name="sut")
    source = dest.read_text(encoding="utf-8")

    # ast.parse raises SyntaxError if the file is invalid
    ast.parse(source)


@pytest.mark.unit
def test_materialize_script_is_valid_python(eval_dir: Path) -> None:
    """Materialized script scaffold must be syntactically valid Python."""
    from gavel_ai.scaffolds._materialize import _materialize

    dest = _materialize(eval_dir, protocol="script", name="sut")
    source = dest.read_text(encoding="utf-8")

    ast.parse(source)


@pytest.mark.unit
def test_materialize_unknown_protocol_raises(eval_dir: Path) -> None:
    """Unknown protocol raises ValueError with a helpful message."""
    from gavel_ai.scaffolds._materialize import _materialize

    with pytest.raises(ValueError, match="Unknown protocol"):
        _materialize(eval_dir, protocol="grpc", name="sut")  # type: ignore[arg-type]


@pytest.mark.unit
def test_materialize_creates_scripts_dir(tmp_path: Path) -> None:
    """_materialize creates the scripts/ subdirectory if it does not exist."""
    from gavel_ai.scaffolds._materialize import _materialize

    eval_dir = tmp_path / "fresh_eval"
    eval_dir.mkdir()
    # scripts/ does NOT exist yet

    dest = _materialize(eval_dir, protocol="http", name="sut")
    assert (eval_dir / "scripts").is_dir()
    assert dest.exists()


@pytest.mark.unit
def test_materialize_custom_name(eval_dir: Path) -> None:
    """Custom name parameter controls output filename."""
    from gavel_ai.scaffolds._materialize import _materialize

    dest = _materialize(eval_dir, protocol="script", name="my_backend")
    assert dest.name == "my_backend_scaffold.py"
