# 02: Contributing Guide

This guide is the canonical onboarding for anyone—human or AI—contributing to the NEXUS codebase. It builds on the global rules in `CLAUDE.md` / `AGENTS.md`; treat every instruction here as mandatory.

## Required Reading Before You Code
Review these documents at the start of every task. Reference them in your implementation plans when they inform a decision.
- `docs/developer_guides/04_AI_COLLABORATION_CHARTER.md`
- `tests/README.md`
- `docs/rules/frontend_design_principles.md` (for any UI/UX, motion, or styling work)
- `docs/developer_guides/03_TESTING_STRATEGY.md`
- Feature- or service-specific files uncovered during your contextual scan (see below)

## Documentation Workflow
1. **Exploration Phase (Read-Only)** – Read foundational docs, scan related code (≥3 files), identify dependencies. No modifications during this phase.
2. **Task File Creation** – Create a three-part task file in `docs/tasks/YY-MMDD_name.md`:
   - **Part 1: Task Brief** – Background, objectives, deliverables, risk assessment (pragmatic technical risks only), dependencies (real technical dependencies only), references, acceptance criteria.
   - **Part 2: Implementation Plan** – Architecture overview, Phase 1/2/3... (decomposed by technical dependencies), detailed design with function signatures, complete test case lists.
   - **Part 3: Completion Report** – (Added after execution) Technical blog-style summary with implementation details, debugging processes, reflections.
3. **Reference Scan** – Pull architecture/protocol context from `docs/knowledge_base/` and `docs/api_reference/`; note the specific files you relied on.
4. **History Check** – Search `docs/learn/` for similar incidents to inherit lessons, adding citations in your task file.
5. **Future Alignment** – Review `docs/future/Future_Roadmap.md` to ensure upcoming initiatives are not impacted or to coordinate scope.
6. **Wait for Approval** – User reviews and approves the task file before execution begins.
7. **Execute & Document** – Follow TDD workflow, then append Part 3 (Completion Report) to the same task file.
8. Document all consulted materials in your task file and completion report so reviewers can trace the reasoning.

**For Large-Scale Initiatives**: If a task requires multiple conversations or exceeds context limits, create a strategic plan in `docs/strategic_plans/` that decomposes into multiple sub-tasks, each with its own task file in `docs/tasks/`.

## Core Philosophy
- **Security > Architecture > Process > Preference** — follow the priority order defined in the AI charter.
- **Context First** — understand the existing implementation before touching code. Inspect at least three related modules, handlers, or components.
- **TDD Discipline** — RED → GREEN → REFACTOR is the only accepted development loop.
- **Incremental Delivery** — favor small, verifiable changes that keep the repository buildable at every commit.
- **Transparency** — document assumptions, risks, and trade-offs explicitly in your notes or plan.

## Workflow Selection

Choose the appropriate workflow based on task complexity:

### Workflow A: Simple Changes (Direct Commit)

**Use for:** Documentation updates, minor config changes, simple fixes with no code logic changes.

**Steps:**
1. Quick verification: Confirm the change is truly simple (≤3 files, no business logic)
2. Make changes: Edit files directly on current branch (typically `main`)
3. Test & commit: Verify changes, commit with clear message

**No branch creation, no task file required.**

---

### Workflow B: Medium Tasks (Branch + Task File)

**Use for:** Feature additions, bug fixes, refactoring, or any work involving ≤15 files.

1. **Exploration Phase (Read-Only, MANDATORY FIRST STEP)**
   - Read all required documentation listed above.
   - Scan at least three related code files to understand existing patterns.
   - Identify technical dependencies and potential risks.
   - **No code changes or branch creation during this phase**.

2. **Branch Creation**
   - Check current branch: `git branch --show-current`
   - Create feature branch: `git checkout -b [type]/[descriptive-name]`
     - Types: `feat/`, `fix/`, `refactor/`, `docs/`, `test/`
     - Example: `feat/config-hot-reload`, `fix/websocket-timeout`
   - Verify branch: `git branch --show-current`

3. **Task File Creation**
   - Create `docs/tasks/YY-MMDD_descriptive-name.md` with three parts:
     - **Part 1: Task Brief** (Background, objectives, deliverables, risk assessment, dependencies, references, acceptance criteria)
     - **Part 2: Implementation Plan** (Architecture overview, Phase decomposition with detailed design and test cases)
     - **Part 3: Completion Report** (Leave empty until execution completes)
   - See `docs/tasks/README.md` for detailed format specifications.

4. **Wait for Approval**
   - Present the task file to the user.
   - Await explicit approval before proceeding to implementation.

5. **Test First (RED)**
   - Add or extend tests in the correct location (`tests/nexus/...` or `aura/src/**/__tests__/`).
   - Run the relevant suite and confirm the new test fails for the expected reason.

