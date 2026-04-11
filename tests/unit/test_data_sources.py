import pytest

pytestmark = pytest.mark.unit
"""
Unit tests for data sources.
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from gavel_ai.core.adapters.backends import LocalStorageBackend
from gavel_ai.core.adapters.data_sources import (
    DataSource,
    DataSourceCollection,
    MultiFormatDataSource,
    RecordDataSource,
    StructDataSource,
    TextDataSource,
)


class TestDataSource:
    """Test abstract DataSource base class."""

    def test_data_source_is_abstract(self):
        """DataSource cannot be instantiated directly."""
        with pytest.raises(TypeError):
            DataSource()


class TestStructDataSource:
    """Test StructDataSource for structured documents."""

    def test_init_with_storage_and_path(self, tmp_path):
        """StructDataSource initializes with storage and path."""
        storage = LocalStorageBackend(tmp_path)
        ds = StructDataSource(storage, "test.json")

        assert ds._storage is storage
        assert ds._path == "test.json"
        assert ds._ext == ".json"
        assert ds._schema is None

    def test_init_with_schema(self, tmp_path):
        """StructDataSource can be initialized with schema."""
        storage = LocalStorageBackend(tmp_path)

        class TestModel(BaseModel):
            name: str
            value: int

        ds = StructDataSource(storage, "test.json", schema=TestModel)
        assert ds._schema == TestModel

    def test_write_creates_json_file(self, tmp_path):
        """write creates JSON file with data."""
        storage = LocalStorageBackend(tmp_path)
        ds = StructDataSource(storage, "test.json")

        data = {"name": "test", "value": 42}
        ds.write(data)

        file_path = tmp_path / "test.json"
        assert file_path.exists()
        content = json.loads(file_path.read_text())
        assert content == data

    def test_write_with_pydantic_model(self, tmp_path):
        """write serializes Pydantic model to JSON."""
        storage = LocalStorageBackend(tmp_path)

        class TestModel(BaseModel):
            name: str
            value: int

        ds = StructDataSource(storage, "test.json", schema=TestModel)
        model = TestModel(name="test", value=42)

        ds.write(model)

        file_path = tmp_path / "test.json"
        content = json.loads(file_path.read_text())
        assert content == {"name": "test", "value": 42}

    def test_write_creates_yaml_file(self, tmp_path):
        """write creates YAML file with .yaml extension."""
        storage = LocalStorageBackend(tmp_path)
        ds = StructDataSource(storage, "test.yaml")

        data = {"name": "test", "value": 42}
        ds.write(data)

        file_path = tmp_path / "test.yaml"
        assert file_path.exists()

        import yaml

        content = yaml.safe_load(file_path.read_text())
        assert content == data

    def test_write_creates_yml_file(self, tmp_path):
        """write creates YAML file with .yml extension."""
        storage = LocalStorageBackend(tmp_path)
        ds = StructDataSource(storage, "test.yml")

        data = {"name": "test"}
        ds.write(data)

        file_path = tmp_path / "test.yml"
        assert file_path.exists()

    def test_write_creates_toml_file(self, tmp_path):
        """write creates TOML file with .toml extension."""
        pytest.skip("tomli_w not installed in test environment")
        storage = LocalStorageBackend(tmp_path)
        ds = StructDataSource(storage, "test.toml")

        data = {"name": "test", "value": 42}
        ds.write(data)

        file_path = tmp_path / "test.toml"
        assert file_path.exists()

        import tomllib

        content = tomllib.loads(file_path.read_text())
        assert content == data

    def test_write_raises_for_unsupported_format(self, tmp_path):
        """write raises ValueError for unsupported format."""
        storage = LocalStorageBackend(tmp_path)
        ds = StructDataSource(storage, "test.txt")

        with pytest.raises(ValueError) as exc_info:
            ds.write({"data": "test"})

        assert "Unsupported struct format" in str(exc_info.value)

    def test_read_json_file(self, tmp_path):
        """read parses JSON file."""
        storage = LocalStorageBackend(tmp_path)
        ds = StructDataSource(storage, "test.json")

        data = {"name": "test", "value": 42}
        ds.write(data)

        result = ds.read()
        assert result == data

    def test_read_yaml_file(self, tmp_path):
        """read parses YAML file."""
        storage = LocalStorageBackend(tmp_path)
        ds = StructDataSource(storage, "test.yaml")

        data = {"name": "test", "value": 42}
        ds.write(data)

        result = ds.read()
        assert result == data

    def test_read_toml_file(self, tmp_path):
        """read parses TOML file."""
        pytest.skip("tomli_w not installed in test environment")
        storage = LocalStorageBackend(tmp_path)
        ds = StructDataSource(storage, "test.toml")

        data = {"name": "test", "value": 42}
        ds.write(data)

        result = ds.read()
        assert result == data

        storage = LocalStorageBackend(tmp_path)
        ds = StructDataSource(storage, "test.toml")

        storage = LocalStorageBackend(tmp_path)

        class TestModel(BaseModel):
            name: str
            value: int

        ds = StructDataSource(storage, "test.json", schema=TestModel)
        ds.write({"name": "test", "value": "invalid"})

        with pytest.raises(ValidationError):
            ds.read()

    def test_exists_returns_true_for_existing_file(self, tmp_path):
        """exists returns True when file exists."""
        storage = LocalStorageBackend(tmp_path)
        ds = StructDataSource(storage, "test.json")
        ds.write({"data": "test"})

        assert ds.exists() is True

    def test_exists_returns_false_for_nonexistent_file(self, tmp_path):
        """exists returns False when file doesn't exist."""
        storage = LocalStorageBackend(tmp_path)
        ds = StructDataSource(storage, "test.json")

        assert ds.exists() is False


