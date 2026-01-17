import json
from abc import ABC
from pathlib import Path
from typing import Any, Callable, Generic, Iterator, Type, TypeVar

from pydantic import BaseModel

from gavel_ai.core.adapters.backends import StorageBackend

T = TypeVar("T")


class DataSource(ABC):
    """Base class for all data sources"""

    def __init__(self, storage: StorageBackend, path: str):
        self._storage = storage
        self._path = path
        self._ext = Path(path).suffix.lower()

    def exists(self) -> bool:
        return self._storage.exists(self._path)


class StructDataSource(DataSource, Generic[T]):
    """Single structured document (JSON, YAML, TOML)"""

    def __init__(self, storage: StorageBackend, path: str, schema: Type[T] | None = None):
        super().__init__(storage, path)
        self._schema = schema

    def write(self, data: T | dict[str, Any]) -> None:
        """Write structured data (format auto-detected from extension)"""
        obj = data.model_dump() if isinstance(data, BaseModel) else data
        content = self._serialize(obj)
        self._storage.write_bytes(self._path, content.encode("utf-8"))

    def read(self) -> T | dict[str, Any]:
        """Read structured data (format auto-detected from extension)"""
        content = self._storage.read_bytes(self._path).decode("utf-8")
        data = self._deserialize(content)
        return self._schema(**data) if self._schema else data

    def _serialize(self, data: dict[str, Any]) -> str:
        if self._ext == ".json":
            return json.dumps(data, indent=2, ensure_ascii=False)
        elif self._ext in (".yaml", ".yml"):
            import yaml

            return yaml.dump(data, sort_keys=False, allow_unicode=True)
        elif self._ext == ".toml":
            import tomli_w

            return tomli_w.dumps(data)
        else:
            raise ValueError(f"Unsupported struct format: {self._ext}")

    def _deserialize(self, content: str) -> dict[str, Any]:
        if self._ext == ".json":
            return json.loads(content)
        elif self._ext in (".yaml", ".yml"):
            import yaml

            return yaml.safe_load(content)
        elif self._ext == ".toml":
            import tomllib

            return tomllib.loads(content)
        else:
            raise ValueError(f"Unsupported struct format: {self._ext}")


class RecordDataSource(DataSource, Generic[T]):
    """List of records (JSONL, CSV, SQL results, etc.)"""

    def __init__(self, storage: StorageBackend, path: str, schema: Type[T] | None = None):
        super().__init__(storage, path)
        self._schema = schema

    def append(self, record: T | dict[str, Any]) -> None:
        """Append single record"""
        data = record.model_dump() if isinstance(record, BaseModel) else record
        line = self._serialize_record(data)
        self._storage.append_bytes(self._path, line.encode("utf-8"))

    def write(self, records: list[T | dict[str, Any]]) -> None:
        """Write all records (overwrites existing)"""
        items = [r.model_dump() if isinstance(r, BaseModel) else r for r in records]
        content = self._serialize_records(items)
        self._storage.write_bytes(self._path, content.encode("utf-8"))

    def read(self) -> list[T | dict[str, Any]]:
        """Read all records into memory"""
        return list(self.iter())

    def iter(self) -> Iterator[T | dict[str, Any]]:
        """Stream records one at a time (memory efficient)"""
        if not self.exists():
            return

        content = self._storage.read_bytes(self._path).decode("utf-8")
        for record in self._deserialize_records(content):
            yield self._schema(**record) if self._schema else record

    def _serialize_record(self, record: dict[str, Any]) -> str:
        """Serialize single record with newline"""
        if self._ext == ".jsonl":
            return json.dumps(record) + "\n"
        elif self._ext == ".csv":
            # Would need CSV writer logic here
            raise NotImplementedError("CSV append not yet implemented")
        else:
            raise ValueError(f"Unsupported record format: {self._ext}")

    def _serialize_records(self, records: list[dict[str, Any]]) -> str:
        """Serialize multiple records"""
        if self._ext == ".jsonl":
            return "\n".join(json.dumps(r) for r in records)
        elif self._ext == ".json":
            return json.dumps(records, indent=2, ensure_ascii=False)
        elif self._ext == ".csv":
            import csv
            import io

            output = io.StringIO()
            if records:
                writer = csv.DictWriter(output, fieldnames=records[0].keys())
                writer.writeheader()
                writer.writerows(records)
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported record format: {self._ext}")

    def _deserialize_records(self, content: str) -> Iterator[dict[str, Any]]:
        """Deserialize records"""
        if self._ext == ".jsonl":
            for line in content.splitlines():
                if line.strip():
                    yield json.loads(line)
        elif self._ext == ".json":
            data = json.loads(content)
            if isinstance(data, list):
                yield from data
            else:
                raise ValueError("JSON file must contain an array of records")
        elif self._ext == ".csv":
            import csv
            import io

            reader = csv.DictReader(io.StringIO(content))
            yield from reader
        else:
            raise ValueError(f"Unsupported record format: {self._ext}")


