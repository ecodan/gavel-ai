# Storage Abstraction Specification

**Status**: Design Document
**Version**: 1.0
**Last Updated**: 2026-01-10
**Related Specs**:
- `data-schemas-specification.md` (data models)
- `file-formats-specification.md` (serialization formats)

## Overview

This specification defines the storage abstraction architecture for gavel-ai, which decouples business logic from storage implementation details. The architecture enables workflows and steps to access data through clean, schema-aware interfaces while supporting multiple storage backends (local files, S3, databases, APIs, etc.).

### Design Principles

1. **Separation of Concerns**: Three distinct layers (Backend → DataSource → Context)
2. **Storage Agnostic**: Same business logic works with any storage backend
3. **Type Safety**: Schema-aware data sources with optional runtime validation
4. **Format Abstraction**: Auto-detect serialization format from file extension
5. **Lazy Loading**: Load data only when accessed, cache for efficiency
6. **Memory Efficiency**: Stream large datasets without full materialization

## Architecture Layers

### Layer 1: Storage Backend (WHERE)

**Purpose**: Abstract the physical location and access mechanism for data.

**Interface**: `StorageBackend` (ABC)

```python
class StorageBackend(ABC):
    """Raw bytes read/write operations"""

    @abstractmethod
    def read_bytes(self, path: str) -> bytes:
        """Read raw bytes from storage"""

    @abstractmethod
    def write_bytes(self, path: str, content: bytes) -> None:
        """Write raw bytes (overwrites existing)"""

    @abstractmethod
    def append_bytes(self, path: str, content: bytes) -> None:
        """Append raw bytes to existing content"""

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if path exists"""

    @abstractmethod
    def delete(self, path: str) -> None:
        """Delete path from storage"""

    @abstractmethod
    def list(self, prefix: str = "") -> list[str]:
        """List all paths with given prefix"""
```

**Implementations**:

1. **LocalStorageBackend**: Local filesystem
   - Uses `pathlib.Path` for file operations
   - Creates parent directories automatically
   - Paths relative to `base_dir`

2. **FsspecStorageBackend**: Cloud storage via fsspec
   - Supports S3, GCS, Azure, HTTP, etc.
   - URL format: `s3://bucket/path`, `gcs://bucket/path`
   - Fallback for backends without append support

3. **InMemoryStorageBackend**: In-memory dict (testing)
   - No persistence, fast for unit tests
   - Simple dict-based implementation

**When to implement a new backend**:
- New storage location (database, custom API, etc.)
- Special authentication requirements
- Custom caching or optimization needs

### Layer 2: Data Source (WHAT Shape)

**Purpose**: Abstract the structure and format of data, provide typed access.

**Base Class**: `DataSource` (ABC)

```python
class DataSource(ABC):
    """Base for all data sources"""

    def __init__(self, storage: StorageBackend, path: str):
        self._storage = storage
        self._path = path

    def exists(self) -> bool:
        return self._storage.exists(self._path)
```

#### 2.1 StructDataSource[T]

**Purpose**: Single structured document (JSON, YAML, TOML)

**Use cases**: Configuration files, metadata, single objects

**Features**:
- Auto-detect format from path extension (.json, .yaml, .toml)
- Optional schema for type conversion: `dict → Pydantic model`
- Read/write entire document atomically
- Format inference from extension works with any storage backend

**API**:

```python
class StructDataSource(DataSource, Generic[T]):
    def __init__(
        self,
        storage: StorageBackend,
        path: str,
        schema: Type[T] | None = None
    ):
        """
        Args:
            storage: Backend for storage operations
            path: Storage path (location identifier)
            schema: Optional Pydantic model for type conversion

        Note:
            Format is inferred from path extension (.json, .yaml, .toml)
        """

    def write(self, data: T | dict[str, Any]) -> None:
        """Write structured data (serializes based on format)"""

    def read(self) -> T | dict[str, Any]:
        """Read structured data (returns typed object if schema provided)"""
```

**Example usage**:

```python
# File storage - format auto-detected from extension
local_storage = LocalStorageBackend(Path(".gavel"))
config_source = StructDataSource(local_storage, "config/eval.json")
config = config_source.read()  # dict[str, Any]

# File storage with schema (typed)
from gavel_ai.core.schemas import EvalConfig
config_source = StructDataSource(
    local_storage,
    "config/eval.json",
    schema=EvalConfig
)
config = config_source.read()  # EvalConfig instance

# For non-file backends, use file extension in path to indicate format
db_storage = DatabaseStorageBackend(conn)
config_source = StructDataSource(
    db_storage,
    "eval_configs.test_os.json",  # Extension indicates JSON format
    schema=EvalConfig
)
config = config_source.read()  # EvalConfig instance

# API storage - extension in path
api_storage = HTTPStorageBackend("https://api.example.com")
config_source = StructDataSource(
    api_storage,
    "/v1/eval/test_os.json",
)
config = config_source.read()

# Different formats via extensions
yaml_config = StructDataSource(local_storage, "config/eval.yaml")
json_config = StructDataSource(local_storage, "config/eval.json")
```

**Supported formats**:
- `json` - JSON with indentation
- `yaml` - YAML with unicode support
- `toml` - TOML format

#### 2.2 RecordDataSource[T]

**Purpose**: List of records (JSONL, CSV, database results)

**Use cases**: Results files, telemetry, scenarios, logs

**Features**:
- Auto-detect format from path extension (.jsonl, .csv)
- Optional schema for type conversion
- Memory-efficient streaming via `iter()`
- Append individual records without rewriting entire file
- Format inference from extension works with any storage backend

**API**:

```python
class RecordDataSource(DataSource, Generic[T]):
    def __init__(
        self,
        storage: StorageBackend,
        path: str,
        schema: Type[T] | None = None
    ):
        """
        Args:
            storage: Backend for storage operations
            path: Storage path (location identifier)
            schema: Optional Pydantic model for record validation

        Note:
            Format is inferred from path extension (.jsonl, .csv)
        """

    def append(self, record: T | dict[str, Any]) -> None:
        """Append single record (efficient for streaming writes)"""

    def write(self, records: list[T | dict[str, Any]]) -> None:
        """Write all records (overwrites existing)"""

    def read(self) -> list[T | dict[str, Any]]:
        """Read all records into memory"""

    def iter(self) -> Iterator[T | dict[str, Any]]:
        """Stream records one at a time (memory efficient)"""
```

**Example usage**:

```python
# File storage - streaming writes (memory efficient)
from gavel_ai.core.schemas import OutputRecord
local_storage = LocalStorageBackend(Path(".gavel/runs"))
results = RecordDataSource(
    local_storage,
    "run-123/results_raw.jsonl",
    schema=OutputRecord
)

for scenario in scenarios:
    result = process_scenario(scenario)
    results.append(result)  # Append immediately

# Streaming reads (memory efficient)
for result in results.iter():
    analyze_result(result)  # Process one at a time

# Batch read (loads all into memory)
all_results = results.read()  # list[OutputRecord]

# Database storage - extension in path indicates format
db_storage = DatabaseStorageBackend(conn)
results = RecordDataSource(
    db_storage,
    "run_results.run_123.jsonl",  # Extension indicates JSONL format
    schema=OutputRecord
)

# API storage - extension in path
api_storage = HTTPStorageBackend("https://api.example.com")
telemetry = RecordDataSource(
    api_storage,
    "/v1/runs/run-123/telemetry.jsonl"
)
```

**Supported formats**:
- `jsonl` - JSON Lines (one JSON object per line)
- `csv` - CSV with header row

#### 2.3 TextDataSource

**Purpose**: Plain text content (reports, logs, markdown)

**Use cases**: Generated reports, log files, documentation

**Features**:
- Read/write/append raw text
- Line-based operations (readlines, iter_lines)
- UTF-8 encoding assumed

**API**:

```python
class TextDataSource(DataSource):
    def write(self, content: str) -> None:
        """Write text content (overwrites)"""

    def append(self, content: str) -> None:
        """Append text content"""

    def read(self) -> str:
        """Read entire text content"""

    def readlines(self) -> list[str]:
        """Read as list of lines"""

    def iter_lines(self) -> Iterator[str]:
        """Stream lines one at a time"""
```

**Example usage**:

```python
# Write report
report = TextDataSource(storage, "report.html")
report.write(generate_html_report())

# Append log entries
log = TextDataSource(storage, "run.log")
log.append(f"[{timestamp}] Processing scenario: {scenario_id}\n")

# Stream large log file
for line in log.iter_lines():
    if "ERROR" in line:
        print(line)
```

#### 2.4 MultiFormatDataSource

**Purpose**: Single logical artifact in multiple formats

**Use cases**: Reports available as HTML, Markdown, PDF

**Features**:
- Same content, different representations
- Write/read by format name
- Query available formats
- Lazy creation of format-specific sources

**API**:

```python
class MultiFormatDataSource:
    def __init__(
        self,
        storage: StorageBackend,
        base_path: str,
        base_name: str
    ):
        """
        Args:
            storage: Backend for storage operations
            base_path: Directory path (e.g., "runs/run-123")
            base_name: Base filename without extension (e.g., "report")

        Creates: {base_path}/{base_name}.{format}
        """

    def write(self, content: str, format: str) -> None:
        """Write content in specified format"""

    def read(self, format: str) -> str:
        """Read content in specified format"""

    def exists(self, format: str) -> bool:
        """Check if format exists"""

    def available_formats(self) -> list[str]:
        """List all available formats"""
```

**Example usage**:

```python
# Create report in multiple formats
reports = MultiFormatDataSource(storage, f"runs/{run_id}", "report")

reports.write(generate_html(), "html")
reports.write(generate_markdown(), "md")
reports.write(generate_pdf(), "pdf")

# Check what's available
formats = reports.available_formats()  # ["html", "md", "pdf"]

# Read specific format
html_report = reports.read("html")
```

#### 2.5 DataSourceCollection[DS]

**Purpose**: Generic collection for key-based data source access

**Use cases**: Multiple prompt templates, multiple report types, artifact collections

**Features**:
- Lazy creation of data sources
- Type-safe generic over data source type
- Factory pattern for source creation

**API**:

```python
DS = TypeVar('DS', bound=DataSource)

class DataSourceCollection(Generic[DS]):
    def __init__(
        self,
        storage: StorageBackend,
        base_path: str,
        source_factory: Callable[[StorageBackend, str], DS]
    ):
        """
        Args:
            storage: Backend for storage operations
            base_path: Directory path for collection
            source_factory: Function to create data source from (storage, path)
        """

    def get(self, key: str) -> DS:
        """Get or create data source for key"""

    def exists(self, key: str) -> bool:
        """Check if key exists"""

    def keys(self) -> list[str]:
        """List all available keys"""
```

**Example usage**:

```python
# Collection of prompt templates
def make_prompt_source(storage: StorageBackend, path: str) -> TextDataSource:
    return TextDataSource(storage, path)

prompts = DataSourceCollection(
    storage,
    base_path="config/prompts",
    source_factory=make_prompt_source
)

# Get specific prompt (lazy loaded)
assistant_prompt = prompts.get("assistant:v1.md").read()

# List all prompts
all_prompts = prompts.keys()  # ["assistant:v1.md", "judge:v2.md", ...]
```

### Layer 3: Context (WHAT Business Logic Needs)

**Purpose**: Provide high-level, domain-specific access to data for workflows/steps.

**Design**: Two context types for different phases:

#### 3.1 EvalContext (Read-Only Configuration)

**Purpose**: Access evaluation configuration (agents, prompts, judges, scenarios).

