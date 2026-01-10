"""
Test module to verify project structure initialization (Story 1.1).

RED Phase: Tests for directory structure requirements.
"""

import sys
from pathlib import Path


class TestProjectStructure:
    """Test that project structure matches architecture requirements."""

    def test_src_layout_exists(self):
        """Test that src/gavel_ai/ directory exists."""
        src_dir = Path(__file__).parent.parent / "src" / "gavel_ai"
        assert src_dir.exists(), f"src/gavel_ai/ directory does not exist at {src_dir}"
        assert src_dir.is_dir(), "src/gavel_ai/ is not a directory"

    def test_core_submodules_exist(self):
        """Test that all core submodules exist."""
        src_dir = Path(__file__).parent.parent / "src" / "gavel_ai"
        required_modules = ["cli", "core", "processors", "judges", "reporters", "storage"]

        for module_name in required_modules:
            module_dir = src_dir / module_name
            assert module_dir.exists(), f"{module_name}/ submodule does not exist at {module_dir}"
            assert module_dir.is_dir(), f"{module_name}/ is not a directory"

    def test_test_directories_exist(self):
        """Test that test directories exist."""
        tests_dir = Path(__file__).parent
        required_dirs = ["unit", "integration", "fixtures"]

        for dir_name in required_dirs:
            test_dir = tests_dir / dir_name
            assert test_dir.exists(), f"tests/{dir_name}/ directory does not exist at {test_dir}"
            assert test_dir.is_dir(), f"tests/{dir_name}/ is not a directory"

    def test_docs_directories_exist(self):
        """Test that docs directories exist."""
        project_root = Path(__file__).parent.parent
        docs_dir = project_root / "docs"
        assert docs_dir.exists(), f"docs/ directory does not exist at {docs_dir}"
        assert docs_dir.is_dir(), "docs/ is not a directory"

        # Check for expected subdirectories
        expected_subdirs = ["quickstart", "cli-reference", "examples"]
        for subdir in expected_subdirs:
            subdir_path = docs_dir / subdir
            assert subdir_path.exists(), (
                f"docs/{subdir}/ subdirectory does not exist at {subdir_path}"
            )

    def test_github_workflows_directory_exists(self):
        """Test that .github/workflows/ directory exists."""
        project_root = Path(__file__).parent.parent
        workflows_dir = project_root / ".github" / "workflows"
        assert workflows_dir.exists(), (
            f".github/workflows/ directory does not exist at {workflows_dir}"
        )
        assert workflows_dir.is_dir(), ".github/workflows/ is not a directory"


class TestPythonPackageInitialization:
    """Test that Python packages are properly initialized."""

    def test_src_gavel_ai_init_exists(self):
        """Test that src/gavel_ai/__init__.py exists."""
        init_file = Path(__file__).parent.parent / "src" / "gavel_ai" / "__init__.py"
        assert init_file.exists(), f"src/gavel_ai/__init__.py does not exist at {init_file}"
        assert init_file.is_file(), "__init__.py is not a file"

    def test_submodule_init_files_exist(self):
        """Test that all submodules have __init__.py files."""
        src_dir = Path(__file__).parent.parent / "src" / "gavel_ai"
        required_modules = ["cli", "core", "processors", "judges", "reporters", "storage"]

        for module_name in required_modules:
            init_file = src_dir / module_name / "__init__.py"
            assert init_file.exists(), (
                f"src/gavel_ai/{module_name}/__init__.py does not exist at {init_file}"
            )
            assert init_file.is_file(), f"{module_name}/__init__.py is not a file"

    def test_imports_work_from_src_layout(self):
        """Test that imports work correctly from src-layout."""
        # Add src to path to test src-layout imports
        project_root = Path(__file__).parent.parent
        src_path = project_root / "src"

        # Only add if not already there
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))

        # Try importing main package
        try:
            import gavel_ai

            assert gavel_ai is not None, "Failed to import gavel_ai"
        except ImportError as e:
            raise AssertionError(f"Cannot import gavel_ai from src-layout: {e}") from e

    def test_no_circular_dependencies(self):
        """Test that core submodules can be imported without circular dependency issues."""
        project_root = Path(__file__).parent.parent
        src_path = project_root / "src"

        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))

        # Test importing each submodule
        submodules = ["cli", "core", "processors", "judges", "reporters", "storage"]

        for module_name in submodules:
            try:
                module = __import__(f"gavel_ai.{module_name}", fromlist=[module_name])
                assert module is not None, f"Failed to import gavel_ai.{module_name}"
            except ImportError as e:
                if "circular import" in str(e).lower():
                    raise AssertionError(
                        f"Circular import detected in gavel_ai.{module_name}: {e}"
                    ) from e
                # Other import errors are expected if modules aren't fully implemented yet


class TestRootProjectFiles:
    """Test that root project files exist."""

    def test_gitignore_exists(self):
        """Test that .gitignore file exists."""
        project_root = Path(__file__).parent.parent
        gitignore_file = project_root / ".gitignore"
        assert gitignore_file.exists(), f".gitignore file does not exist at {gitignore_file}"
        assert gitignore_file.is_file(), ".gitignore is not a file"

    def test_readme_exists(self):
        """Test that README.md file exists."""
        project_root = Path(__file__).parent.parent
        readme_file = project_root / "README.md"
        assert readme_file.exists(), f"README.md file does not exist at {readme_file}"
        assert readme_file.is_file(), "README.md is not a file"

    def test_changelog_exists(self):
        """Test that CHANGELOG.md file exists."""
        project_root = Path(__file__).parent.parent
        changelog_file = project_root / "CHANGELOG.md"
        assert changelog_file.exists(), f"CHANGELOG.md file does not exist at {changelog_file}"
        assert changelog_file.is_file(), "CHANGELOG.md is not a file"

    def test_pyproject_toml_exists(self):
        """Test that pyproject.toml file exists."""
        project_root = Path(__file__).parent.parent
        pyproject_file = project_root / "pyproject.toml"
        assert pyproject_file.exists(), f"pyproject.toml file does not exist at {pyproject_file}"
        assert pyproject_file.is_file(), "pyproject.toml is not a file"