class TextDataSource(DataSource):
    """Plain text data (markdown, logs, etc.)"""

    def write(self, content: str) -> None:
        """Write text content"""
        self._storage.write_bytes(self._path, content.encode("utf-8"))

    def append(self, content: str) -> None:
        """Append text content"""
        self._storage.append_bytes(self._path, content.encode("utf-8"))

    def read(self) -> str:
        """Read text content"""
        return self._storage.read_bytes(self._path).decode("utf-8")

    def readlines(self) -> list[str]:
        """Read as list of lines"""
        return self.read().splitlines()

    def iter_lines(self) -> Iterator[str]:
        """Stream lines one at a time"""
        for line in self.readlines():
            yield line


class MultiFormatDataSource:
    """Single logical artifact available in multiple formats"""

    def __init__(self, storage: StorageBackend, base_path: str, base_name: str):
        self._storage = storage
        self._base_path = base_path
        self._base_name = base_name
        self._sources: dict[str, TextDataSource] = {}

    def write(self, content: str, format: str) -> None:
        """Write content in specified format"""
        source = self._get_source(format)
        source.write(content)

    def read(self, format: str) -> str:
        """Read content in specified format"""
        source = self._get_source(format)
        return source.read()

    def exists(self, format: str) -> bool:
        """Check if format exists"""
        return self._get_source(format).exists()

    def available_formats(self) -> list[str]:
        """List all available formats"""
        pattern = f"{self._base_name}."
        files = self._storage.list(self._base_path)
        return [Path(f).suffix.lstrip(".") for f in files if Path(f).stem == self._base_name]

    def _get_source(self, format: str) -> "TextDataSource":
        """Get or create source for format"""
        if format not in self._sources:
            path = f"{self._base_path}/{self._base_name}.{format}"
            self._sources[format] = TextDataSource(self._storage, path)
        return self._sources[format]


DS = TypeVar("DS", bound=DataSource)


class DataSourceCollection(Generic[DS]):
    """Generic collection for key-based access to data sources"""

    def __init__(
        self,
        storage: StorageBackend,
        base_path: str,
        source_factory: Callable[[StorageBackend, str], DS],
    ):
        self._storage = storage
        self._base_path = base_path
        self._source_factory = source_factory
        self._sources: dict[str, DS] = {}

    def get(self, key: str) -> DS:
        """Get or create data source for key"""
        if key not in self._sources:
            path = f"{self._base_path}/{key}"
            self._sources[key] = self._source_factory(self._storage, path)
        return self._sources[key]

    def exists(self, key: str) -> bool:
        """Check if key exists"""
        return self.get(key).exists()

    def keys(self) -> list[str]:
        """List all available keys"""
        # Scan storage for files matching pattern
        files = self._storage.list(self._base_path)
        return [Path(f).stem for f in files]