class TestRecordDataSource:
    """Test RecordDataSource for record-based data."""

    def test_init_with_storage_and_path(self, tmp_path):
        """RecordDataSource initializes with storage and path."""
        storage = LocalStorageBackend(tmp_path)
        ds = RecordDataSource(storage, "test.jsonl")

        assert ds._storage is storage
        assert ds._path == "test.jsonl"
        assert ds._ext == ".jsonl"

    def test_append_adds_record_to_jsonl(self, tmp_path):
        """append adds single record to JSONL file."""
        storage = LocalStorageBackend(tmp_path)
        ds = RecordDataSource(storage, "test.jsonl")

        ds.append({"id": 1, "value": "first"})
        ds.append({"id": 2, "value": "second"})

        file_path = tmp_path / "test.jsonl"
        lines = file_path.read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0]) == {"id": 1, "value": "first"}
        assert json.loads(lines[1]) == {"id": 2, "value": "second"}

    def test_append_with_pydantic_model(self, tmp_path):
        """append serializes Pydantic model to JSONL."""
        storage = LocalStorageBackend(tmp_path)

        class TestModel(BaseModel):
            id: int
            value: str

        ds = RecordDataSource(storage, "test.jsonl", schema=TestModel)
        ds.append(TestModel(id=1, value="test"))

        file_path = tmp_path / "test.jsonl"
        content = json.loads(file_path.read_text().strip())
        assert content == {"id": 1, "value": "test"}

    def test_write_overwrites_all_records(self, tmp_path):
        """write overwrites existing records with new ones."""
        storage = LocalStorageBackend(tmp_path)
        ds = RecordDataSource(storage, "test.jsonl")

        ds.append({"id": 1})
        ds.append({"id": 2})

        ds.write([{"id": 3}, {"id": 4}])

        file_path = tmp_path / "test.jsonl"
        lines = file_path.read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0]) == {"id": 3}
        assert json.loads(lines[1]) == {"id": 4}

    def test_read_loads_all_records(self, tmp_path):
        """read loads all records from JSONL file."""
        storage = LocalStorageBackend(tmp_path)
        ds = RecordDataSource(storage, "test.jsonl")

        records = [
            {"id": 1, "value": "first"},
            {"id": 2, "value": "second"},
        ]
        ds.write(records)

        result = ds.read()
        assert result == records

    def test_read_with_schema_returns_pydantic_models(self, tmp_path):
        """read returns list of Pydantic models when schema is provided."""
        storage = LocalStorageBackend(tmp_path)

        class TestModel(BaseModel):
            id: int
            value: str

        ds = RecordDataSource(storage, "test.jsonl", schema=TestModel)
        ds.write([{"id": 1, "value": "first"}, {"id": 2, "value": "second"}])

        result = ds.read()
        assert len(result) == 2
        assert all(isinstance(r, TestModel) for r in result)
        assert result[0].id == 1
        assert result[1].id == 2

    def test_iter_streams_records(self, tmp_path):
        """iter streams records one at a time."""
        storage = LocalStorageBackend(tmp_path)
        ds = RecordDataSource(storage, "test.jsonl")

        records = [{"id": i, "value": f"record_{i}"} for i in range(5)]
        ds.write(records)

        count = 0
        for record in ds.iter():
            assert record["id"] == count
            count += 1

        assert count == 5

    def test_iter_returns_empty_when_file_not_exists(self, tmp_path):
        """iter returns empty generator when file doesn't exist."""
        storage = LocalStorageBackend(tmp_path)
        ds = RecordDataSource(storage, "nonexistent.jsonl")

        records = list(ds.iter())
        assert records == []

    def test_write_csv_format(self, tmp_path):
        """write creates CSV file."""
        storage = LocalStorageBackend(tmp_path)
        ds = RecordDataSource(storage, "test.csv")

        records = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]
        ds.write(records)

        file_path = tmp_path / "test.csv"
        content = file_path.read_text()
        assert "id,name" in content
        assert "1,Alice" in content
        assert "2,Bob" in content

    def test_read_csv_format(self, tmp_path):
        """read parses CSV file."""
        storage = LocalStorageBackend(tmp_path)
        ds = RecordDataSource(storage, "test.csv")

        records = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]
        ds.write(records)

        result = ds.read()
        assert len(result) == 2
        assert result[0] == {"id": "1", "name": "Alice"}
        assert result[1] == {"id": "2", "name": "Bob"}

    def test_append_csv_not_implemented(self, tmp_path):
        """append raises NotImplementedError for CSV format."""
        storage = LocalStorageBackend(tmp_path)
        ds = RecordDataSource(storage, "test.csv")

        with pytest.raises(NotImplementedError):
            ds.append({"id": 1, "name": "Alice"})

    def test_write_empty_records(self, tmp_path):
        """write handles empty records list."""
        storage = LocalStorageBackend(tmp_path)
        ds = RecordDataSource(storage, "test.jsonl")

        ds.write([])

        file_path = tmp_path / "test.jsonl"
        assert file_path.read_text() == ""

    def test_jsonl_with_blank_lines(self, tmp_path):
        """iter handles JSONL with blank lines."""
        storage = LocalStorageBackend(tmp_path)
        ds = RecordDataSource(storage, "test.jsonl")

        file_path = tmp_path / "test.jsonl"
        file_path.write_text('{"id": 1}\n\n{"id": 2}\n  \n{"id": 3}\n')

        records = list(ds.iter())
        assert len(records) == 3
        assert records[0]["id"] == 1
        assert records[1]["id"] == 2
        assert records[2]["id"] == 3


