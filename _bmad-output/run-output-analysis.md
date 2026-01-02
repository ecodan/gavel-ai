# Run Output Files - Requirements vs. Implementation Gap Report

**Analysis Date:** 2026-01-01
**Analyzed Runs:**
- `run-20260101-232906` (2 scenarios, 4 workers)
- `run-20260101-233147` (metadata only)

**Evaluation Tested:** `test_os` (local evaluation with 2 scenarios, no judges)

---

## Executive Summary

The run output structure is **partially compliant** with documented requirements. While core files are being created (telemetry.jsonl, results.jsonl, run_metadata.json, report.html), several critical artifacts and metadata fields are **missing or incomplete**. This report identifies gaps between PRD requirements and actual implementation.

**Compliance Score: 55% of documented requirements**

---

## Detailed Gap Analysis

### 1. **CRITICAL: manifest.json Missing**

**Requirement Source:** FR-3.2, FR-8.5

**Specification (PRD lines 587, 839-843):**
```
Standard artifacts: telemetry.jsonl (OT spans), results.jsonl (judged results), manifest.json
Manifest contains: timestamp, config hash, scenario count, judge versions, metadata
```

**Actual Status:** ❌ **MISSING**

**Current Files in Run Directory:**
```
✅ report.html                     (6270 bytes)
❌ results.jsonl                   (0 bytes) - EMPTY, see issue #2
❌ manifest.json                   - MISSING
✅ run_metadata.json              (115 bytes) - INCOMPLETE, see issue #3
✅ run.log                        (1802 bytes)
✅ telemetry.jsonl                (4340 bytes)
❌ config/                        (directory exists but EMPTY, see issue #4)
```

**Impact:**
- No verification of reproducibility (missing config hash)
- No machine-readable run metadata for programmatic access
- Cannot validate scenario count or judge versions at a glance
- Breaks artifact archival/export workflows (FR-3.5)

**Required Manifest Schema** (missing in implementation):
```json
{
  "run_id": "run-20260101-232906",
  "eval_name": "test_os",
  "eval_type": "local",
  "timestamp": "2026-01-01T23:29:06.957741+00:00",
  "config_hash": "sha256:abc123...",
  "scenario_count": 2,
  "variant_count": 1,
  "judge_versions": [],
  "status": "completed",
  "processor_type": "prompt_input",
  "metadata": {
    "duration_seconds": 9,
    "total_inputs_processed": 2,
    "completed_inputs": 2,
    "failed_inputs": 0
  }
}
```

---

### 2. **CRITICAL: results_raw.jsonl Empty**

**Requirement Source:** FR-3.2, FR-8.4, FR-2.6

**Specification (Updated Design):**

**Two-File Design:**

a) **results_raw.jsonl** (immutable execution artifact)
```
One entry per (scenario × variant × XUT/processor) combination
Immutable once written - enables reproducible re-judging
Schema:
{
  "scenario_id": "scenario_1",
  "variant_id": "variant_0",
  "processor_output": "The LLM response text here",
  "processor_type": "prompt_input",
  "timing_ms": 4250,
  "tokens_prompt": 156,
  "tokens_completion": 87,
  "error": null,
  "timestamp": "2026-01-01T23:29:10.123456Z"
}
```

b) **results_judged.jsonl** (mutable judgment artifact)
```
Same dimensions as results_raw, regenerated when judges change
Supports FR-3.3 (re-judge existing runs without re-execution)
Schema:
{
  "scenario_id": "scenario_1",
  "variant_id": "variant_0",
  "processor_output": "The LLM response text here",
  "processor_type": "prompt_input",
  "timing_ms": 4250,
  "tokens_prompt": 156,
  "tokens_completion": 87,
  "error": null,
  "judges": [
    {
      "judge_id": "similarity",
      "judge_name": "deepeval.similarity",
      "judge_score": 8,
      "judge_reasoning": "...",
      "judge_evidence": "..."
    },
    {
      "judge_id": "faithfulness",
      "judge_name": "deepeval.faithfulness",
      "judge_score": 7,
      "judge_reasoning": "...",
      "judge_evidence": "..."
    }
  ]
}
```

