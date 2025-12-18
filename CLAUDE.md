# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. Treat every instruction as binding policy, not optional advice.

## Before You Start
- `docs/developer_guides/04_AI_COLLABORATION_CHARTER.md` – mandatory planning, retry, and communication protocol.
- `tests/README.md` – TDD workflow and testing pyramid expectations.
- `docs/rules/frontend_design_principles.md` – required for any UI, motion, or styling work.
- `docs/rules/LOGIC_SCHEMA.md` – logic-first meta-language schema + playbook (treat it as an executable prompt).
- `LOGIC_MAP.md` – project logic map index (if missing, create/update it using `docs/rules/LOGIC_SCHEMA.md`).
- `docs/developer_guides/02_CONTRIBUTING_GUIDE.md` and `docs/developer_guides/03_TESTING_STRATEGY.md` – workflow and test patterns.
- `docs/tasks/` – Three-part task files (Task Brief → Implementation Plan → Completion Report) for single-conversation work. See `tasks/README.md` for detailed format specifications.
- `docs/strategic_plans/` – Strategic planning documents for large-scale initiatives requiring multiple conversations or exceeding context limits.
- `docs/knowledge_base/` and `docs/api_reference/` – architectural, protocol, and reference material to cite during planning.
- `docs/learn/` – past incident reports and lessons; scan for similar issues when debugging.
- `docs/Future_Roadmap.md` – upcoming initiatives that may affect scope or design decisions.
- For unfamiliar domains, inspect at least three related implementations or tests before writing new code. Reference the material you consult in task files or status updates.

## Logic Map Protocol (MANDATORY)

This repository uses a logic-first mapping layer to make both humans and agents effective at navigating the codebase.

- `docs/rules/LOGIC_SCHEMA.md` defines the schema + methodology (treat it as an executable prompt).
- `LOGIC_MAP.md` (repo root) is the project-specific instance (small, stable, frequently updated).

### Required behavior (every task)

1. **Bootstrap / read**
   - If `LOGIC_MAP.md` exists: read it first and use its `FLOW-*` / `CMP-*` / `INV-*` nodes to scope exploration.
   - If `LOGIC_MAP.md` does not exist: create it using the template in `docs/rules/LOGIC_SCHEMA.md` (§6.1). Keep v0 intentionally small; anchors must be grep-able (`file#SymbolPath`), avoid line numbers.

2. **Explore via graph, not by scanning**
   - Traverse `relations` outward to find entrypoints, implementations, and constraints.
   - Follow `anchors` / `refs` into code/tests/config.
   - Only if anchors are insufficient: search for symbols, then write new anchors/relations back into `LOGIC_MAP.md`.

3. **Maintenance is part of done**
   - Before declaring completion, update `LOGIC_MAP.md` to reflect what you learned or changed:
     - behavior changes: update `FLOW-*`
     - dependency changes: update/add `REL-*`
     - new constraints: update/add `INV-*` and preferably `EVD-*`
     - moved symbols: update anchors
   - If no update is needed, explicitly state why (map already covered it).

## Architecture Overview
- **Backend (NEXUS)** – FastAPI event-driven service orchestrating `NexusBus`, `ConfigService`, `DatabaseService`, `PersistenceService`, `IdentityService`, `CommandService`, `ContextService`, `ToolExecutorService`, `LLMService`, and `OrchestratorService`, plus REST/WebSocket interfaces (`nexus/main.py`).
- **Frontend (AURA)** – React 19 + TypeScript + Vite client using Zustand state, Tailwind CSS (grayscale-only tokens), and Framer Motion.
- **Tool System** – Functions and metadata in `nexus/tools/definition/` auto-discovered by `ToolRegistry.discover_and_register('nexus.tools.definition')`.

## Repository Layout
- `nexus/core/` – Bus, topics, shared models.
- `nexus/services/` – Service implementations; keep responsibilities bounded by existing modules or propose new folders.
- `nexus/interfaces/` – `rest.py` and `websocket.py` IO surfaces.
- `nexus/prompts/` – Prompt layer templates exposed to clients.
- `aura/src/` – Feature-first frontend tree (`app/`, `components/`, `features/`, `hooks/`, `services/`, `stores/`, `lib/`, `test/setup.ts`).
- **Testing** – Backend suites live in `tests/nexus/{unit,integration,e2e}` with fixtures in `tests/conftest.py`; frontend Vitest suites sit alongside code under `__tests__/` directories (e.g., `aura/src/features/chat/components/__tests__/`).
- Tooling helpers: `scripts/shell/run.sh` (local bootstrap) and `docker-compose.yml` (container orchestration).

## Git & Branch Management (MANDATORY)
**CRITICAL**: After the exploration phase (read-only), you MUST create a dedicated feature branch before any modifications. This project supports parallel development across multiple branches.

