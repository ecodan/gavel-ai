# Story 1.5: Create Central Logging Configuration

Status: review

## Story

As a developer,
I want centralized logging setup with standard format,
So that all modules log consistently and observability is clear.

## Acceptance Criteria

1. **Logger Configuration:**
   - Given log_config.py exists in src/gavel_ai/
   - When imported from any module
   - Then modules receive a configured logger with standard format:
     `"%(asctime)s [%(levelname)s] <%(filename)s:%(lineno)s> %(message)s"`

2. **Logger Usage:**
   - Given a module imports and uses the logger
   - When it writes log messages
   - Then messages appear in stdout (development) or file (production) with correct format

3. **Debug Mode:**
   - Given debug mode is enabled
   - When the application runs
   - Then DEBUG level logs are included

## Tasks / Subtasks

- [x] Task 1: Create log_config.py (AC: #1)
  - [x] Define LOGGER_NAME constant
  - [x] Create create_logger() function
  - [x] Set standard log format
  - [x] Configure stdout handler
  - [x] Support optional file logging

- [x] Task 2: Test logger across modules (AC: #2)
  - [x] Create test that imports logger
  - [x] Verify log format matches standard
  - [x] Verify messages appear with correct formatting

- [x] Task 3: Debug mode support (AC: #3)
  - [x] Add DEBUG environment variable support
  - [x] Adjust log level based on debug flag
  - [x] Verify DEBUG logs appear when enabled

### Review Follow-ups (AI Code Review)

- [ ] [MEDIUM] Missing thread-safety documentation - log_config.py module-level logger lacks docstring explaining thread-safety guarantees [src/gavel_ai/log_config.py:99]
- [ ] [MEDIUM] File List discrepancy - lists `tests/test_logging.py` but actual file is `tests/test_logging_config.py` [1-5 File List line 83]

## Dev Notes

### Logger Configuration

**Standard Format:**
```
"%(asctime)s [%(levelname)s] <%(filename)s:%(lineno)s> %(message)s"
```

**Example Output:**
```
2025-12-28 10:30:45,123 [INFO] <main.py:42> Application started
2025-12-28 10:30:46,456 [ERROR] <processor.py:87> Failed to process input
```

**Constants:**
- LOGGER_NAME: "gavel-ai"
- Default log level: INFO
- Debug log level: DEBUG (when GAVEL_DEBUG=true)

### Handler Configuration

**Development (stdout):**
- StreamHandler to stdout
- Color support via Rich (optional)
- Full traceback for exceptions

**Production (file):**
- RotatingFileHandler to gavel.log
- Max file size: 10MB
- Backup count: 5

## File List

- `src/gavel_ai/log_config.py` (new)
- `tests/test_logging.py` (new)

## Change Log

- **2025-12-28:** Story created with logging configuration module
- **2025-12-28:** Implementation completed and tested
  - ✅ All acceptance criteria met
  - ✅ log_config.py created with LOGGER_NAME, LOG_FORMAT, and create_logger() function
  - ✅ Standard logging format implemented: "%(asctime)s [%(levelname)s] <%(filename)s:%(lineno)s> %(message)s"
  - ✅ Debug mode support via GAVEL_DEBUG environment variable
  - ✅ File logging with RotatingFileHandler (10MB max, 5 backups)
  - ✅ 12 comprehensive test cases covering all functionality (test_logging_config.py)
  - ✅ All 12 logging tests passing
