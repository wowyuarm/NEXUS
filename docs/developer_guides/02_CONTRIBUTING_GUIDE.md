# 02: Contributing Guide

This guide is the canonical onboarding for anyone—human or AI—contributing to the YX NEXUS codebase. It builds on the global rules in `CLAUDE.md` / `AGENTS.md`; treat every instruction here as mandatory.

## Required Reading Before You Code
Review these documents at the start of every task. Reference them in your implementation plans when they inform a decision.
- `docs/developer_guides/04_AI_COLLABORATION_CHARTER.md`
- `tests/README.md`
- `docs/rules/frontend_design_principles.md` (for any UI/UX, motion, or styling work)
- `docs/developer_guides/03_TESTING_STRATEGY.md`
- Feature- or service-specific files uncovered during your contextual scan (see below)

## Documentation Workflow
1. **Task Brief** – Locate the closest `docs/tasks/*.md` entry and read it fully. Use the `Implementation/` subdirectory if a long-form plan already exists; otherwise create/update `IMPLEMENTATION_PLAN.md` at the project root.
2. **Reference Scan** – Pull architecture/protocol context from `docs/knowledge_base/` and `docs/api_reference/`; note the specific files you relied on.
3. **History Check** – Search `docs/learn/` for similar incidents to inherit lessons, adding citations in your plan.
4. **Future Alignment** – Review `docs/Future_Roadmap.md` to ensure upcoming initiatives are not impacted or to coordinate scope.
5. Document all consulted materials in your plan and final status update so reviewers can trace the reasoning.

## Core Philosophy
- **Security > Architecture > Process > Preference** — follow the priority order defined in the AI charter.
- **Context First** — understand the existing implementation before touching code. Inspect at least three related modules, handlers, or components.
- **TDD Discipline** — RED → GREEN → REFACTOR is the only accepted development loop.
- **Incremental Delivery** — favor small, verifiable changes that keep the repository buildable at every commit.
- **Transparency** — document assumptions, risks, and trade-offs explicitly in your notes or plan.

## Default Workflow
1. **Contextual Scan**
   - Read the required docs above.
   - Locate adjacent implementations with `rg`, repo search, or directory inspection.
   - Collect open design constraints (e.g., prompt layers, event contracts, motion rules).
2. **Implementation Plan**
   - Create or update `IMPLEMENTATION_PLAN.md` following the template in the AI charter.
   - Break work into 3–5 verifiable stages; keep only one stage `In Progress` at a time.
3. **Test First (RED)**
   - Add or extend tests in the correct location (`tests/nexus/...` or `aura/src/**/__tests__/`).
   - Run the relevant suite and confirm the new test fails for the expected reason.
4. **Minimal Implementation (GREEN)**
   - Write the smallest change to satisfy the failing test.
   - Stay within existing architectural boundaries (service, feature, store).
5. **Refactor & Harden**
   - Clean code and tests for readability and consistency.
   - Ensure formatting (`black`, Prettier) and lint tools (`flake8`, ESLint) pass.
   - Run the full relevant test scope (`pytest`, `pnpm test:run`, etc.).
6. **Self-Audit & Status Update**
   - Verify no unrelated files changed and no TODOs are left without tracking.
   - Update the implementation plan, marking completed stages.
   - Summarize results, risks, and test commands in your hand-off or PR description.

## Branching & Commits
- Branch from `main`; prefer descriptive names such as `feat/llm-dynamic-temperature`.
- Follow Conventional Commits (English only). Examples: `feat: add tool execution audit log`, `fix: respect websocket retry delay`, `refactor(ui): simplify tool card motion`.
- Each commit must be independently buildable and accompanied by passing tests for the changed area.
- Reference issue IDs or task identifiers when available.

## Local Command Reference
- Backend setup: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
- Backend run: `python -m nexus.main` (or `scripts/shell/run.sh` to launch backend + frontend together).
- Frontend setup: `cd aura && pnpm install`.
- Frontend dev: `pnpm dev`; build: `pnpm build`; lint: `pnpm lint`; tests: `pnpm test`, `pnpm test:run`, `pnpm test:coverage`.
- Containers: `docker-compose up --build` provisions `nexus-backend` and `aura-frontend` on `nexus-net`.

## Collaboration & Communication
- Respect the retry policy: after three failed attempts, prepare the escalation report described in the AI charter.
- Challenge unsafe or inefficient requests with data-backed alternatives.
- Keep all stakeholders informed about blockers, risks, and deviations from the plan.
- Document any assumption about environment variables, external services, or data fixtures.

## Common Scenarios
### 1. Adding a Backend Tool
1. Create a new file (or extend an existing one) under `nexus/tools/definition/`.
2. Implement a synchronous function with clear logging and error handling.
3. Provide an accompanying metadata dictionary constant matching the JSON schema (name, description, parameters, required).
4. Add unit or integration tests under `tests/nexus/unit/` or `tests/nexus/integration/` to verify registry behavior.
5. Update documentation or examples if the tool impacts user-facing behavior.

### 2. Extending WebSocket Protocol
1. Add or update topics in `nexus/core/topics.py` if a new channel is required.
2. Publish the new event inside the relevant service (`OrchestratorService`, etc.), ensuring payload structure matches existing conventions.
3. Update `aura/src/services/websocket/protocol.ts` with the new TypeScript types and type guard.
4. Wire the event into Zustand stores (`aura/src/features/chat/store/auraStore.ts`) and surface it through hooks/components.
5. Cover backend publishing with integration tests and frontend handling with Vitest suites under `__tests__/`.

### 3. Creating or Updating Frontend Components
1. Place presenter components in the appropriate feature `components` subfolder; keep logic in container/hooks.
2. Follow grayscale and motion rules from `docs/rules/frontend_design_principles.md`.
3. Co-locate tests under `__tests__/` using Testing Library and Vitest.
4. Validate type safety and linting before hand-off (`pnpm test:run`, `pnpm lint`).

### 4. Modifying a Core Service
1. Understand existing contracts by reviewing the service module, its tests, and dependent subscribers.
2. Update or add integration tests (`tests/nexus/integration/`) that assert bus interactions and side effects.
3. Ensure configuration dependencies are documented if new settings are introduced (`config.example.yml`).
4. If behavior surfaces in the UI, extend WebSocket or REST tests accordingly.

## Definition of Done Checklist
- [ ] Implementation plan stages completed and updated.
- [ ] New or modified tests written, fail before fix, and now pass.
- [ ] `pytest` (scope-appropriate) and `pnpm test:run` or other relevant suites executed successfully.
- [ ] Formatters and linters pass with no warnings.
- [ ] Secrets, credentials, or production configs are untouched.
- [ ] Risks, follow-ups, and verification steps documented in the task hand-off.

## References
- `CLAUDE.md`, `AGENTS.md`
- `docs/developer_guides/01_SETUP_AND_RUN.md`
- `docs/developer_guides/03_TESTING_STRATEGY.md`
- `docs/developer_guides/04_AI_COLLABORATION_CHARTER.md`
- `tests/README.md`
- `docs/rules/frontend_design_principles.md`
- `docs/tasks/`
- `docs/learn/`
- `docs/knowledge_base/`
- `docs/api_reference/`
- `docs/Future_Roadmap.md`