### Branch Creation Protocol
1. **Complete Exploration First**: Read docs, scan code, identify dependencies – NO branch creation or modifications yet.
2. **Check Current Branch**: Run `git branch --show-current` to verify current branch.
3. **Pull Latest Changes** (if no uncommitted changes): Run `git pull origin main` to ensure you have the latest code.
4. **Create Feature Branch**: Use descriptive naming following these patterns:
   - `feat/[feature-name]` for new features (e.g., `feat/llm-dynamic-temperature`)
   - `fix/[bug-description]` for bug fixes (e.g., `fix/websocket-timeout`)
   - `refactor/[scope]` for refactoring (e.g., `refactor/ui-tool-card`)
   - `docs/[topic]` for documentation updates (e.g., `docs/api-reference`)
   - `test/[scope]` for test additions (e.g., `test/orchestrator-service`)
5. **Verify Branch Creation**: Run `git branch --show-current` to confirm you're on the new branch.

### Branch Naming Rules
- Use lowercase with hyphens (kebab-case)
- Be descriptive but concise (3-5 words max)
- Include scope/context when helpful
- Examples: `feat/config-hot-reload`, `fix/deepseek-streaming-timeout`, `refactor/aura-store-types`

### Working on Branches
- **Never work directly on `main`** unless explicitly instructed
- Keep branches focused on a single task or feature
- Commit frequently with clear conventional commit messages
- Push your branch regularly: `git push -u origin [branch-name]`
- Before merging, ensure all tests pass and code is formatted

### Branch Lifecycle
1. Create branch from `main`
2. Implement changes following TDD workflow
3. Commit with conventional commit messages
4. Push branch to remote
5. Create Pull Request when ready
6. After merge, delete the feature branch

## Documentation-Driven Workflow

### For Single-Conversation Tasks
1. **Exploration Phase (Read-Only)**: Read foundational docs, scan related code (≥3 files), identify dependencies and risks. No modifications yet.
2. **Create Branch**: After exploration, create feature branch following the protocol above.
3. **Create Task File**: Create `docs/tasks/YY-MMDD_name.md` with three parts:
   - **CRITICAL**: Before creating any task file, MUST read `docs/tasks/README.md` to understand the required three-part format and guidelines.
   - **Part 1: Task Brief** – Background, objectives, deliverables, pragmatic risk assessment, real technical dependencies, references, acceptance criteria.
   - **Part 2: Implementation Plan** – Architecture overview, phase-based decomposition (by technical dependencies), detailed design with function signatures, complete test case lists.
   - **Part 3: Completion Report** – (Leave empty until execution completes)
4. **Wait for Approval**: Present task file to user for review and approval.
5. **Execute Implementation**: Follow TDD workflow (RED → GREEN → REFACTOR), commit frequently.
6. **Append Completion Report**: Add Part 3 with technical blog-style documentation: implementation details, debugging processes (including failed attempts), test verification, reflections, and links to commits/PRs.

### For Large-Scale Initiatives
If a task requires multiple conversations or exceeds context limits (>15 files), create a strategic plan in `docs/strategic_plans/` that decomposes into multiple sub-tasks, each with its own task file in `docs/tasks/`.

### Context Gathering
- Pull architectural details from `docs/knowledge_base/` and protocol specifics from `docs/api_reference/`.
- Search `docs/learn/` for similar incidents to avoid repeating past issues.
- Confirm your design does not conflict with items in `docs/Future_Roadmap.md`.
- **Best Practice**: Always read README files in relevant directories before creating or modifying documentation.
- Cite every document consulted in your task file.

## Development Workflow
1. **Exploration Phase (MANDATORY FIRST STEP - Read-Only)**
   - Read required documentation
   - Scan at least 3 related code files
   - Identify dependencies and risks
   - NO code changes or branch creation yet

2. **Branch Creation (MANDATORY SECOND STEP)**
   ```bash
   git branch --show-current        # verify current branch
   git pull origin main             # pull latest (if no uncommitted changes)
   git checkout -b [type]/[name]    # create feature branch
   git branch --show-current        # confirm new branch
   ```
   **Never work directly on `main`** unless explicitly instructed.

3. **Backend** (Poetry-based)
   ```bash
   # Install Poetry (if not installed)
   curl -sSL https://install.python-poetry.org | python3 -
   
   # Install dependencies
   poetry install
   
   # Run backend
   poetry run python -m nexus.main
   ```
4. **Frontend**
   ```bash
   cd aura
   pnpm install
   pnpm dev
   pnpm build      # production bundle
   pnpm lint       # ESLint
   pnpm test       # Vitest watch
   pnpm test:run   # Vitest CI
   pnpm test:coverage
   ```
   _Note_: there is no `pnpm typecheck` script today; add one only with team approval.