**Lifecycle**: Created once at workflow start, shared across all steps.

**Features**:
- Read-only access to configuration artifacts
- Lazy loading with caching
- Prompt template resolution and versioning
- Support for optional judge configurations

**Directory Structure (Local Filesystem)**:
```
.gavel/evaluations/{eval_name}/
├── config/
│   ├── eval_config.json       # EvalConfig
│   ├── agents.json             # AgentsConfig with _models
│   ├── prompts/                # PromptTemplate collection
│   │   ├── assistant.toml
│   │   ├── reviewer.toml
│   │   └── ...
│   └── judges/                 # Optional custom judge configs
│       ├── similarity.json
│       └── ...
└── data/
    └── scenarios.json          # Scenario records (.json or .csv)
```

**Interface**:

```python
class EvalContext(ABC):
    """Evaluation configuration context"""

    # Core properties (lazy-loaded)
    @property
    @abstractmethod
    def eval_name(self) -> str:
        """Evaluation name"""

    @property
    @abstractmethod
    def eval_root(self) -> Path:
        """Evaluation root directory"""

    @property
    @abstractmethod
    def eval_dir(self) -> Path:
        """Evaluation directory path (.gavel/evaluations/{eval_name})"""

    @property
    @abstractmethod
    def config_dir(self) -> Path:
        """Configuration directory path"""

    # Data sources for config artifacts
    @property
    @abstractmethod
    def eval_config(self) -> StructDataSource[EvalConfig]:
        """Evaluation configuration (config/eval_config.json)"""

    @property
    @abstractmethod
    def agents(self) -> StructDataSource[AgentsConfig]:
        """Agents and models configuration (config/agents.json)"""

    @property
    @abstractmethod
    def scenarios(self) -> RecordDataSource[Scenario]:
        """Test scenarios (data/scenarios.json or .csv)"""

    # Prompt template access
    @abstractmethod
    def get_prompt(self, prompt_ref: str) -> str:
        """
        Get prompt template content (cached).

        Args:
            prompt_ref: Prompt reference in format "name:version" or "name:latest"
                       e.g., "assistant:v1", "reviewer:latest"

        Returns:
            Prompt template text with {{variable}} placeholders

        Raises:
            FileNotFoundError: If prompt file or version not found
        """

    # Optional: Custom judge configurations
    @abstractmethod
    def get_judge_config(self, judge_name: str) -> Optional[dict]:
        """
        Get custom judge configuration if exists.

        Args:
            judge_name: Judge identifier

        Returns:
            Judge configuration dict or None if not found
        """
```

**Example concrete implementation (Local Filesystem)**:

```python
class LocalFileSystemEvalContext(EvalContext):
    """Local filesystem evaluation context implementation"""

    def __init__(self, eval_name: str, eval_root: Path = Path(".gavel/evaluations")):
        self._eval_name = eval_name
        self._eval_root = eval_root

        # Initialize storage backend
        self._storage = LocalStorageBackend(self._eval_root / eval_name)

        # Lazy-loaded data sources
        self._eval_config_source: Optional[StructDataSource[EvalConfig]] = None
        self._agents_source: Optional[StructDataSource[AgentsConfig]] = None
        self._scenarios_source: Optional[RecordDataSource[Scenario]] = None

        # Caches
        self._prompt_cache: Dict[str, str] = {}
        self._judge_config_cache: Dict[str, dict] = {}

    # Properties
    @property
    def eval_name(self) -> str:
        return self._eval_name

    @property
    def eval_root(self) -> Path:
        return self._eval_root

    @property
    def eval_dir(self) -> Path:
        return self._eval_root / self._eval_name

    @property
    def config_dir(self) -> Path:
        return self.eval_dir / "config"

    # Data sources (lazy-loaded)
    @property
    def eval_config(self) -> StructDataSource[EvalConfig]:
        if self._eval_config_source is None:
            self._eval_config_source = StructDataSource(
                self._storage,
                "config/eval_config.json",
                schema=EvalConfig
            )
        return self._eval_config_source

    @property
    def agents(self) -> StructDataSource[AgentsConfig]:
        if self._agents_source is None:
            self._agents_source = StructDataSource(
                self._storage,
                "config/agents.json",
                schema=AgentsConfig
            )
        return self._agents_source

    @property
    def scenarios(self) -> RecordDataSource[Scenario]:
        if self._scenarios_source is None:
            # Auto-detect format from file extension (.json or .csv)
            scenarios_path = "data/scenarios.json"
            if not (self.eval_dir / scenarios_path).exists():
                scenarios_path = "data/scenarios.csv"

            self._scenarios_source = RecordDataSource(
                self._storage,
                scenarios_path,
                schema=Scenario
            )
        return self._scenarios_source

    # Prompt template access
    def get_prompt(self, prompt_ref: str) -> str:
        """Load and cache prompt template"""
        if prompt_ref not in self._prompt_cache:
            # Parse prompt_ref: "name:version"
            name, version = prompt_ref.split(":")

            # Read TOML file
            prompt_source = StructDataSource(
                self._storage,
                f"config/prompts/{name}.toml"
            )
            prompt_data = prompt_source.read()  # dict

            # Get specific version or latest
            if version == "latest":
                # Get highest version number
                versions = [k for k in prompt_data.keys() if k.startswith("v")]
                version = max(versions, key=lambda v: int(v[1:]))

            if version not in prompt_data:
                raise KeyError(f"Version {version} not found in prompt {name}")

            self._prompt_cache[prompt_ref] = prompt_data[version]

        return self._prompt_cache[prompt_ref]

    # Optional judge configurations
    def get_judge_config(self, judge_name: str) -> Optional[dict]:
        """Load custom judge configuration if exists"""
        if judge_name not in self._judge_config_cache:
            judge_path = f"config/judges/{judge_name}.json"

            if not (self.eval_dir / judge_path).exists():
                return None

            judge_source = StructDataSource(
                self._storage,
                judge_path
            )
            self._judge_config_cache[judge_name] = judge_source.read()

        return self._judge_config_cache.get(judge_name)
```

