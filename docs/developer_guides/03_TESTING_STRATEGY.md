# 03: Testing Strategy

This document formalizes the testing approach for NEXUS and complements the mandatory charter in `tests/README.md`. Follow these practices along with the project-wide rules in `CLAUDE.md` / `AGENTS.md`.

## Required Reading
- `tests/README.md` – authoritative TDD policy and QA pyramid
- `docs/developer_guides/04_AI_COLLABORATION_CHARTER.md` – planning, retry protocol, definition of done
- Feature or service documentation pertinent to the area under test (e.g., `nexus/services/**`, `aura/src/features/**`)

## Guiding Principles
- **TDD Always**: Write the failing test first, observe RED → GREEN → REFACTOR.
- **Confidence with Pragmatism**: Favor fast, deterministic tests that mirror real contracts.
- **Contracts Over Internals**: Assert observable behavior (events published, UI rendered, state mutations) instead of private implementation details.
- **Isolation Where It Matters**: Mock external services, network calls, and databases unless the test layer explicitly calls for live integration.

## The NEXUS Testing Pyramid

### Layer 1 – Backend Unit & Service Tests (Foundation)
- **Location**: `tests/nexus/unit/` and `tests/nexus/integration/`
- **Purpose**: Validate pure logic (unit) and service-level behavior within the event-driven system (integration).
- **Tooling**: `pytest`, `pytest-asyncio`, `pytest-mock`
- **Patterns**:
  - Unit tests mock all IO and focus on deterministic logic (e.g., prompt assembly utilities, tool registry helpers).
  - Integration tests construct real service instances with mocked dependencies (especially `NexusBus`) and assert published messages or state transitions.
- **When to Add**: Any change inside `nexus/services/`, `nexus/core/`, or backend utilities.
- **Example**: Verifying `OrchestratorService` publishes expected events when receiving a `Topics.RUN_STARTED` message.

### Layer 2 – Frontend Component, Hook, & Store Tests (Core)
- **Location**: Colocated under `__tests__/` directories within feature folders, e.g., `aura/src/features/chat/components/__tests__/ChatInput.test.tsx`
- **Purpose**: Ensure React components, Zustand stores, and hooks behave as designed across interaction scenarios.
- **Tooling**: Vitest (`pnpm test`, `pnpm test:run`, `pnpm test:coverage`), Testing Library, `@testing-library/user-event`
- **Patterns**:
  - Treat components as black boxes: render, simulate user behavior, and observe DOM output.
  - For stores/hooks, initialize state with the provided helpers and assert state snapshots or emitted actions.
  - Respect the grayscale design and motion rules when asserting styles; prefer semantic expectations over pixel checks.
- **When to Add**: UI changes, new WebSocket event handling, state-store mutations, or hook refactors.
- **Example**: Testing `ToolCallCard` renders the correct status timeline when a tool completes with streaming output.

### Layer 3 – Backend End-to-End (Apex)
- **Location**: `tests/nexus/e2e/`
- **Purpose**: Validate critical user journeys across the fully wired backend (FastAPI, WebSocket, Mongo persistence).
- **Tooling**: `pytest`, `pytest-asyncio`, `httpx`, `websockets`; fixtures spin up the service and temporary Mongo instance.
- **Usage**:
  - Reserved for high-value flows (e.g., complete run with tool execution).
  - Executed manually or pre-release; not part of default CI to avoid flakiness.
- **Example**: `test_full_interaction_flow.py` connecting via WebSocket, sending user input, and asserting the resulting event stream.

## Writing Effective Tests
- Mirror naming conventions: `test_<behavior>_<expected_outcome>`.
- Use fixtures from `tests/conftest.py` or feature-specific helpers to reduce duplication.
- Prefer parametrization when covering multiple scenarios of the same behavior.
- Validate enums and constants (e.g., `Role`, topic names) against real definitions before asserting.
- Limit snapshot tests to stable UI fragments; justify them in the PR description.
- Keep tests resilient to refactors by focusing on public API contracts.

## Running Tests
```bash
# Backend – entire suite
pytest

# Backend – targeted scopes
pytest tests/nexus/unit
pytest tests/nexus/integration
pytest tests/nexus/e2e/test_full_interaction_flow.py::test_tool_call_interaction

# Frontend – watch / CI / coverage
cd aura
pnpm test        # watch mode
pnpm test:run    # CI-friendly
pnpm test:coverage
```
- Run lint/format commands (`flake8`, `black`, `pnpm lint`) after making changes.
- Record the commands you executed in your task summary or PR template.

## Fixture & Data Management
- Reuse shared fixtures in `tests/conftest.py` for backend services and event bus setup.
- Frontend tests can define local fixtures inside `__tests__/fixtures.ts` or similar files.
- When integration tests require Mongo data, seed via fixtures and clean up between tests; never point at production databases.
- Avoid hard-coding secrets or environment-specific paths; use configuration helpers or dependency injection.

## When to Escalate Testing Concerns
- Flaky or slow tests discovered during implementation must be flagged immediately with reproduction details.
- If a new feature cannot be covered with existing layers, propose an extension to the pyramid in your plan before coding.
- For cross-cutting changes (e.g., protocol redesigns), coordinate updates for backend + frontend tests within the same effort.

## References
- `tests/README.md`
- `docs/developer_guides/02_CONTRIBUTING_GUIDE.md`
- `docs/developer_guides/04_AI_COLLABORATION_CHARTER.md`
- `docs/rules/frontend_design_principles.md`