class TestTextDataSource:
    """Test TextDataSource for plain text data."""

    def test_init_with_storage_and_path(self, tmp_path):
        """TextDataSource initializes with storage and path."""
        storage = LocalStorageBackend(tmp_path)
        ds = TextDataSource(storage, "test.txt")

        assert ds._storage is storage
        assert ds._path == "test.txt"

    def test_write_creates_text_file(self, tmp_path):
        """write creates text file with content."""
        storage = LocalStorageBackend(tmp_path)
        ds = TextDataSource(storage, "test.txt")

        content = "Hello, World!"
        ds.write(content)

        file_path = tmp_path / "test.txt"
        assert file_path.exists()
        assert file_path.read_text() == content

    def test_append_adds_to_existing_file(self, tmp_path):
        """append adds content to existing file."""
        storage = LocalStorageBackend(tmp_path)
        ds = TextDataSource(storage, "test.txt")

        ds.write("Hello")
        ds.append(", World!")

        file_path = tmp_path / "test.txt"
        assert file_path.read_text() == "Hello, World!"

    def test_append_creates_file_if_not_exists(self, tmp_path):
        """append creates file if it doesn't exist."""
        storage = LocalStorageBackend(tmp_path)
        ds = TextDataSource(storage, "test.txt")

        ds.append("Hello, World!")

        file_path = tmp_path / "test.txt"
        assert file_path.exists()
        assert file_path.read_text() == "Hello, World!"

    def test_read_returns_file_content(self, tmp_path):
        """read returns file content."""
        storage = LocalStorageBackend(tmp_path)
        ds = TextDataSource(storage, "test.txt")

        content = "Line 1\nLine 2\nLine 3"
        ds.write(content)

        assert ds.read() == content

    def test_readlines_returns_list_of_lines(self, tmp_path):
        """readlines returns list of lines."""
        storage = LocalStorageBackend(tmp_path)
        ds = TextDataSource(storage, "test.txt")

        ds.write("Line 1\nLine 2\nLine 3")

        lines = ds.readlines()
        assert lines == ["Line 1", "Line 2", "Line 3"]

    def test_iter_lines_yields_lines(self, tmp_path):
        """iter_lines yields lines one at a time."""
        storage = LocalStorageBackend(tmp_path)
        ds = TextDataSource(storage, "test.txt")

        ds.write("Line 1\nLine 2\nLine 3")

        lines = []
        for line in ds.iter_lines():
            lines.append(line)

        assert lines == ["Line 1", "Line 2", "Line 3"]

    def test_write_empty_content(self, tmp_path):
        """write handles empty content."""
        storage = LocalStorageBackend(tmp_path)
        ds = TextDataSource(storage, "test.txt")

        ds.write("")

        file_path = tmp_path / "test.txt"
        assert file_path.exists()
        assert file_path.read_text() == ""

    def test_write_unicode_content(self, tmp_path):
        """write handles unicode content."""
        storage = LocalStorageBackend(tmp_path)
        ds = TextDataSource(storage, "test.txt")

        content = "Hello, 世界! 🌍"
        ds.write(content)

        assert ds.read() == content