#### 3.2 RunContext (Read/Write Execution)

**Purpose**: Access run-specific data (results, metadata, reports, logs).

**Lifecycle**: Created for each run, used by all steps to record results.

**Features**:
- Read/write access to run artifacts
- Type-safe data sources with schemas
- Automatic artifact initialization
- Configuration snapshot at run start (for reproducibility)
- Support for multiple report formats

**Directory Structure (Local Filesystem)**:
```
.gavel/runs/{run_id}/
├── .config/                    # Config snapshot for reproducibility
│   ├── eval_config.json
│   ├── agents.json
│   ├── prompts/
│   │   └── ...
│   └── judges/
│       └── ...
├── results_raw.jsonl           # OutputRecord records
├── results_judged.jsonl        # JudgedRecord records (denormalized)
├── telemetry.jsonl             # TelemetrySpan records (REQUIRED)
├── run_metadata.json           # RunMetadata summary
├── report.html                 # Primary report format
├── report.md                   # Optional markdown report
└── run.log                     # Execution log (managed by logging framework)
```

**Interface**:

```python
class RunContext(ABC):
    """Run execution context"""

    def __init__(self, eval_ctx: EvalContext):
        self._eval_ctx = eval_ctx
        # Subclass must initialize all artifacts

    # Reference to eval context
    @property
    def eval_ctx(self) -> EvalContext:
        """Access to evaluation configuration"""
        return self._eval_ctx

    # Abstract artifact properties - subclass must provide
    @property
    @abstractmethod
    def results_raw(self) -> RecordDataSource[OutputRecord]:
        """Raw execution results"""

    @property
    @abstractmethod
    def results_judged(self) -> RecordDataSource[JudgedRecord]:
        """Judged results (denormalized - one record per judge evaluation)"""

    @property
    @abstractmethod
    def telemetry(self) -> RecordDataSource[TelemetrySpan]:
        """Telemetry spans (REQUIRED - source of truth for detailed metrics)"""

    @property
    @abstractmethod
    def run_metadata(self) -> StructDataSource[RunMetadata]:
        """Run metadata summary"""

    @property
    @abstractmethod
    def reports(self) -> MultiFormatDataSource:
        """Reports in multiple formats (html, md, pdf, etc.)"""

    @property
    @abstractmethod
    def run_logger(self) -> logging.Logger:
        """Run-specific logger"""

    @abstractmethod
    def snapshot_run_config(self) -> None:
        """
        Copy eval configs to run storage for reference.

        This ensures reproducibility by capturing the exact configuration
        used for this run, even if the eval config is later modified.
        """
```

**Example concrete implementation (Local Filesystem)**:

```python
class LocalRunContext(RunContext):
    """Local filesystem implementation"""

    def __init__(
        self,
        eval_ctx: EvalContext,
        base_dir: Path = Path(".gavel/runs"),
        run_id: Optional[str] = None
    ):
        super().__init__(eval_ctx)

        # Generate run_id if not provided
        if run_id is None:
            from datetime import datetime
            run_id = f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        self._run_id = run_id
        self._base_dir = base_dir
        self._storage = LocalStorageBackend(base_dir)

        # Initialize all artifacts (concrete implementation decides format/schema)
        self._init_artifacts()

        # Configure run-specific logger
        self._configure_logger()

        # Snapshot eval config for reproducibility
        self.snapshot_run_config()

    def _init_artifacts(self) -> None:
        """
        Initialize artifacts for local filesystem storage.

        Concrete implementation controls:
        - File formats (jsonl, json, etc.)
        - Schema validation (enable/disable)
        - Path structure
        """
        # Raw results - JSONL with schema validation
        self._results_raw = RecordDataSource(
            self._storage,
            f"{self._run_id}/results_raw.jsonl",
            schema=OutputRecord
        )

        # Judged results - JSONL with schema validation
        self._results_judged = RecordDataSource(
            self._storage,
            f"{self._run_id}/results_judged.jsonl",
            schema=JudgedRecord
        )

        # Telemetry - JSONL with schema validation
        self._telemetry = RecordDataSource(
            self._storage,
            f"{self._run_id}/telemetry.jsonl",
            schema=TelemetrySpan
        )

        # Run metadata - JSON with schema validation
        self._run_metadata = StructDataSource(
            self._storage,
            f"{self._run_id}/run_metadata.json",
            schema=RunMetadata
        )

        # Reports - multiple formats
        self._reports = MultiFormatDataSource(
            self._storage,
            f"{self._run_id}",  # Base directory
            "report"  # Base filename
        )

    def _configure_logger(self) -> None:
        """Configure run-specific logger for local filesystem"""
        import logging
        from logging.handlers import RotatingFileHandler

        log_file = self._base_dir / self._run_id / "run.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Create rotating file handler
        handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] <%(filename)s:%(lineno)s> %(message)s"
            )
        )

        # Create run-specific logger
        self._run_logger = logging.getLogger(f"gavel_ai.{self._run_id}")
        self._run_logger.addHandler(handler)
        self._run_logger.setLevel(logging.INFO)
        self._run_logger.propagate = False

    # Implement abstract properties
    @property
    def results_raw(self) -> RecordDataSource[OutputRecord]:
        return self._results_raw

    @property
    def results_judged(self) -> RecordDataSource[JudgedRecord]:
        return self._results_judged

    @property
    def telemetry(self) -> RecordDataSource[TelemetrySpan]:
        return self._telemetry

    @property
    def run_metadata(self) -> StructDataSource[RunMetadata]:
        return self._run_metadata

    @property
    def reports(self) -> MultiFormatDataSource:
        return self._reports

    @property
    def run_logger(self) -> logging.Logger:
        return self._run_logger

    def snapshot_run_config(self) -> None:
        """
        Copy eval configs to .config/ subdirectory for reproducibility.

        Copies:
        - config/eval_config.json
        - config/agents.json
        - config/prompts/*.toml
        - config/judges/*.json (if any)
        - data/scenarios.json (or .csv)
        """
        import shutil

        config_snapshot_dir = f"{self._run_id}/.config"

        # Copy eval_config.json
        eval_config_content = self._eval_ctx.eval_config.read()
        eval_config_snapshot = StructDataSource(
            self._storage,
            f"{config_snapshot_dir}/eval_config.json"
        )
        eval_config_snapshot.write(eval_config_content)

        # Copy agents.json
        agents_content = self._eval_ctx.agents.read()
        agents_snapshot = StructDataSource(
            self._storage,
            f"{config_snapshot_dir}/agents.json"
        )
        agents_snapshot.write(agents_content)

        # Copy prompts directory
        prompts_dir = self._eval_ctx.config_dir / "prompts"
        if prompts_dir.exists():
            for prompt_file in prompts_dir.glob("*.toml"):
                prompt_content = prompt_file.read_text()
                prompt_snapshot = TextDataSource(
                    self._storage,
                    f"{config_snapshot_dir}/prompts/{prompt_file.name}"
                )
                prompt_snapshot.write(prompt_content)

        # Copy judges directory (if exists)
        judges_dir = self._eval_ctx.config_dir / "judges"
        if judges_dir.exists():
            for judge_file in judges_dir.glob("*.json"):
                judge_content = judge_file.read_text()
                judge_snapshot = TextDataSource(
                    self._storage,
                    f"{config_snapshot_dir}/judges/{judge_file.name}"
                )
                judge_snapshot.write(judge_content)

        # Copy scenarios
        scenarios_content = self._eval_ctx.scenarios.read()
        scenarios_snapshot = RecordDataSource(
            self._storage,
            f"{config_snapshot_dir}/scenarios.jsonl"  # Save as JSONL
        )
        scenarios_snapshot.write(scenarios_content)
```