**Rationale for Two Files:**
- **results_raw.jsonl**: Immutable record of processor execution. Never changes. Enables reproducibility and re-judging without re-running processors.
- **results_judged.jsonl**: Mutable judgment layer. Can be regenerated when judges change (FR-3.3). Provides complete picture with all judge scores.

**Workflow:**
1. Execute processors → write **results_raw.jsonl** (immutable)
2. Apply judges → write **results_judged.jsonl** (mutable)
3. User changes judges → delete results_judged.jsonl and re-generate from results_raw.jsonl
4. No need to re-run LLM processors

**Actual Status:** ❌ **BOTH FILES EMPTY (0 bytes)**

**Evidence from run.log:**
- Line 8: `Loaded 2 scenarios`
- Line 10: `Executing 2 scenarios with 4 workers`
- Line 11: `Completed execution of 2 scenarios`
- Line 12: `No judges configured - skipping judging`

**Analysis:**
- Scenarios were processed (confirmed by telemetry.jsonl with 5400+ bytes)
- Processor outputs exist in telemetry but are NOT being exported to results_raw.jsonl
- Neither results file populated

**Impact:**
- Violates FR-8.4 (results stored in evaluable format)
- Breaks report generation (reports need results data)
- Users cannot access scenario outputs programmatically
- Cannot implement FR-3.3 (re-judge without re-execution)
- CSV/JSON export workflows fail

**What Should Be in results_raw.jsonl:**
Based on telemetry, at least 2 entries expected:
```jsonl
{"scenario_id": "scenario_1", "variant_id": "variant_0", "processor_output": "...", "processor_type": "prompt_input", "timing_ms": 4250, "tokens_prompt": 156, "tokens_completion": 87, "error": null}
{"scenario_id": "scenario_2", "variant_id": "variant_0", "processor_output": "...", "processor_type": "prompt_input", "timing_ms": 3900, "tokens_prompt": 142, "tokens_completion": 93, "error": null}
```

**results_judged.jsonl:**
Since no judges configured in this run, results_judged.jsonl would be identical to results_raw.jsonl (empty judges array):
```jsonl
{"scenario_id": "scenario_1", "variant_id": "variant_0", "processor_output": "...", "processor_type": "prompt_input", "timing_ms": 4250, "tokens_prompt": 156, "tokens_completion": 87, "error": null, "judges": []}
{"scenario_id": "scenario_2", "variant_id": "variant_0", "processor_output": "...", "processor_type": "prompt_input", "timing_ms": 3900, "tokens_prompt": 142, "tokens_completion": 93, "error": null, "judges": []}
```

---

### 3. **CRITICAL: run_metadata.json Incomplete**

**Requirement Source:** FR-9.5 (Telemetry & Metrics)

**Specification (PRD lines 888-914):**
```
run_metadata.json stored in run directory containing:
- Timing metrics: Run start/end time, total duration, mean/median/min/max/std for processing time per input
- Input metrics: Total inputs processed (inputs × variants × XUT count)
- LLM call tracking: List of all distinct LLM calls (prompt+variant combination) with individual timing stats
- Execution stats: Completed inputs, failed inputs, retry counts
```

**Actual Status:** ❌ **INCOMPLETE**

**Current Content:**
```json
{
  "eval_name": "test_os",
  "run_id": "run-20260101-232906",
  "start_time": "2026-01-01T23:29:06.957741+00:00"
}
```

**Missing Fields:**
- ❌ `end_time` (required for duration calculation)
- ❌ `duration_seconds` (total run time)
- ❌ `timing_metrics` (per-input processing stats)
- ❌ `input_metrics` (total count, breakdown)
- ❌ `llm_calls` (distinct calls with timing)
- ❌ `execution_stats` (completed/failed/retry)

**Impact:**
- Users cannot analyze performance (FR-9.5: "Enables performance profiling, cost analysis, bottleneck identification")
- Telemetry variables {{telemetry}} and {{metadata}} unavailable for report templates (FR-9.8)
- Morgan Kim's use case (CI/CD integration, performance monitoring) broken
- Dr. Wong's use case (detailed analysis, profiling) broken