5. Use `scripts/shell/run.sh` to launch both stacks locally once dependencies are installed. `docker-compose.yml` builds `nexus-backend` and `aura-frontend` on the `nexus-net` bridge network.
6. Always follow the RED → GREEN → REFACTOR cadence from the AI charter and maintain a three-part task file in `docs/tasks/` while a task is in flight.

## Configuration & Secrets
- Copy `.env.example` → `.env` at the repo root. Provide `MONGO_URI`, `GEMINI_API_KEY`, `TAVILY_API_KEY`, `OPENROUTER_API_KEY`, `DEEPSEEK_API_KEY` (if catalog entries require it), and set `NEXUS_ENV` (`development` by default).
- Backend honors `HOST`, `PORT`, and `ALLOWED_ORIGINS` for deployment-time overrides (`nexus/main.py`).
- Frontend expects `aura/.env` with `VITE_WS_URL` (defaults to `ws://localhost:8000/api/v1/ws`).
- System defaults (LLM catalog, editable fields, prompts) live in Mongo's `configurations` collection; see `config.example.yml` before altering runtime config.
- Never commit secrets or production configuration overrides.

## Testing Expectations
- TDD is mandatory. Write the failing test first, implement the minimal fix, then refactor.
- Backend: run `pytest`, or scope with `pytest tests/nexus/unit`, `pytest tests/nexus/integration`, etc. Prefer asserting bus publications and service outputs over internal state. Use `pytest.mark.asyncio` for async routines.
- Frontend: run `pnpm test` (watch) or `pnpm test:run` (CI). Tests use Vitest + Testing Library; keep fixtures colocated with the feature. Limit snapshots to stable UI fragments.
- Maintain reusable fixtures in `tests/conftest.py` and shared helpers per feature.
- All suites must pass before delivering work; never skip tests or use `--no-verify`.

## Coding Style & Quality
- Python: format with `ruff format` and lint with `ruff check`. Type check with `mypy nexus/`.
- TypeScript/React: rely on Prettier defaults and the ESLint config in `aura/eslint.config.js`.
- Enforce grayscale-only styling, motion timing, and interaction rules from `docs/rules/frontend_design_principles.md`.
- Keep modules ≤ 600 lines as mandated in the AI charter; refactor when approaching limits.
- Provide explicit typing for services, hooks, and complex data structures.

## Tooling & Integration Contracts
- When introducing new WebSocket events, update `nexus/core/topics.py`, the orchestrator publisher, `aura/src/services/websocket/protocol.ts`, and the associated Zustand store (`aura/src/features/chat/store/auraStore.ts`).
- New tools require a synchronous function and metadata constant in `nexus/tools/definition/*.py`; discovery is automatic on startup.
- Reference `scripts/shell/run.sh` for local bootstrapping and ensure new tooling respects existing ANSI logging/output conventions.

## Process & Collaboration
- Task files must be three-part (Task Brief → Implementation Plan → Completion Report) and created in `docs/tasks/YY-MMDD_name.md`.
- Respect the retry limit in the AI charter: stop after three failed attempts and escalate with the required report.
- Interrogate user requests against security, architecture, and process priorities. When guidance conflicts, cite the charter and propose safer alternatives.
- Use Conventional Commits (`feat:`, `fix:`, `refactor(ui):`), English only, no AI signatures. Explain the "why" within commit bodies when not obvious.
- Surface risks, technical debt, and smells proactively; request prioritization before refactoring unrelated areas.
- Completion reports (Part 3) must be technical blog-style: document real debugging processes including failed attempts, technical decisions, and reflections.

## Security & Operations
- Protect WebSocket endpoints during demos (use password-protected tunnels such as `ngrok`).
- Verify Mongo indexes after migrations and avoid seeding production data (`scripts/seed_config.py` is for disposable environments only).
- Logging defaults to INFO (`nexus/main.py`); adjust via config when necessary, not through ad-hoc code changes.

## Reference Materials
- `AGENTS.md` – mirrors this policy for other agents.
- `docs/developer_guides/01_SETUP_AND_RUN.md`, `02_CONTRIBUTING_GUIDE.md`, `03_TESTING_STRATEGY.md`, `04_AI_COLLABORATION_CHARTER.md` – canonical process documentation.
- `docs/rules/frontend_design_principles.md` – non-negotiable UI/UX philosophy.
- `docs/tasks/` – Three-part task files for single-conversation work. See `tasks/README.md` for format specifications.
- `docs/strategic_plans/` – Strategic planning documents for large-scale initiatives.
- `docs/learn/` – lessons learned repository for prior incidents and fixes.
- `docs/knowledge_base/` & `docs/api_reference/` – architectural and protocol references.
- `docs/Future_Roadmap.md` – upcoming initiatives to consider during planning.