**Alternative implementations**:

```python
class S3RunContext(RunContext):
    """S3 bucket implementation - same formats as local filesystem"""

    def __init__(self, eval_ctx: EvalContext, bucket: str, run_id: str):
        super().__init__(eval_ctx)
        self._run_id = run_id
        self._storage = FsspecStorageBackend(
            f"s3://{bucket}/gavel-runs",
            anon=False
        )
        self._init_artifacts()
        self._configure_logger()  # Could log to CloudWatch instead
        self.snapshot_run_config()

    def _init_artifacts(self) -> None:
        """Initialize artifacts for S3 storage (same format choices as local)"""
        # Same formats as LocalRunContext - JSONL/JSON
        self._results_raw = RecordDataSource(
            self._storage,
            f"{self._run_id}/results_raw.jsonl",
            schema=OutputRecord
        )
        self._results_judged = RecordDataSource(
            self._storage,
            f"{self._run_id}/results_judged.jsonl",
            schema=JudgedRecord
        )
        # ... etc (same as local)

    # Implement abstract properties (same pattern as LocalRunContext)
    @property
    def results_raw(self) -> RecordDataSource[OutputRecord]:
        return self._results_raw

    # ... other properties


class DatabaseRunContext(RunContext):
    """Database implementation - different format/validation choices"""

    def __init__(self, eval_ctx: EvalContext, db_conn: Connection, run_id: str):
        super().__init__(eval_ctx)
        self._run_id = run_id
        self._storage = DatabaseStorageBackend(db_conn)  # Custom backend
        self._init_artifacts()
        self._configure_logger()
        self.snapshot_run_config()

    def _init_artifacts(self) -> None:
        """
        Initialize artifacts for database storage.

        Different choices from LocalRunContext:
        - Table names with .json extension (format indicator)
        - Skip schema validation for performance (trust DB constraints)
        """
        # Store as JSON in TEXT columns, skip validation
        self._results_raw = RecordDataSource(
            self._storage,
            "run_results_raw.jsonl",  # Table name with extension for format
            schema=None  # Skip validation - rely on DB constraints
        )

        self._results_judged = RecordDataSource(
            self._storage,
            "run_results_judged.jsonl",
            schema=None
        )

        self._telemetry = RecordDataSource(
            self._storage,
            "run_telemetry.jsonl",
            schema=None
        )

        self._run_metadata = StructDataSource(
            self._storage,
            f"run_metadata_{self._run_id}.json",  # DB-specific naming with extension
            schema=None
        )

        # Reports might be stored as BLOBs
        self._reports = MultiFormatDataSource(
            self._storage,
            f"run_reports_{self._run_id}",
            "report"
        )

    # Implement abstract properties
    @property
    def results_raw(self) -> RecordDataSource[OutputRecord]:
        return self._results_raw

    # ... other properties

    def snapshot_run_config(self) -> None:
        """Database-specific config snapshot - might use JSON columns"""
        # Store entire config as JSON in run_configs table
        config_snapshot = {
            "eval_config": self._eval_ctx.eval_config.read(),
            "agents": self._eval_ctx.agents.read(),
            "scenarios": self._eval_ctx.scenarios.read(),
        }
        # Store in database table instead of files
        self._storage.write_bytes(
            f"config_snapshot_{self._run_id}",
            json.dumps(config_snapshot).encode()
        )
```

## Usage Patterns

### Pattern 1: Workflow Setup

```python
from gavel_ai.core.contexts import LocalFileSystemEvalContext, LocalRunContext
from gavel_ai.core.workflows import OneShotWorkflow

# Create evaluation context (read-only config)
eval_ctx = LocalFileSystemEvalContext(
    eval_name="test_os",
    eval_root=Path(".gavel/evaluations")
)

# Create run context (read/write execution)
run_ctx = LocalRunContext(
    eval_ctx=eval_ctx,
    base_dir=Path(".gavel/runs"),
    run_id="run-20260110-120000"
)

# Pass to workflow
workflow = OneShotWorkflow(eval_ctx, run_ctx)
workflow.run()
```

