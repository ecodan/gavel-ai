"""
Unit tests for storage backends.
"""

from unittest.mock import MagicMock, patch

import pytest

from gavel_ai.core.adapters.backends import (
    FsspecStorageBackend,
    InMemoryStorageBackend,
    LocalStorageBackend,
    StorageBackend,
)


class TestStorageBackend:
    """Test abstract StorageBackend base class."""

    def test_storage_backend_is_abstract(self):
        """StorageBackend cannot be instantiated directly."""
        with pytest.raises(TypeError):
            StorageBackend()


class TestLocalStorageBackend:
    """Test LocalStorageBackend implementation."""

    def test_init_creates_directory(self, tmp_path):
        """LocalStorageBackend creates base directory on init."""
        backend = LocalStorageBackend(tmp_path / "test_dir")
        assert backend.base_dir.exists()
        assert backend.base_dir.is_dir()

    def test_write_bytes_creates_file(self, tmp_path):
        """write_bytes creates file with content."""
        backend = LocalStorageBackend(tmp_path)
        content = b"Hello, World!"
        backend.write_bytes("test.txt", content)

        file_path = tmp_path / "test.txt"
        assert file_path.exists()
        assert file_path.read_bytes() == content

    def test_write_bytes_creates_subdirectories(self, tmp_path):
        """write_bytes creates parent directories if needed."""
        backend = LocalStorageBackend(tmp_path)
        content = b"test content"
        backend.write_bytes("subdir/nested/test.txt", content)

        file_path = tmp_path / "subdir" / "nested" / "test.txt"
        assert file_path.exists()
        assert file_path.read_bytes() == content

    def test_read_bytes_returns_content(self, tmp_path):
        """read_bytes returns file content."""
        backend = LocalStorageBackend(tmp_path)
        content = b"test content"
        backend.write_bytes("test.txt", content)

        assert backend.read_bytes("test.txt") == content

    def test_read_bytes_raises_file_not_found(self, tmp_path):
        """read_bytes raises FileNotFoundError for non-existent file."""
        backend = LocalStorageBackend(tmp_path)

        with pytest.raises(FileNotFoundError) as exc_info:
            backend.read_bytes("nonexistent.txt")

        assert "nonexistent.txt" in str(exc_info.value)

    def test_append_bytes_appends_content(self, tmp_path):
        """append_bytes appends to existing file."""
        backend = LocalStorageBackend(tmp_path)
        backend.write_bytes("test.txt", b"Hello")
        backend.append_bytes("test.txt", b", World!")

        assert backend.read_bytes("test.txt") == b"Hello, World!"

    def test_append_bytes_creates_file_if_not_exists(self, tmp_path):
        """append_bytes creates file if it doesn't exist."""
        backend = LocalStorageBackend(tmp_path)
        backend.append_bytes("new.txt", b"new content")

        assert backend.read_bytes("new.txt") == b"new content"

    def test_exists_returns_true_for_existing_file(self, tmp_path):
        """exists returns True for existing file."""
        backend = LocalStorageBackend(tmp_path)
        backend.write_bytes("test.txt", b"content")

        assert backend.exists("test.txt") is True

    def test_exists_returns_false_for_nonexistent_file(self, tmp_path):
        """exists returns False for non-existent file."""
        backend = LocalStorageBackend(tmp_path)

        assert backend.exists("nonexistent.txt") is False

    def test_exists_returns_true_for_existing_directory(self, tmp_path):
        """exists returns True for existing directory."""
        backend = LocalStorageBackend(tmp_path)
        backend.write_bytes("subdir/test.txt", b"content")

        assert backend.exists("subdir") is True

    def test_delete_removes_file(self, tmp_path):
        """delete removes file from filesystem."""
        backend = LocalStorageBackend(tmp_path)
        backend.write_bytes("test.txt", b"content")

        backend.delete("test.txt")
        assert not (tmp_path / "test.txt").exists()

    def test_delete_nonexistent_file_no_error(self, tmp_path):
        """delete doesn't raise error for non-existent file."""
        backend = LocalStorageBackend(tmp_path)

        backend.delete("nonexistent.txt")

    def test_list_returns_all_files_recursively(self, tmp_path):
        """list returns all files matching prefix recursively."""
        backend = LocalStorageBackend(tmp_path)
        backend.write_bytes("file1.txt", b"content1")
        backend.write_bytes("dir1/file2.txt", b"content2")
        backend.write_bytes("dir1/subdir/file3.txt", b"content3")
        backend.write_bytes("dir2/file4.txt", b"content4")

        files = backend.list()
        assert len(files) == 4
        assert "file1.txt" in files
        assert "dir1/file2.txt" in files
        assert "dir1/subdir/file3.txt" in files
        assert "dir2/file4.txt" in files

    def test_list_with_prefix_filters_results(self, tmp_path):
        """list with prefix returns only matching files."""
        backend = LocalStorageBackend(tmp_path)
        backend.write_bytes("dir1/file1.txt", b"content1")
        backend.write_bytes("dir1/file2.txt", b"content2")
        backend.write_bytes("dir2/file3.txt", b"content3")

        files = backend.list("dir1")
        assert len(files) == 2
        assert "dir1/file1.txt" in files
        assert "dir1/file2.txt" in files
        assert "dir2/file3.txt" not in files

    def test_list_returns_empty_for_nonexistent_prefix(self, tmp_path):
        """list returns empty list for non-existent prefix."""
        backend = LocalStorageBackend(tmp_path)

        files = backend.list("nonexistent")
        assert files == []