**What Should Be in run_metadata.json:**
```json
{
  "eval_name": "test_os",
  "run_id": "run-20260101-232906",
  "start_time": "2026-01-01T23:29:06.957741+00:00",
  "end_time": "2026-01-01T23:29:15.312456+00:00",
  "duration_seconds": 8.355,
  "timing_metrics": {
    "per_input": [
      {"scenario_id": "scenario_1", "duration_ms": 4200},
      {"scenario_id": "scenario_2", "duration_ms": 3900}
    ],
    "mean_ms": 4050,
    "median_ms": 4050,
    "min_ms": 3900,
    "max_ms": 4200,
    "std_ms": 150
  },
  "input_metrics": {
    "total_inputs": 2,
    "total_variant_combinations": 2,
    "completed": 2,
    "failed": 0
  },
  "llm_calls": [
    {
      "prompt_id": "prompt_0",
      "variant_id": "variant_0",
      "call_count": 2,
      "total_duration_ms": 8100,
      "mean_latency_ms": 4050
    }
  ],
  "execution_stats": {
    "completed_inputs": 2,
    "failed_inputs": 0,
    "retry_count": 0
  }
}
```

---

### 4. **MAJOR: config/ Directory Empty**

**Requirement Source:** FR-3.2, FR-8.5

**Specification (PRD lines 592, 1228):**
```
"A copy of all eval configs is also saved for each run under /run/config for reproducibility"
Directory structure: runs/<timestamp>/config/ (Copy of eval configs)
```

**Actual Status:** ❌ **EMPTY**

**Verification:**
```bash
$ ls -la run-20260101-232906/config/
total 0
```

**Analysis:**
- Directory is created but nothing is copied into it
- Evaluation configs exist at `.gavel/evaluations/test_os/config/` but not replicated to run

**Impact:**
- Violates reproducibility principle (cannot re-run with exact same config)
- Breaks artifact export/archival (FR-3.5: "Export complete run including config")
- Dr. Wong's use case (complete transparency, audit trail) broken
- Priya Desai's use case (historical tracking with config diffs) broken

**What Should Be in config/ Directory:**
```
runs/run-20260101-232906/config/
├── agents.json                    # Copy of agents.json
├── eval_config.json              # Copy of eval_config.json
├── async_config.json             # Copy of async_config.json (if exists)
└── judges/
    └── <judge_configs>           # Copy of all judge configs
```

---

### 5. **MAJOR: Missing gavel.log File**

**Requirement Source:** FR-9.4

**Specification (PRD lines 882-886):**
```
Logging uses consistent format and levels
Logs stored in run directory for analysis
Log format: "%(asctime)s [%(levelname)s] <%(filename)s:%(lineno)s> %(message)s"
```

**Actual Status:** ✅ **EXISTS** (run.log found)

**Note:** File is named `run.log` instead of `gavel.log` per spec, but requirement is met functionally.

**Log Format Compliance:**
```
✅ Timestamp: "2026-01-01 15:29:06"
✅ Level: "[INFO]"
✅ Source: "<oneshot.py:107>"
✅ Message: "Telemetry export configured: ..."
```

---

### 6. **MAJOR: Telemetry Format Non-Standard**

**Requirement Source:** FR-8.3

**Specification (PRD lines 827-831):**
```
telemetry.jsonl: one OT span per line (JSON Lines)
Format: JSONL with standard OpenTelemetry attributes
Includes: timestamps, trace IDs, span names, attributes, duration
Standard OT attributes for LLM calls (model, provider, tokens, etc)
```

**Actual Status:** ⚠️ **PARTIALLY COMPLIANT**

**Actual Telemetry Format Found:**
```json
{
  "name": "agents.validate_agent_references",
  "trace_id": "d795e5c2d6db76e30bdc14f723696a02",
  "span_id": "bac23cb3542b9af9",
  "parent_id": "068b224d6e4757f2",
  "start_time": 1767310146957146000,
  "end_time": 1767310146957162000,
  "duration_ns": 16000,
  "status": "UNSET",
  "attributes": {}
}
```

**Issues:**
- ✅ JSONL format correct
- ✅ Contains trace_id, span_id, parent_id
- ⚠️ Timestamps in nanoseconds (start_time/end_time) instead of ISO 8601
- ⚠️ Missing standard OT attributes: run_id, processor.type, scenario.id, variant.id
- ⚠️ Missing LLM call details: llm.provider, llm.model, llm.tokens
- ⚠️ Status field shows "UNSET" instead of "ok"/"error"