### Pattern 2: Step Implementation (Reading Config)

```python
class ScenarioProcessorStep:
    def execute(self, eval_ctx: EvalContext, run_ctx: RunContext) -> None:
        # Read configuration
        scenarios = eval_ctx.scenarios.read()  # list[Scenario]
        eval_config = eval_ctx.eval_config.read()  # EvalConfig

        # Get prompt template
        prompt = eval_ctx.get_prompt("assistant:v1")

        # Process scenarios...
```

### Pattern 3: Step Implementation (Writing Results)

```python
class ScenarioProcessorStep:
    def execute(self, eval_ctx: EvalContext, run_ctx: RunContext) -> None:
        scenarios = eval_ctx.scenarios.read()

        for scenario in scenarios:
            # Process scenario
            result = self._process(scenario)

            # Write result immediately (streaming)
            run_ctx.results_raw.append(result)

            # Log progress (using run logger)
            run_ctx.run_logger.info(f"Processed scenario: {scenario.scenario_id}")
```

### Pattern 4: Step Implementation (Telemetry)

```python
class JudgeRunnerStep:
    def execute(self, eval_ctx: EvalContext, run_ctx: RunContext) -> None:
        # Stream results (memory efficient)
        for result in run_ctx.results_raw.iter():
            span_start = time.time()

            # Execute judges
            judged = self._judge(result)

            # Record telemetry
            span = TelemetrySpan(
                operation="judge_scenario",
                duration_ms=(time.time() - span_start) * 1000,
                scenario_id=result.scenario_id,
                metadata={"judge_count": len(judged.judges)}
            )
            run_ctx.telemetry.append(span)

            # Record judged result
            run_ctx.results_judged.append(judged)
```

### Pattern 5: Step Implementation (Reports)

```python
class ReportRunnerStep:
    def execute(self, eval_ctx: EvalContext, run_ctx: RunContext) -> None:
        # Read all judged results
        results = run_ctx.results_judged.read()

        # Generate report in multiple formats
        html = self._generate_html(results)
        markdown = self._generate_markdown(results)

        # Write reports
        run_ctx.reports.write(html, "html")
        run_ctx.reports.write(markdown, "md")

        # Log completion (using run logger)
        formats = run_ctx.reports.available_formats()
        run_ctx.run_logger.info(f"Generated reports: {', '.join(formats)}")
```

### Pattern 6: Logging Patterns

```python
class ScenarioProcessorStep:
    def execute(self, eval_ctx: EvalContext, run_ctx: RunContext) -> None:
        # Get run logger
        logger = run_ctx.run_logger

        logger.info("Starting scenario processing")

        scenarios = eval_ctx.scenarios.read()
        logger.debug(f"Loaded {len(scenarios)} scenarios")

        for scenario in scenarios:
            try:
                # Process scenario
                logger.debug(f"Processing scenario: {scenario.scenario_id}")
                result = self._process(scenario)

                # Write result
                run_ctx.results_raw.append(result)
                logger.info(f"Processed scenario: {scenario.scenario_id}")

            except Exception as e:
                # Log error with traceback
                logger.error(
                    f"Failed to process scenario: {scenario.scenario_id}",
                    exc_info=True
                )
                # Re-raise or handle error
                raise

        logger.info(f"Completed processing {len(scenarios)} scenarios")
```

**Logging Best Practices**:
- Use `logger.info()` for significant events (scenario completed, report generated)
- Use `logger.debug()` for detailed diagnostic information
- Use `logger.warning()` for recoverable issues
- Use `logger.error()` for failures with `exc_info=True` to capture stack traces
- Logger is automatically configured with:
  - File output to `{run_dir}/run.log`
  - Rotation (10MB max, 5 backups)
  - Standard format: `timestamp [LEVEL] <file:line> message`
  - Run-specific logger name to avoid conflicts

### Pattern 7: Testing with In-Memory Backend

```python
from gavel_ai.core.adapters.backends import InMemoryStorageBackend

def test_scenario_processor():
    # Use in-memory backend for fast tests
    storage = InMemoryStorageBackend()

    # Create mock context
    run_ctx = MockRunContext(storage)

    # Populate test data
    run_ctx.scenarios.write([
        Scenario(scenario_id="test1", input="Hello"),
        Scenario(scenario_id="test2", input="World"),
    ])

    # Run step
    step = ScenarioProcessorStep()
    step.execute(eval_ctx, run_ctx)

    # Verify results
    results = run_ctx.results_raw.read()
    assert len(results) == 2
```

## Schema Integration

### How Schemas Work with Data Sources

1. **Optional Type Conversion**:
   ```python
   # Without schema (dict)
   source = StructDataSource(storage, "config.json")
   data = source.read()  # dict[str, Any]

   # With schema (typed)
   source = StructDataSource(storage, "config.json", schema=EvalConfig)
   data = source.read()  # EvalConfig instance
   ```

2. **Automatic Validation**:
   ```python
   # Write validates against schema
   config = EvalConfig(eval_name="test", ...)
   source.write(config)  # Validates before serialization

   # Read validates on load
   config = source.read()  # Raises ValidationError if invalid
   ```

3. **Schema Evolution**:
   - Schemas defined in `data-schemas-specification.md`
   - Pydantic models in `src/gavel_ai/core/schemas.py`
   - Data sources automatically handle serialization
   - Backward compatibility via Pydantic field defaults

4. **Performance Considerations**:
   - Validation overhead on read/write
   - Skip validation for trusted internal data: `schema=None`
   - Use validation for external data and user inputs

## Extension Points

### Adding a New Storage Backend