class TestFsspecStorageBackend:
    """Test FsspecStorageBackend implementation."""

    @patch("fsspec.filesystem")
    def test_init_creates_filesystem(self, mock_filesystem):
        """FsspecStorageBackend initializes fsspec filesystem."""
        mock_fs = MagicMock()
        mock_filesystem.return_value = mock_fs

        backend = FsspecStorageBackend("s3://bucket/path", key="test_key")

        mock_filesystem.assert_called_once_with("s3", key="test_key")
        assert backend.fs_url == "s3://bucket/path"
        assert backend.fs == mock_fs

    @patch("fsspec.filesystem")
    def test_full_path_constructs_correct_url(self, mock_filesystem):
        """_full_path constructs correct full URL."""
        mock_fs = MagicMock()
        mock_filesystem.return_value = mock_fs

        backend = FsspecStorageBackend("s3://bucket/path")

        assert backend._full_path("file.txt") == "s3://bucket/path//file.txt"
        assert backend._full_path("subdir/file.txt") == "s3://bucket/path//subdir/file.txt"

    @patch("fsspec.filesystem")
    def test_write_bytes(self, mock_filesystem):
        """write_bytes writes content using fsspec."""
        mock_fs = MagicMock()
        mock_filesystem.return_value = mock_fs

        backend = FsspecStorageBackend("s3://bucket/path")

        mock_open = MagicMock()
        mock_fs.open.return_value.__enter__.return_value = mock_open

        backend.write_bytes("test.txt", b"test content")

        mock_fs.open.assert_called_once_with("s3://bucket/path//test.txt", "wb")
        mock_open.write.assert_called_once_with(b"test content")

    @patch("fsspec.filesystem")
    def test_read_bytes(self, mock_filesystem):
        """read_bytes reads content using fsspec."""
        mock_fs = MagicMock()
        mock_filesystem.return_value = mock_fs

        backend = FsspecStorageBackend("s3://bucket/path")

        mock_open = MagicMock()
        mock_open.read.return_value = b"test content"
        mock_fs.open.return_value.__enter__.return_value = mock_open

        content = backend.read_bytes("test.txt")

        mock_fs.open.assert_called_once_with("s3://bucket/path//test.txt", "rb")
        assert content == b"test content"

    @patch("fsspec.filesystem")
    def test_append_bytes_with_append_support(self, mock_filesystem):
        """append_bytes uses append mode when supported."""
        mock_fs = MagicMock()
        mock_filesystem.return_value = mock_fs

        backend = FsspecStorageBackend("s3://bucket/path")

        mock_open = MagicMock()
        mock_fs.open.return_value.__enter__.return_value = mock_open

        backend.append_bytes("test.txt", b"appended")

        mock_fs.open.assert_called_once_with("s3://bucket/path//test.txt", "ab")
        mock_open.write.assert_called_once_with(b"appended")

    @patch("fsspec.filesystem")
    def test_append_bytes_fallback_to_read_modify_write(self, mock_filesystem):
        """append_bytes falls back to read-modify-write when append fails."""
        mock_fs = MagicMock()
        mock_filesystem.return_value = mock_fs

        backend = FsspecStorageBackend("s3://bucket/path")

        # Simulate append failure
        def open_side_effect(path, mode):
            mock = MagicMock()
            if "ab" in mode:
                raise Exception("Append not supported")
            mock.read.return_value = b"existing"
            return mock.__enter__.return_value

        mock_fs.open.side_effect = open_side_effect

        backend.append_bytes("test.txt", b"appended")

        # Should have called write with combined content
        write_calls = [call for call in mock_fs.open.call_args_list if "'wb'" in str(call)]
        assert len(write_calls) == 1

    @patch("fsspec.filesystem")
    def test_exists(self, mock_filesystem):
        """exists checks file existence via fsspec."""
        mock_fs = MagicMock()
        mock_fs.exists.return_value = True
        mock_filesystem.return_value = mock_fs

        backend = FsspecStorageBackend("s3://bucket/path")

        assert backend.exists("test.txt") is True
        mock_fs.exists.assert_called_once_with("s3://bucket/path//test.txt")

    @patch("fsspec.filesystem")
    def test_delete(self, mock_filesystem):
        """delete removes file via fsspec."""
        mock_fs = MagicMock()
        mock_filesystem.return_value = mock_fs

        backend = FsspecStorageBackend("s3://bucket/path")

        backend.delete("test.txt")

        mock_fs.rm.assert_called_once_with("s3://bucket/path//test.txt")

    @patch("fsspec.filesystem")
    def test_list(self, mock_filesystem):
        """list returns files via fsspec glob."""
        mock_fs = MagicMock()
        mock_fs.glob.return_value = [
            "s3://bucket/path//file1.txt",
            "s3://bucket/path//subdir/file2.txt",
        ]
        mock_filesystem.return_value = mock_fs

        backend = FsspecStorageBackend("s3://bucket/path")

        files = backend.list()

        mock_fs.glob.assert_called_once_with("s3://bucket/path/**")
        assert "file1.txt" in files
        assert "subdir/file2.txt" in files

    @patch("fsspec.filesystem")
    def test_list_with_prefix(self, mock_filesystem):
        """list with prefix filters via fsspec glob."""
        mock_fs = MagicMock()
        mock_fs.glob.return_value = ["s3://bucket/path//subdir/file.txt"]
        mock_filesystem.return_value = mock_fs

        backend = FsspecStorageBackend("s3://bucket/path")

        files = backend.list("subdir")

        mock_fs.glob.assert_called_once_with("s3://bucket/path/subdir/**")
        assert "subdir/file.txt" in files