6. **Minimal Implementation (GREEN)**
   - Write the smallest change to satisfy the failing test.
   - Stay within existing architectural boundaries (service, feature, store).

7. **Refactor & Harden**
   - Clean code and tests for readability and consistency.
   - Ensure formatting (`black`, Prettier) and lint tools (`flake8`, ESLint) pass.
   - Run the full relevant test scope (`pytest`, `pnpm test:run`, etc.).

8. **Self-Audit**
   - Verify no unrelated files changed and no TODOs are left without tracking.
   - Run formatters and linters to ensure code quality.

9. **Append Completion Report (MANDATORY BEFORE COMMIT)**
   - Add Part 3 to the same task file with technical blog-style documentation:
     - Implementation overview and key decisions
     - Problems encountered and debugging processes (with failed attempts)
     - Test verification results (commands + outputs)
     - Reflections and improvement suggestions
   - **CRITICAL**: This must be completed BEFORE any commit.

10. **Wait for User Authorization to Commit**
    - Present completion status to user.
    - **NEVER commit unless user explicitly requests it**.
    - When user requests commit, use clear conventional commit messages.

---

### Workflow C: Large Initiatives (Branch + Strategic Plan)

**Use for:** Multi-conversation work, tasks exceeding context limits (>15 files).

1. **Exploration & Research**: Deep dive into architecture, dependencies, and scope.
2. **Branch Creation**: Create feature branch for the initiative.
3. **Strategic Plan Creation**: Create plan in `docs/strategic_plans/` that decomposes into multiple sub-tasks.
4. **Wait for Approval**: Present strategic plan to user.
5. **Execute Sub-Tasks**: Follow Workflow B for each sub-task.

## Branching & Commits

### Branch Management
- **Create a branch for medium and large tasks** — this project supports parallel development.
- **Simple changes can be committed directly to `main`** (documentation updates, minor fixes).
- Branch from `main`; use descriptive names following these patterns:
  - `feat/[feature-name]` for new features (e.g., `feat/llm-dynamic-temperature`)
  - `fix/[bug-description]` for bug fixes (e.g., `fix/websocket-timeout`)
  - `refactor/[scope]` for refactoring (e.g., `refactor/ui-tool-card`)
  - `docs/[topic]` for documentation (e.g., `docs/api-reference`)
  - `test/[scope]` for test additions (e.g., `test/orchestrator-service`)
- Keep branch names lowercase with hyphens (kebab-case), 3-5 words max.
- Push your branch regularly: `git push -u origin [branch-name]`

### Commit Guidelines
- Follow Conventional Commits (English only). Examples:
  - `feat: add tool execution audit log`
  - `fix: respect websocket retry delay`
  - `refactor(ui): simplify tool card motion`
  - `docs: update AI collaboration charter`
  - `test: add integration tests for orchestrator`
- Each commit must be independently buildable and accompanied by passing tests for the changed area.
- Reference issue IDs or task identifiers when available.
- Commit frequently with clear, descriptive messages explaining the "why" behind changes.

## Local Command Reference
- Backend setup: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
- Backend run: `python -m nexus.main` (or `scripts/shell/run.sh` to launch backend + frontend together).
- Frontend setup: `cd aura && pnpm install`.
- Frontend dev: `pnpm dev`; build: `pnpm build`; lint: `pnpm lint`; tests: `pnpm test`, `pnpm test:run`, `pnpm test:coverage`.
- Backend container (optional): `docker-compose up --build` provisions `nexus-backend` on `nexus-net`.
  - Note: Frontend is deployed on Vercel in production, no Docker container needed for frontend.

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
- [ ] All phases in the task file's Implementation Plan are executed.
- [ ] New or modified tests written, fail before fix, and now pass.
- [ ] `pytest` (scope-appropriate) and `pnpm test:run` or other relevant suites executed successfully.
- [ ] Formatters and linters pass with no warnings.
- [ ] Secrets, credentials, or production configs are untouched.
- [ ] Part 3 (Completion Report) appended to the task file with technical blog-level detail.
- [ ] Risks, follow-ups, and verification steps documented in the completion report.

## References
- `CLAUDE.md`, `AGENTS.md`
- `docs/developer_guides/01_SETUP_AND_RUN.md`
- `docs/developer_guides/03_TESTING_STRATEGY.md`
- `docs/developer_guides/04_AI_COLLABORATION_CHARTER.md`
- `tests/README.md`
- `docs/rules/frontend_design_principles.md`
- `docs/tasks/` – Single-conversation task files
- `docs/strategic_plans/` – Multi-conversation strategic initiatives
- `docs/learn/` – Postmortems and lessons learned
- `docs/knowledge_base/` – Architecture and technical references
- `docs/api_reference/` – API specifications
- `docs/future/Future_Roadmap.md`
