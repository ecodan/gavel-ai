# Story 3.6: Implement Provider Abstraction with Pydantic-AI

Status: done

## Story

As a developer,
I want a unified provider interface for LLM calls,
So that I can support multiple providers (Anthropic, OpenAI, Google, Ollama) without coupling to specific APIs.

## Acceptance Criteria

1. **Provider Factory:**
   - Given ModelDefinition with provider configuration
   - When create_agent() is called
   - Then a configured Pydantic-AI Agent is returned

2. **Multi-Provider Support:**
   - Given provider is "anthropic", "openai", "google", or "ollama"
   - When agent is created
   - Then correct provider instance is configured with credentials

3. **LLM Call Execution:**
   - Given agent and prompt
   - When call_agent() is invoked
   - Then ProviderResult is returned with output and metadata

4. **Metadata Extraction:**
   - Given LLM response
   - When call completes
   - Then tokens, latency, provider info are captured in metadata

## Tasks / Subtasks

- [x] Task 1: Create providers module
  - [x] Create src/gavel_ai/providers/__init__.py
  - [x] Create src/gavel_ai/providers/factory.py
  - [x] Define ProviderResult Pydantic model

- [x] Task 2: Implement ProviderFactory
  - [x] Implement create_agent() for all providers
  - [x] Handle API key resolution from env vars
  - [x] Create provider instances with credentials
  - [x] Fallback to model string if needed

- [x] Task 3: Implement call_agent()
  - [x] Execute agent.run() async
  - [x] Extract output from response
  - [x] Extract metadata (tokens, latency, provider)
  - [x] Handle missing usage metadata gracefully

- [x] Task 4: Add error handling
  - [x] Wrap TimeoutError as ProcessorError
  - [x] Handle provider configuration errors
  - [x] Validate unsupported providers

- [x] Task 5: Write comprehensive tests (8 tests)
  - [x] Test factory initialization
  - [x] Test create_agent for each provider
  - [x] Test unsupported provider error
  - [x] Test call_agent execution
  - [x] Test metadata extraction
  - [x] Test timeout error handling
  - [x] Test missing usage metadata

- [x] Task 6: Integrate with PromptInputProcessor
  - [x] Update PromptInputProcessor to use ProviderFactory
  - [x] Replace mock with real Pydantic-AI calls

## Dev Agent Record

### Agent Model Used
Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Completion Notes
- ✅ Created providers module with ProviderFactory (205 lines)
- ✅ Support for Anthropic, OpenAI, Google, Ollama providers
- ✅ API key resolution from environment variables
- ✅ Metadata extraction (tokens, latency, provider info)
- ✅ 8 comprehensive unit tests (all passing)
- ✅ Integrated with PromptInputProcessor
- ✅ Telemetry spans for agent creation and calls

### File List

**New Files:**
- `src/gavel_ai/providers/__init__.py` (5 lines)
- `src/gavel_ai/providers/factory.py` (200 lines)
- `tests/unit/test_provider_factory.py` (8 tests)

**Modified Files:**
- `src/gavel_ai/processors/prompt_processor.py` (integrated ProviderFactory)

## Change Log

- **2025-12-29**: ✅ Implementation complete - 8 tests passing, all ACs satisfied