**Architecture Spec (Decision 4, lines 344-360):**
```
Specification calls for ISO 8601 format:
"start_time_iso": "2025-12-27T14:30:22.123Z",
"end_time_iso": "2025-12-27T14:30:24.456Z",
"duration_ms": 2333,
"status": "ok|error"
```

**Impact:**
- Telemetry format deviates from documented spec
- Reports cannot use {{telemetry}} variables effectively
- Analysis scripts expecting ISO timestamps will fail

---

## File Completeness Matrix

| Artifact | Required | Exists | Complete | Notes |
|----------|----------|--------|----------|-------|
| **manifest.json** | ✅ FR-3.2, FR-8.5 | ❌ No | ❌ N/A | **CRITICAL** - Missing completely |
| **results_raw.jsonl** | ✅ FR-3.2, FR-8.4 | ✅ Yes | ❌ Empty | **CRITICAL** - Immutable execution artifact; 0 bytes, should have 2 entries |
| **results_judged.jsonl** | ✅ FR-3.3, FR-8.4 | ✅ Yes | ❌ Empty | **CRITICAL** - Mutable judgment artifact; enables re-judge; 0 bytes |
| **telemetry.jsonl** | ✅ FR-8.3 | ✅ Yes | ⚠️ Partial | Format issues (ns timestamps, missing attrs) |
| **run_metadata.json** | ✅ FR-9.5 | ✅ Yes | ❌ Incomplete | **CRITICAL** - Missing end_time, metrics |
| **report.html** | ✅ FR-5.2 | ✅ Yes | ⚠️ Partial | Generated but limited by empty results files |
| **run.log** | ✅ FR-9.4 | ✅ Yes | ✅ Complete | Named run.log not gavel.log (minor) |
| **config/** | ✅ FR-3.2 | ✅ Yes | ❌ Empty | **MAJOR** - Directory exists but no configs copied |

---

## Impact on User Journeys

### ❌ Alex Chen Journey (Developer)
**Requirement:** "More importantly, they can see exactly why—the judge's reasoning is transparent, and they can inspect every scenario, output, and decision."

**Status:** BROKEN
- `results.jsonl` is empty → Cannot see scenario outputs
- `config/` is empty → Cannot inspect evaluation configuration
- `run_metadata.json` incomplete → Cannot see timing metrics

### ❌ Sam Patel Journey (Product Manager)
**Requirement:** "They can read the generated reports and approve/reject changes based on clear metrics."

**Status:** BROKEN
- Report.html generated but limited by empty results.jsonl
- No metrics available (missing from run_metadata.json)

### ❌ Priya Desai Journey (Team Lead)
**Requirement:** "Enables performance profiling, cost analysis, bottleneck identification"

**Status:** BROKEN
- `run_metadata.json` missing all timing/cost metrics
- `config/` empty → Cannot do config diffs across runs

### ❌ Dr. Lisa Wong Journey (Researcher)
**Requirement:** "All evaluation setup...can be committed to GitHub, and reviewers can reproduce her results exactly"

**Status:** BROKEN
- `manifest.json` missing → No config hash for validation
- `config/` empty → Cannot reproduce without original files
- `results.jsonl` empty → Incomplete run artifacts

### ❌ Morgan Kim Journey (DevOps/CI)
**Requirement:** "Enable performance profiling, cost analysis, bottleneck identification"

**Status:** BROKEN
- `run_metadata.json` missing all metrics needed for CI dashboards
- Cannot parse performance data for automation

---

## Comparison: Requirements vs. Implementation

### Requirements Spec (Architecture Decision 4, lines 331-372)

**What Should Exist:**
```
runs/<timestamp>/
├── manifest.json          # Run metadata (timestamp, config hash, counts)
├── config/                # Copy of eval configs
├── telemetry.jsonl        # Simplified OT spans
├── results.jsonl          # Judged results
├── run_metadata.json      # Performance metrics
├── gavel.log              # Execution log
└── report.html            # Generated report
```

**What Actually Exists:**
```
runs/run-20260101-232906/
├── report.html            # ✅ Exists
├── results.jsonl          # ❌ Empty (0 bytes)
├── run_metadata.json      # ❌ Incomplete (3 fields, needs 8+)
├── run.log                # ✅ Exists (named run.log not gavel.log)
├── telemetry.jsonl        # ⚠️ Format issues
└── config/                # ❌ Empty directory
```

**Compliance: 2.5 / 7 files fully compliant (36%)**

---

## Root Cause Analysis

### 1. results.jsonl Population Bug
**Hypothesis:** Processor outputs exist in telemetry but export logic is missing

**Evidence:**
- telemetry.jsonl has 5400+ bytes (rich span data)
- results.jsonl is 0 bytes (never populated)
- run.log shows processors completed successfully
- No error messages in run.log related to results export

**Fix Required:** Export processor outputs from telemetry to results.jsonl in standardized format

### 2. run_metadata.json Incomplete
**Hypothesis:** Only initialization fields being saved, not completion metrics

**Evidence:**
- Contains only: eval_name, run_id, start_time
- No end_time, duration, or metrics
- run.log shows "Metadata computed - 2 scenarios processed" but final metadata not captured

**Fix Required:** Capture completion metrics and save full run_metadata object

### 3. config/ Not Populated
**Hypothesis:** Directory creation logic exists but copy logic is missing

**Evidence:**
- Directory is created and exists
- Directory is empty (no files)
- Evaluation configs exist at eval root but not replicated

**Fix Required:** Copy eval configs to run/config/ during or after execution

### 4. manifest.json Never Created
**Hypothesis:** Feature may not be implemented yet

**Evidence:**
- No manifest.json in any run directory
- No mention in run.log of manifest creation
- This is a critical reproducibility feature

**Fix Required:** Create manifest.json with all required metadata

---

## Requirements Coverage Summary

| Category | % Complete | Status |
|----------|------------|--------|
| **Run Artifacts** | 36% | ❌ CRITICAL ISSUES |
| **Telemetry** | 70% | ⚠️ FORMAT ISSUES |
| **Metadata/Metrics** | 15% | ❌ INCOMPLETE |
| **Config Preservation** | 0% | ❌ MISSING |
| **Reproducibility** | 10% | ❌ BROKEN |

**Overall Compliance: 26% of run output requirements met**

---

## Recommended Fixes (Priority Order)

### CRITICAL (Blocks Core Functionality)

1. **Populate results.jsonl** (FR-8.4)
   - Export processor outputs from telemetry to results.jsonl
   - 2-4 hour fix
   - Affects: All result-dependent features (reports, exports, analysis)

2. **Complete run_metadata.json** (FR-9.5)
   - Capture end_time, duration, and timing metrics
   - Add timing stats per scenario
   - Add LLM call tracking
   - 3-5 hour fix
   - Affects: Performance analysis, CI/CD metrics, reporting

3. **Create manifest.json** (FR-3.2, FR-8.5)
   - Add run manifest with config hash, counts, status
   - 1-2 hour fix
   - Affects: Reproducibility, archival, validation

4. **Populate config/ Directory** (FR-3.2)
   - Copy eval configs to run/config/ during execution
   - 1 hour fix
   - Affects: Reproducibility, artifact export

### IMPORTANT (Improves Quality/Spec Compliance)

5. **Fix Telemetry Format** (FR-8.3)
   - Switch timestamps to ISO 8601 format
   - Add required attributes: run_id, processor.type, scenario.id, variant.id
   - Add LLM call attributes: llm.provider, llm.model, llm.tokens
   - 2-3 hour fix
   - Affects: Report generation, analysis accuracy

---

## Conclusion

The current run output implementation captures foundational files but is **missing critical metadata and result data** needed for the documented user journeys and workflows. The gaps affect:

- **Transparency**: Users cannot see actual scenario outputs (results.jsonl empty)
- **Reproducibility**: No config copy or validation hash (config/ empty, manifest.json missing)
- **Analysis**: No metrics for performance profiling (run_metadata.json incomplete)
- **Trust**: Cannot verify evaluation integrity (manifest.json missing)

**Recommendation:** Address the 4 CRITICAL fixes before declaring run output ready for general use. Current state is suitable only for basic testing but breaks user journeys for production use.