class TestInMemoryStorageBackend:
    """Test InMemoryStorageBackend implementation."""

    def test_init_creates_empty_storage(self):
        """InMemoryStorageBackend starts with empty storage."""
        backend = InMemoryStorageBackend()
        assert backend._data == {}

    def test_write_bytes_stores_content(self):
        """write_bytes stores content in memory."""
        backend = InMemoryStorageBackend()
        content = b"test content"

        backend.write_bytes("test.txt", content)

        assert backend._data["test.txt"] == content

    def test_read_bytes_returns_stored_content(self):
        """read_bytes returns previously stored content."""
        backend = InMemoryStorageBackend()
        content = b"test content"
        backend.write_bytes("test.txt", content)

        assert backend.read_bytes("test.txt") == content

    def test_read_bytes_raises_file_not_found(self):
        """read_bytes raises FileNotFoundError for non-existent key."""
        backend = InMemoryStorageBackend()

        with pytest.raises(FileNotFoundError) as exc_info:
            backend.read_bytes("nonexistent.txt")

        assert "nonexistent.txt" in str(exc_info.value)

    def test_append_bytes_appends_to_existing(self):
        """append_bytes appends to existing content."""
        backend = InMemoryStorageBackend()
        backend.write_bytes("test.txt", b"Hello")

        backend.append_bytes("test.txt", b", World!")

        assert backend.read_bytes("test.txt") == b"Hello, World!"

    def test_append_bytes_creates_new_entry(self):
        """append_bytes creates new entry if key doesn't exist."""
        backend = InMemoryStorageBackend()

        backend.append_bytes("new.txt", b"new content")

        assert backend.read_bytes("new.txt") == b"new content"

    def test_exists_returns_true_for_stored_key(self):
        """exists returns True for stored key."""
        backend = InMemoryStorageBackend()
        backend.write_bytes("test.txt", b"content")

        assert backend.exists("test.txt") is True

    def test_exists_returns_false_for_nonexistent_key(self):
        """exists returns False for non-existent key."""
        backend = InMemoryStorageBackend()

        assert backend.exists("nonexistent.txt") is False

    def test_delete_removes_key(self):
        """delete removes key from storage."""
        backend = InMemoryStorageBackend()
        backend.write_bytes("test.txt", b"content")

        backend.delete("test.txt")

        assert "test.txt" not in backend._data
        assert not backend.exists("test.txt")

    def test_delete_nonexistent_key_no_error(self):
        """delete doesn't raise for non-existent key."""
        backend = InMemoryStorageBackend()

        backend.delete("nonexistent.txt")

    def test_list_returns_all_keys(self):
        """list returns all stored keys."""
        backend = InMemoryStorageBackend()
        backend.write_bytes("file1.txt", b"content1")
        backend.write_bytes("file2.txt", b"content2")
        backend.write_bytes("dir/file3.txt", b"content3")

        keys = backend.list()
        assert len(keys) == 3
        assert "file1.txt" in keys
        assert "file2.txt" in keys
        assert "dir/file3.txt" in keys

    def test_list_with_prefix_filters_keys(self):
        """list with prefix returns only matching keys."""
        backend = InMemoryStorageBackend()
        backend.write_bytes("dir1/file1.txt", b"content1")
        backend.write_bytes("dir1/file2.txt", b"content2")
        backend.write_bytes("dir2/file3.txt", b"content3")

        keys = backend.list("dir1")
        assert len(keys) == 2
        assert "dir1/file1.txt" in keys
        assert "dir1/file2.txt" in keys
        assert "dir2/file3.txt" not in keys

    def test_multiple_writes_overwrite(self):
        """Multiple writes to same path overwrite content."""
        backend = InMemoryStorageBackend()
        backend.write_bytes("test.txt", b"first")
        backend.write_bytes("test.txt", b"second")

        assert backend.read_bytes("test.txt") == b"second"

    def test_handles_binary_data(self):
        """InMemoryStorageBackend handles binary data correctly."""
        backend = InMemoryStorageBackend()
        binary_data = bytes(range(256))

        backend.write_bytes("binary.bin", binary_data)

        assert backend.read_bytes("binary.bin") == binary_data
