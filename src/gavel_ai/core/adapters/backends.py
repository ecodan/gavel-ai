from abc import ABC, abstractmethod
from pathlib import Path


class StorageBackend(ABC):
    """
    Abstract interface for storage location.
    Handles raw bytes read/write operations.
    """

    @abstractmethod
    def read_bytes(self, path: str) -> bytes:
        """Read raw bytes from storage"""
        ...

    @abstractmethod
    def write_bytes(self, path: str, content: bytes) -> None:
        """Write raw bytes to storage (overwrites existing)"""
        ...

    @abstractmethod
    def append_bytes(self, path: str, content: bytes) -> None:
        """Append raw bytes to storage"""
        ...

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if path exists in storage"""
        ...

    @abstractmethod
    def delete(self, path: str) -> None:
        """Delete path from storage"""
        ...

    @abstractmethod
    def list(self, prefix: str = "") -> list[str]:
        """List all paths with given prefix"""
        ...


class LocalStorageBackend(StorageBackend):
    """Store data on local filesystem"""

    def __init__(self, base_dir: Path | str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def read_bytes(self, path: str) -> bytes:
        full_path = self.base_dir / path
        if not full_path.exists():
            raise FileNotFoundError(f"Path not found: {path}")
        return full_path.read_bytes()

    def write_bytes(self, path: str, content: bytes) -> None:
        full_path = self.base_dir / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(content)

    def append_bytes(self, path: str, content: bytes) -> None:
        full_path = self.base_dir / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with full_path.open("ab") as f:
            f.write(content)

    def exists(self, path: str) -> bool:
        return (self.base_dir / path).exists()

    def delete(self, path: str) -> None:
        full_path = self.base_dir / path
        if full_path.exists():
            full_path.unlink()

    def list(self, prefix: str = "") -> list[str]:
        prefix_path = self.base_dir / prefix
        if not prefix_path.exists():
            return []

        results = []
        for item in prefix_path.rglob("*"):
            if item.is_file():
                results.append(str(item.relative_to(self.base_dir)))
        return results


class FsspecStorageBackend(StorageBackend):
    """Storage using fsspec (supports S3, GCS, Azure, HTTP, etc.)"""

    def __init__(self, fs_url: str, **storage_options):
        """
        Examples:
        - "s3://bucket/path"
        - "gcs://bucket/path"
        - "az://container/path"
        - "file:///local/path"
        """
        import fsspec

        self.fs_url = fs_url.rstrip("/")
        protocol = fs_url.split("://")[0]
        self.fs = fsspec.filesystem(protocol, **storage_options)

    def _full_path(self, path: str) -> str:
        return f"{self.fs_url}/{path}"

    def read_bytes(self, path: str) -> bytes:
        with self.fs.open(self._full_path(path), "rb") as f:
            return f.read()

    def write_bytes(self, path: str, content: bytes) -> None:
        with self.fs.open(self._full_path(path), "wb") as f:
            f.write(content)

    def append_bytes(self, path: str, content: bytes) -> None:
        # Note: Not all fsspec backends support append mode
        try:
            with self.fs.open(self._full_path(path), "ab") as f:
                f.write(content)
        except Exception:
            # Fallback to read-modify-write
            existing = self.read_bytes(path) if self.exists(path) else b""
            self.write_bytes(path, existing + content)

    def exists(self, path: str) -> bool:
        return self.fs.exists(self._full_path(path))

    def delete(self, path: str) -> None:
        self.fs.rm(self._full_path(path))

    def list(self, prefix: str = "") -> list[str]:
        full_prefix = self._full_path(prefix).rstrip("/")
        files = self.fs.glob(f"{full_prefix}/**")
        # Return relative paths
        base_len = len(self.fs_url) + 1
        return [f[base_len:] for f in files]


class InMemoryStorageBackend(StorageBackend):
    """Store data in memory (useful for testing)"""

    def __init__(self):
        self._data: dict[str, bytes] = {}

    def read_bytes(self, path: str) -> bytes:
        if path not in self._data:
            raise FileNotFoundError(f"Path not found: {path}")
        return self._data[path]

    def write_bytes(self, path: str, content: bytes) -> None:
        self._data[path] = content

    def append_bytes(self, path: str, content: bytes) -> None:
        if path in self._data:
            self._data[path] += content
        else:
            self._data[path] = content

    def exists(self, path: str) -> bool:
        return path in self._data

    def delete(self, path: str) -> None:
        self._data.pop(path, None)

    def list(self, prefix: str = "") -> list[str]:
        return [p for p in self._data.keys() if p.startswith(prefix)]