class TestMultiFormatDataSource:
    """Test MultiFormatDataSource for multi-format artifacts."""

    def test_init_creates_multi_format_source(self, tmp_path):
        """MultiFormatDataSource initializes with base path and name."""
        storage = LocalStorageBackend(tmp_path)
        ds = MultiFormatDataSource(storage, "output", "report")

        assert ds._storage is storage
        assert ds._base_path == "output"
        assert ds._base_name == "report"

    def test_write_creates_format_specific_file(self, tmp_path):
        """write creates file for specific format."""
        storage = LocalStorageBackend(tmp_path)
        ds = MultiFormatDataSource(storage, "output", "report")

        ds.write("HTML report", "html")
        ds.write("Markdown report", "md")

        assert (tmp_path / "output" / "report.html").exists()
        assert (tmp_path / "output" / "report.md").exists()
        assert (tmp_path / "output" / "report.html").read_text() == "HTML report"
        assert (tmp_path / "output" / "report.md").read_text() == "Markdown report"

    def test_read_returns_format_specific_content(self, tmp_path):
        """read returns content for specific format."""
        storage = LocalStorageBackend(tmp_path)
        ds = MultiFormatDataSource(storage, "output", "report")

        ds.write("HTML content", "html")
        ds.write("MD content", "md")

        assert ds.read("html") == "HTML content"
        assert ds.read("md") == "MD content"

    def test_exists_checks_format_specific_file(self, tmp_path):
        """exists checks if specific format exists."""
        storage = LocalStorageBackend(tmp_path)
        ds = MultiFormatDataSource(storage, "output", "report")

        ds.write("HTML content", "html")

        assert ds.exists("html") is True
        assert ds.exists("md") is False

    def test_available_formats_lists_existing_formats(self, tmp_path):
        """available_formats returns list of existing formats."""
        storage = LocalStorageBackend(tmp_path)
        ds = MultiFormatDataSource(storage, "output", "report")

        ds.write("HTML", "html")
        ds.write("MD", "md")

        formats = ds.available_formats()
        assert "html" in formats
        assert "md" in formats

    def test_available_formats_returns_empty_for_no_formats(self, tmp_path):
        """available_formats returns empty list when no formats exist."""
        storage = LocalStorageBackend(tmp_path)
        ds = MultiFormatDataSource(storage, "output", "report")

        formats = ds.available_formats()
        assert formats == []

    def test_caches_data_sources(self, tmp_path):
        """MultiFormatDataSource caches data sources per format."""
        storage = LocalStorageBackend(tmp_path)
        ds = MultiFormatDataSource(storage, "output", "report")

        source1 = ds._get_source("html")
        source2 = ds._get_source("html")

        assert source1 is source2

    def test_ignores_other_files_in_directory(self, tmp_path):
        """available_formats only returns files matching base name."""
        storage = LocalStorageBackend(tmp_path)
        ds = MultiFormatDataSource(storage, "output", "report")

        ds.write("HTML content", "html")
        storage.write_bytes("output/other.txt", b"content")

        formats = ds.available_formats()
        assert "html" in formats
        assert "txt" not in formats