1. **Implement StorageBackend interface**:
   ```python
   class RedisStorageBackend(StorageBackend):
       def __init__(self, redis_url: str):
           self.redis = Redis.from_url(redis_url)

       def read_bytes(self, path: str) -> bytes:
           data = self.redis.get(path)
           if data is None:
               raise FileNotFoundError(f"Path not found: {path}")
           return data

       # ... implement other methods
   ```

2. **Create context subclass**:
   ```python
   class RedisRunContext(RunContext):
       def __init__(self, eval_ctx: EvalContext, redis_url: str, run_id: str):
           super().__init__(eval_ctx)
           self._storage = RedisStorageBackend(redis_url)
           self._run_id = run_id
           self._init_artifacts()

       # ... implement _get_storage, _get_path, snapshot_run_config
   ```

3. **Use in workflow**:
   ```python
   run_ctx = RedisRunContext(eval_ctx, "redis://localhost:6379", run_id)
   workflow = OneShotWorkflow(eval_ctx, run_ctx)
   ```

### Adding a New Data Source Type

1. **Subclass DataSource**:
   ```python
   class BinaryDataSource(DataSource):
       """For binary files (images, PDFs, etc.)"""

       def write(self, content: bytes) -> None:
           self._storage.write_bytes(self._path, content)

       def read(self) -> bytes:
           return self._storage.read_bytes(self._path)
   ```

2. **Add to context if needed**:
   ```python
   class ExtendedRunContext(RunContext):
       def _init_artifacts(self) -> None:
           super()._init_artifacts()

           # Add custom artifact
           self.plots = BinaryDataSource(
               self._get_storage(),
               self._get_path("plots")
           )
   ```

## Error Handling

### Common Error Scenarios

1. **File Not Found**:
   ```python
   try:
       config = eval_ctx.eval_config.read()
   except FileNotFoundError:
       logger.error("Evaluation config not found")
       raise
   ```

2. **Validation Errors**:
   ```python
   try:
       scenarios = eval_ctx.scenarios.read()
   except ValidationError as e:
       logger.error(f"Invalid scenario data: {e}")
       raise
   ```

3. **Format Not Supported**:
   ```python
   try:
       report = reports.read("pdf")
   except FileNotFoundError:
       logger.warning("PDF report not available, falling back to HTML")
       report = reports.read("html")
   ```

4. **Storage Backend Errors**:
   ```python
   try:
       run_ctx.results_raw.append(result)
   except Exception as e:
       logger.error(f"Failed to write result: {e}")
       # Retry logic, fallback storage, etc.
   ```

## Design Rationale

### Why Three Layers?

1. **StorageBackend**: Isolates I/O operations
   - Business logic doesn't know about S3 APIs, file paths, etc.
   - Easy to add new storage types (database, API, etc.)
   - Testable with in-memory backend

2. **DataSource**: Isolates format and structure
   - Business logic doesn't parse JSON, CSV, etc.
   - Auto-detect format from extension
   - Type-safe with optional schemas

3. **Context**: Isolates domain concepts
   - Business logic uses domain terms (scenarios, results, reports)
   - Hides data source configuration
   - Provides lazy loading and caching

### Why Not Use ORM or fsspec Directly?

- **ORM (SQLAlchemy, etc.)**: Too database-centric, doesn't handle files/objects well
- **fsspec directly**: Too low-level, no format abstraction or type safety
- **Our approach**: Combines benefits of both with domain-specific abstractions

### Why Generic Type Parameters?

- **Type Safety**: Catch errors at type-check time, not runtime
- **IDE Support**: Autocomplete for schema fields
- **Flexibility**: Optional validation (`schema=None` for raw dicts)

### Why Separate EvalContext and RunContext?

- **Different lifecycles**: Config loaded once, runs created many times
- **Different access patterns**: Config is read-only, runs are read/write
- **Different storage**: Config might be version-controlled, runs are ephemeral
- **Clear separation**: Immutable config vs. mutable execution state

### Why Abstract Artifact Properties Instead of _init_artifacts()?

**The Problem**: Initially, we had a `@final` `_init_artifacts()` method in RunContext:

```python
class RunContext(ABC):
    @final
    def _init_artifacts(self) -> None:
        """Initialize all artifacts (called by subclass __init__)"""
        storage = self._get_storage()

        self.results_raw = RecordDataSource(
            storage,
            self._get_path("results_raw"),
            format="jsonl",  # HARDCODED!
            schema=OutputRecord
        )
        # ...
```

This **breaks abstraction** by forcing implementation details into the abstract layer:

**Problems**:
- **Hardcoded formats**: Forces all backends to use JSONL/JSON
- **Forced validation**: Forces schema validation even if backend doesn't need it
- **DataSource types**: Forces RecordDataSource when custom sources might be better
- **Path structure**: Forces file path conventions on non-file backends

**Example failure**: A database backend is forced to pretend it's using JSONL files!

**The Solution**: Make artifacts abstract properties, let concrete implementations decide:

```python
class RunContext(ABC):
    """Declares WHAT artifacts exist, not HOW they're created"""

    @property
    @abstractmethod
    def results_raw(self) -> RecordDataSource[OutputRecord]:
        """Raw execution results"""

class LocalRunContext(RunContext):
    """Decides HOW to create artifacts"""

    def _init_artifacts(self) -> None:
        self._results_raw = RecordDataSource(
            self._storage,
            f"{self._run_id}/results_raw.jsonl",
            format="jsonl",  # Local filesystem choice
            schema=OutputRecord  # Enable validation
        )

    @property
    def results_raw(self) -> RecordDataSource[OutputRecord]:
        return self._results_raw

class DatabaseRunContext(RunContext):
    """Makes different choices"""

    def _init_artifacts(self) -> None:
        self._results_raw = RecordDataSource(
            self._storage,
            "run_results_raw",  # Table name
            format="json",  # Different format
            schema=None  # Skip validation (trust DB)
        )
```

