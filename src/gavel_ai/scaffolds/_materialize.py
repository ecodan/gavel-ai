"""
Scaffold materialization helper (ADR-7 drift-detection mitigation).

Copies a protocol-appropriate scaffold template into
``{eval_dir}/scripts/{name}_scaffold.py``, prepending a header comment that
records:

- The source module path (for drift detection).
- A SHA-256 content-hash/version marker.

The resulting file is syntactically valid Python (``ast.parse`` does not
raise).

This module does NOT import from gavel_ai.core.*.
"""

import ast
import hashlib
import importlib.resources
import logging
import sys
from pathlib import Path
from typing import Literal

_logger = logging.getLogger("gavel-ai.scaffolds")
if not _logger.handlers:
    import logging as _logging
    _h = logging.StreamHandler(sys.stdout)
    _h.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] <%(filename)s:%(lineno)s> %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    _logger.addHandler(_h)
    _logger.setLevel(logging.INFO)

# Mapping from protocol name → template filename inside templates/
_TEMPLATE_MAP: dict[str, str] = {
    "http": "http_scaffold.py",
    "script": "script_scaffold.py",
}

_TEMPLATES_PKG = "gavel_ai.scaffolds.templates"


def _read_template(protocol: Literal["http", "script"]) -> tuple[str, str]:
    """Read template source and return (source_text, source_module_path).

    Args:
        protocol: "http" or "script".

    Returns:
        Tuple of (template_source_text, dotted_module_path_of_template).

    Raises:
        ValueError: If ``protocol`` is not "http" or "script".
        FileNotFoundError: If template file is not found in the package.
    """
    if protocol not in _TEMPLATE_MAP:
        raise ValueError(
            f"Unknown protocol '{protocol}' — must be 'http' or 'script'. "
            "See docs/specs/schema-external-runner.md"
        )

    filename: str = _TEMPLATE_MAP[protocol]
    module_path: str = f"{_TEMPLATES_PKG}.{filename[:-3]}"  # strip .py

    try:
        # Python 3.9+ importlib.resources API
        ref = importlib.resources.files(_TEMPLATES_PKG).joinpath(filename)
        source: str = ref.read_text(encoding="utf-8")
    except (FileNotFoundError, AttributeError):
        # Fallback: resolve relative to this file
        template_path = Path(__file__).parent / "templates" / filename
        source = template_path.read_text(encoding="utf-8")

    return source, module_path


def _build_header(module_path: str, content_hash: str) -> str:
    """Build the header comment block prepended to the materialized file."""
    return (
        f"# --- Gavel scaffold header (do not edit) ---\n"
        f"# source_module : {module_path}\n"
        f"# content_hash  : sha256:{content_hash}\n"
        f"# ---\n"
    )


def _materialize(
    eval_dir: Path,
    protocol: Literal["http", "script"],
    name: str = "sut",
) -> Path:
    """Copy the protocol-appropriate scaffold template into eval_dir/scripts/.

    The destination file is ``{eval_dir}/scripts/{name}_scaffold.py`` and
    contains a header comment with the source module path and SHA-256 hash.
    The file is verified to be syntactically valid Python before returning.

    Args:
        eval_dir: Root directory of the evaluation (the ``{eval_name}`` dir).
        protocol: "http" or "script".
        name: Short identifier used in the filename (default: "sut").

    Returns:
        Path to the written scaffold file.

    Raises:
        ValueError: Unknown protocol.
        SyntaxError: If the materialized file is not valid Python (should never
            happen unless the template is broken).
    """
    source, module_path = _read_template(protocol)

    content_hash: str = hashlib.sha256(source.encode("utf-8")).hexdigest()
    header: str = _build_header(module_path, content_hash)
    materialized: str = header + source

    # Verify syntax before writing.
    ast.parse(materialized)

    scripts_dir: Path = eval_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    dest: Path = scripts_dir / f"{name}_scaffold.py"
    dest.write_text(materialized, encoding="utf-8")

    _logger.info(
        "scaffold materialized protocol=%s dest=%s hash=sha256:%s",
        protocol,
        dest,
        content_hash[:16],
    )
    return dest