class TestDataSourceCollection:
    """Test DataSourceCollection for key-based access."""

    def test_init_creates_collection(self, tmp_path):
        """DataSourceCollection initializes with storage and factory."""
        storage = LocalStorageBackend(tmp_path)
        ds = DataSourceCollection(storage, "data", TextDataSource)

        assert ds._storage is storage
        assert ds._base_path == "data"
        assert ds._source_factory == TextDataSource

    def test_get_creates_and_caches_source(self, tmp_path):
        """get creates and caches source for key."""
        storage = LocalStorageBackend(tmp_path)
        collection = DataSourceCollection(storage, "data", TextDataSource)

        source1 = collection.get("key1")
        source2 = collection.get("key1")

        assert source1 is source2
        assert source1._path == "data/key1"

    def test_get_creates_different_sources_for_different_keys(self, tmp_path):
        """get creates different sources for different keys."""
        storage = LocalStorageBackend(tmp_path)
        collection = DataSourceCollection(storage, "data", TextDataSource)

        source1 = collection.get("key1")
        source2 = collection.get("key2")

        assert source1 is not source2
        assert source1._path == "data/key1"
        assert source2._path == "data/key2"

    def test_exists_checks_key_exists(self, tmp_path):
        """exists checks if key exists in storage."""
        storage = LocalStorageBackend(tmp_path)
        collection = DataSourceCollection(storage, "data", TextDataSource)

        source = collection.get("key1")
        source.write("content")

        assert collection.exists("key1") is True
        assert collection.exists("key2") is False

    def test_keys_lists_all_available_keys(self, tmp_path):
        """keys returns list of all available keys."""
        storage = LocalStorageBackend(tmp_path)
        collection = DataSourceCollection(storage, "data", TextDataSource)

        collection.get("key1").write("content1")
        collection.get("key2").write("content2")
        collection.get("key3").write("content3")

        keys = collection.keys()
        assert "key1" in keys
        assert "key2" in keys
        assert "key3" in keys

    def test_keys_returns_empty_for_no_files(self, tmp_path):
        """keys returns empty list when no files exist."""
        storage = LocalStorageBackend(tmp_path)
        collection = DataSourceCollection(storage, "data", TextDataSource)

        keys = collection.keys()
        assert keys == []
