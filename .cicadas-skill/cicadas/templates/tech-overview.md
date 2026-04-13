
# Tech Overview

> Canon document. Updated by the Synthesis agent at the close of each initiative.

## What This Is

{1–2 sentence summary of the system from a technical perspective: what it does at the infrastructure/code level.}

---

## Tech Stack

| Category | Selection | Notes |
|----------|-----------|-------|
| **Language/Runtime** | {e.g., Python 3.10+} | {Any constraints or version locks} |
| **Framework** | {e.g., FastAPI / Django / None} | {Why, any key conventions} |
| **Database** | {e.g., PostgreSQL / SQLite / None} | {Schema location, migration tool} |
| **Auth** | {e.g., JWT / OAuth2 / Session / None} | {Where implemented} |
| **Frontend** | {e.g., React / Next.js / None} | {Entry point, build system} |
| **Testing** | {e.g., pytest / Jest} | {Coverage target} |
| **Key Libraries** | {List significant ones} | {Purpose} |
| **Deployment** | {e.g., Docker / Vercel / bare metal} | {Environment targets} |

---

## Project Structure

{Annotated directory tree showing the major areas. Focus on what a new contributor needs to orient themselves.}

```
{project-root}/
├── {module}/          # {what lives here}
├── {module}/          # {what lives here}
│   ├── {file}         # {purpose}
│   └── {file}         # {purpose}
└── {config-file}      # {purpose}
```

---

## Architecture

### System Design

{Describe the dominant architectural pattern: e.g., "Layered service architecture", "Event-driven pipeline", "Graph-based state engine", "CLI + filesystem". 1–2 paragraphs.}

### Key Components

| Component | Responsibility | Key Files |
|-----------|----------------|-----------|
| {Name} | {What it does} | `{path/to/file}` |
| {Name} | {What it does} | `{path/to/file}` |

### Data Flow

{How does data move through the system? Describe the primary execution path end-to-end. Use a diagram if the flow is complex.}

```
{Input} → [{Component A}] → [{Component B}] → {Output}
```

### Key Architecture Decisions

{Significant past decisions that constrain future work. Agents must not contradict these without explicit discussion.}

- **{Decision}:** {What was chosen and why — 1 sentence}
- **{Decision}:** {What was chosen and why}

---

## Data Models

### {Model Name}

```{language}
{Schema definition — field names, types, and key constraints}
```

**Key rules:**
- {Business rule or constraint that affects implementation}

---

## API & Interface Surface

### {Endpoint group or CLI command group}

```
{METHOD} {path}    # {one-line description}
{METHOD} {path}    # {one-line description}
```

### External Dependencies

| Service / API | Purpose | Auth method |
|---------------|---------|-------------|
| {Name} | {What we use it for} | {API key / OAuth / none} |

---

## Implementation Conventions

{Standards that all contributors must follow. These are the rules that keep parallel agent work compatible.}

### Naming

| Construct | Convention | Example |
|-----------|-----------|---------|
| {Functions/methods} | {snake_case} | `get_user_by_id()` |
| {Classes} | {PascalCase} | `UserRepository` |
| {Files} | {kebab-case or snake_case} | `user_service.py` |

### Key Patterns

- **Error handling:** {e.g., "Convert exceptions to domain errors at service boundary, never swallow"}
- **Testing:** {e.g., "Mock at service boundary; 70%+ coverage on non-trivial logic"}
- **Logging:** {e.g., "Structured JSON logs; never log secrets or PII"}

---

## Module Snapshots

{Reference to detailed module docs in `canon/modules/`. List what exists.}

- [`modules/{name}.md`](../modules/{name}.md) — {what it covers}

---

## Open Questions

{Known unknowns or deferred architecture decisions that affect future initiatives.}

- {Question} — {Owner / urgency}