**Benefits**:
- **True abstraction**: Abstract layer declares interface, concrete layer decides implementation
- **Backend flexibility**: Each backend chooses formats, validation, paths
- **No forced conventions**: Database doesn't pretend to be files
- **Clean separation**: WHAT (abstract) vs HOW (concrete)

**Trade-offs Accepted**:
- More boilerplate: Each backend implements property getters
- Repeated code: Similar initialization patterns across backends
- But: Worth it for proper abstraction and flexibility

### Why Format Inference from Path Extension?

**Approach**: Format is always inferred from the path extension:

```python
# File storage - natural extension
config = StructDataSource(storage, "config/eval.json")  # Infers JSON from .json

# Database - include extension in identifier
db_config = StructDataSource(db_storage, "eval_configs.test_os.json")  # JSON format

# API - extension in URL path
api_config = StructDataSource(api_storage, "/v1/eval/test_os.json")  # JSON format
```

**Benefits**:
- **Simplicity**: One less parameter to manage
- **Self-documenting**: Path clearly shows format
- **Consistency**: Same pattern for all backends
- **No ambiguity**: Extension always indicates format

**Trade-offs Accepted**:
- Non-file backends must include extensions in their identifiers (table names, URLs, keys)
- This is a reasonable trade-off since the extension is part of the logical identifier

### Why run_logger Instead of logs: TextDataSource?

**The Problem**: Initially considered treating logs as another artifact:

```python
# WRONG - Logs as TextDataSource
run_ctx.logs.append(f"[{timestamp}] Processing scenario: {scenario_id}\n")
```

This **breaks the logging abstraction** and creates problems:

**Issues with TextDataSource for Logs**:
- **Manual formatting**: Must manually format timestamps, levels, module names
- **No log levels**: Can't filter INFO vs DEBUG vs ERROR
- **No handlers**: Can't route logs to multiple destinations (file + stdout)
- **No rotation**: Large log files grow unbounded
- **Thread safety**: `append()` might not be thread-safe for concurrent writes
- **No stack traces**: Error logging requires manual traceback formatting
- **Mixing concerns**: Context managing log writes instead of logging framework

**The Solution**: Use Python's logging framework:

```python
# CORRECT - Use logging framework
run_ctx.run_logger.info(f"Processing scenario: {scenario_id}")
run_ctx.run_logger.error(f"Failed: {error}", exc_info=True)
```

**Benefits**:
- **Standard patterns**: Use Python's built-in `logging` module
- **Automatic formatting**: Timestamps, levels, file/line numbers handled
- **Log levels**: Built-in DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Multiple handlers**: Can add stdout, syslog, or remote handlers
- **Rotation**: Built-in `RotatingFileHandler` (10MB max, 5 backups)
- **Thread-safe**: Python's logging is thread-safe by design
- **Stack traces**: `exc_info=True` automatically captures exceptions
- **Separation of concerns**: Logging stays in logging framework's domain

**What RunContext Provides**:
- **run_logger**: Configured logger for this run
- **Automatic setup**: Logger configured with file handler, formatter, rotation
- **Run-specific**: Logger named `gavel_ai.{run_id}` to avoid conflicts

**Implementation**:
```python
# Context configures logger
self.run_logger = logging.getLogger(f"gavel_ai.{run_id}")
handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] <%(filename)s:%(lineno)s> %(message)s"))
self.run_logger.addHandler(handler)

# Steps use normal logging patterns
run_ctx.run_logger.info("Processing started")
run_ctx.run_logger.error("Processing failed", exc_info=True)
```

## Implementation Checklist

- [x] StorageBackend interface and implementations
- [x] DataSource types (Struct, Record, Text)
- [x] MultiFormatDataSource for reports
- [x] DataSourceCollection for collections
- [ ] EvalContext concrete implementation (in progress)
- [ ] RunContext concrete implementation (in progress)
- [ ] Pydantic schemas in `core/schemas.py`
- [ ] Integration with existing ConfigLoader
- [ ] Integration with existing workflows/steps
- [ ] Unit tests for data sources
- [ ] Integration tests with different backends
- [ ] Documentation and examples

## Related Files

**Implementation**:
- `src/gavel_ai/core/adapters/backends.py` - Storage backend implementations
- `src/gavel_ai/core/adapters/data_sources.py` - Data source implementations
- `src/gavel_ai/core/contexts.py` - Context implementations
- `src/gavel_ai/core/schemas.py` - Pydantic schemas (to be created)

**Specifications**:
- `data-schemas-specification.md` - Source of truth for data models
- `file-formats-specification.md` - Serialization format details

**Current Usage**:
- `src/gavel_ai/core/workflows/oneshot.py` - Workflow using contexts
- `src/gavel_ai/core/steps/*.py` - Steps using contexts

## Open Questions

1. **Caching strategy**: Should data sources cache reads? How to invalidate?
2. **Transactions**: Do we need transactional semantics for multi-artifact updates?
3. **Streaming writes**: Should RecordDataSource buffer writes for performance?
4. **Schema versioning**: How to handle schema evolution and migration?
5. **Concurrent access**: How to handle multiple processes writing to same run?

## Future Enhancements

1. **Advanced caching**: LRU cache for frequently accessed data
2. **Compression**: Transparent compression for large JSONL files
3. **Encryption**: Encrypt sensitive data at rest
4. **Replication**: Automatic backup to secondary storage
5. **Versioning**: Track changes to artifacts over time
6. **Indexing**: Fast queries on RecordDataSource (e.g., "find all failed scenarios")
7. **Partitioning**: Split large datasets across multiple files
8. **Lazy writing**: Buffer and batch writes for better performance

---

**Document Status**: Ready for review and implementation
**Next Steps**:
1. Review and refine API based on actual usage patterns
2. Implement remaining context methods
3. Create Pydantic schemas in `core/schemas.py`
4. Update workflows/steps to use new architecture
5. Add comprehensive tests
