# Story 6.3: Implement Manifest (Run Metadata)

Status: ready-for-dev

## Story

As a user,
I want run metadata captured for reproducibility and tracking,
So that I can understand what was run, when, and with what configuration.

## Acceptance Criteria

- **Given** a run completes
  **When** manifest.json is examined
  **Then** it contains:
  - timestamp (ISO format)
  - config_hash (hash of all configs for reproducibility)
  - scenario_count (number of scenarios)
  - variant_count (number of variants)
  - judge_versions (list of judge versions)
  - status (completed, failed, partial)
  - duration (total run time)
  - metadata (custom key/value pairs)

- **Given** two runs with same config and scenarios
  **When** config_hash is compared
  **Then** they match (reproducibility verification)

**Related Requirements:** FR-3.2, FR-8.5

## Tasks / Subtasks

- [ ] Create Manifest model in src/gavel_ai/core/models.py (AC: 1)
  - [ ] Define all required fields with Pydantic
  - [ ] Use ConfigDict(extra="ignore")
  - [ ] Add Field descriptions for each attribute
  - [ ] Include timestamp as datetime field
  - [ ] Include status as Literal["completed", "failed", "partial"]

- [ ] Implement config hashing in src/gavel_ai/storage/manifest.py (AC: 2)
  - [ ] create_config_hash() function
  - [ ] Hash all eval configs deterministically
  - [ ] Use SHA-256 for reproducibility
  - [ ] Sort dict keys before hashing

- [ ] Add manifest methods to LocalFilesystemRun (AC: 1, 2)
  - [ ] save_manifest() method
  - [ ] load_manifest() method
  - [ ] Update artifacts property with manifest ArtifactRef

- [ ] Write comprehensive tests in tests/unit/storage/test_manifest.py (AC: All)
  - [ ] Test Manifest model validation
  - [ ] Test config_hash determinism (same config = same hash)
  - [ ] Test manifest save/load round-trip
  - [ ] Test all required fields present
  - [ ] Achieve 70%+ coverage

## Dev Notes

### Architecture Context

This story implements **Manifest metadata capture** for run reproducibility and tracking per FR-3.2 and FR-8.5.

**Key Principles:**
- Deterministic config hashing enables reproducibility verification
- manifest.json is primary run metadata file
- ISO 8601 timestamps for cross-platform compatibility
- Status tracking: completed, failed, partial

**Manifest Schema:**
```json
{
  "timestamp": "2025-12-30T12:00:00Z",
  "config_hash": "a1b2c3d4...",
  "scenario_count": 5,
  "variant_count": 2,
  "judge_versions": [
    {"judge_id": "similarity", "version": "deepeval-0.21.0"}
  ],
  "status": "completed",
  "duration": 45.2,
  "metadata": {
    "eval_name": "Claude vs GPT",
    "custom_key": "custom_value"
  }
}
```

### Dependencies

**CRITICAL: Stories 6.1 (Run ABC) and 6.2 (LocalFilesystemRun) must be complete.**

### Implementation Patterns

```python
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Dict, Any, List
from datetime import datetime
import hashlib
import json

class Manifest(BaseModel):
    """Run manifest with metadata for reproducibility."""
    model_config = ConfigDict(extra="ignore")

    timestamp: datetime = Field(..., description="Run start time (ISO 8601)")
    config_hash: str = Field(..., description="SHA-256 hash of all configs")
    scenario_count: int = Field(..., description="Number of scenarios")
    variant_count: int = Field(..., description="Number of variants")
    judge_versions: List[Dict[str, str]] = Field(..., description="Judge versions")
    status: Literal["completed", "failed", "partial"] = Field(..., description="Run status")
    duration: float = Field(..., description="Total run time in seconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")

def create_config_hash(configs: Dict[str, Any]) -> str:
    """Create deterministic hash of configs."""
    # Sort keys for determinism
    sorted_json = json.dumps(configs, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(sorted_json.encode()).hexdigest()
```

### References

- [Source: epics.md#Story 6.3] (lines 1263-1287)
- [Source: architecture.md#FR-3.2, FR-8.5]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

