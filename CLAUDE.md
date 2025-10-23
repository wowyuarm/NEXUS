# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. Treat every instruction as binding policy, not optional advice.

## Before You Start
- `docs/developer_guides/04_AI_COLLABORATION_CHARTER.md` – mandatory planning, retry, and communication protocol.
- `tests/README.md` – TDD workflow and testing pyramid expectations.
- `docs/rules/frontend_design_principles.md` – required for any UI, motion, or styling work.
- `docs/developer_guides/02_CONTRIBUTING_GUIDE.md` and `docs/developer_guides/03_TESTING_STRATEGY.md` – workflow and test patterns.
- `docs/tasks/` – mission briefs for major subsystems; read the relevant file (e.g., `tasks/context_md_xml.md`) before drafting `IMPLEMENTATION_PLAN.md`.
- `docs/knowledge_base/` and `docs/api_reference/` – architectural, protocol, and reference material to cite during planning.
- `docs/learn/` – past incident reports and lessons; scan for similar issues when debugging.
- `docs/Future_Roadmap.md` – upcoming initiatives that may affect scope or design decisions.
- For unfamiliar domains, inspect at least three related implementations or tests before writing new code. Reference the material you consult in plans or status updates.

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
**CRITICAL**: Before starting ANY task, you MUST create a dedicated feature branch. This project supports parallel development across multiple branches.

### Branch Creation Protocol
1. **Check Current Branch**: Run `git branch --show-current` to verify you're on `main` or another appropriate base branch.
2. **Pull Latest Changes**: Run `git pull origin main` to ensure you have the latest code.
3. **Create Feature Branch**: Use descriptive naming following these patterns:
   - `feat/[feature-name]` for new features (e.g., `feat/llm-dynamic-temperature`)
   - `fix/[bug-description]` for bug fixes (e.g., `fix/websocket-timeout`)
   - `refactor/[scope]` for refactoring (e.g., `refactor/ui-tool-card`)
   - `docs/[topic]` for documentation updates (e.g., `docs/api-reference`)
   - `test/[scope]` for test additions (e.g., `test/orchestrator-service`)
4. **Verify Branch Creation**: Run `git branch --show-current` to confirm you're on the new branch.

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
- **Task Intake**: Identify the relevant entry in `docs/tasks/` and read it fully. Use `docs/tasks/Implementation/` when long-form implementation plans exist; otherwise create your own `IMPLEMENTATION_PLAN.md` at the project root.
- **Context Gathering**: Pull architectural details from `docs/knowledge_base/` (e.g., `technical_references/command_system.md`) and protocol specifics from `docs/api_reference/`.
- **Risk & History Check**: Search `docs/learn/` for similar incidents to avoid repeating past issues; note applicable lessons in your plan.
- **Future Alignment**: Confirm your design does not conflict with items in `docs/Future_Roadmap.md`.
- Cite the documentation you used inside `IMPLEMENTATION_PLAN.md`, work logs, and final summaries so reviewers can trace reasoning.

## Development Workflow
1. **Branch Creation (MANDATORY FIRST STEP)**
   ```bash
   git branch --show-current        # verify current branch
   git pull origin main             # pull latest changes
   git checkout -b [type]/[name]    # create feature branch
   git branch --show-current        # confirm new branch
   ```
   **Never work directly on `main`** unless explicitly instructed.

2. **Backend**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python -m nexus.main
   ```
3. **Frontend**
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
4. Use `scripts/shell/run.sh` to launch both stacks locally once dependencies are installed. `docker-compose.yml` builds `nexus-backend` and `aura-frontend` on the `nexus-net` bridge network.
5. Always follow the RED → GREEN → REFACTOR cadence from the AI charter and maintain an `IMPLEMENTATION_PLAN.md` while a task is in flight.

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
- Python: format with `black` (line length 88) and lint with `flake8`.
- TypeScript/React: rely on Prettier defaults and the ESLint config in `aura/eslint.config.js`.
- Enforce grayscale-only styling, motion timing, and interaction rules from `docs/rules/frontend_design_principles.md`.
- Keep modules ≤ 600 lines as mandated in the AI charter; refactor when approaching limits.
- Provide explicit typing for services, hooks, and complex data structures.

## Tooling & Integration Contracts
- When introducing new WebSocket events, update `nexus/core/topics.py`, the orchestrator publisher, `aura/src/services/websocket/protocol.ts`, and the associated Zustand store (`aura/src/features/chat/store/auraStore.ts`).
- New tools require a synchronous function and metadata constant in `nexus/tools/definition/*.py`; discovery is automatic on startup.
- Reference `scripts/shell/run.sh` for local bootstrapping and ensure new tooling respects existing ANSI logging/output conventions.

## Process & Collaboration
- Plans must be multi-stage (`IMPLEMENTATION_PLAN.md`) and referenced in status updates. Archive or link plans when tasks finish.
- Respect the retry limit in the AI charter: stop after three failed attempts and escalate with the required report.
- Interrogate user requests against security, architecture, and process priorities. When guidance conflicts, cite the charter and propose safer alternatives.
- Use Conventional Commits (`feat:`, `fix:`, `refactor(ui):`), English only, no AI signatures. Explain the "why" within commit bodies when not obvious.
- Surface risks, technical debt, and smells proactively; request prioritization before refactoring unrelated areas.

## Security & Operations
- Protect WebSocket endpoints during demos (use password-protected tunnels such as `ngrok`).
- Verify Mongo indexes after migrations and avoid seeding production data (`scripts/seed_config.py` is for disposable environments only).
- Logging defaults to INFO (`nexus/main.py`); adjust via config when necessary, not through ad-hoc code changes.

## Reference Materials
- `AGENTS.md` – mirrors this policy for other agents.
- `docs/developer_guides/01_SETUP_AND_RUN.md`, `02_CONTRIBUTING_GUIDE.md`, `03_TESTING_STRATEGY.md`, `04_AI_COLLABORATION_CHARTER.md` – canonical process documentation.
- `docs/rules/frontend_design_principles.md` – non-negotiable UI/UX philosophy.
- `docs/tasks/` – mission briefs and architecture plans for major subsystems.
- `docs/learn/` – lessons learned repository for prior incidents and fixes.
- `docs/knowledge_base/` & `docs/api_reference/` – architectural and protocol references.
- `docs/Future_Roadmap.md` – upcoming initiatives to consider during planning.
