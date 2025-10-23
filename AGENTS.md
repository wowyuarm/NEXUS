# Repository Guidelines

These rules apply to every AI assistant working on the YX NEXUS project. Treat them as non-negotiable.

## Before You Start
- `docs/developer_guides/04_AI_COLLABORATION_CHARTER.md` – mandatory planning, retry, and communication protocol.
- `tests/README.md` – TDD workflow and testing pyramid expectations.
- `docs/rules/frontend_design_principles.md` – required for any UI, motion, or styling work.
- `docs/developer_guides/02_CONTRIBUTING_GUIDE.md` and `docs/developer_guides/03_TESTING_STRATEGY.md` – workflow and test patterns.
- `docs/tasks/` – Three-part task files (Task Brief → Implementation Plan → Completion Report) for single-conversation work. See `tasks/README.md` for detailed format specifications.
- `docs/strategic_plans/` – Strategic planning documents for large-scale initiatives requiring multiple conversations or exceeding context limits.
- `docs/knowledge_base/` and `docs/api_reference/` – architectural, protocol, and reference material to cite during planning.
- `docs/learn/` – past incident reports and lessons; scan for similar issues when debugging.
- `docs/Future_Roadmap.md` – upcoming initiatives that may affect scope or design decisions.
- For unfamiliar domains, inspect at least three related implementations or tests before writing new code. Reference the material you consult in task files or status updates.

## Project Structure & Module Organization
- **Backend (NEXUS)**: `nexus/core/`, `nexus/services/`, `nexus/interfaces/`, `nexus/tools/definition/`, `nexus/prompts/`
- **Frontend (AURA)**: Feature-first layout under `aura/src/` (`app/`, `components/`, `features/`, `hooks/`, `services/`, `stores/`, `lib/`, `test/setup.ts`)
- **Testing**: Backend tests in `tests/nexus/{unit,integration,e2e}`, frontend Vitest suites colocated in `__tests__/` folders.
- Helper tooling: `scripts/shell/run.sh`, `docker-compose.yml`.

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
1. **Exploration Phase (Read-Only)** – Read foundational docs, scan related code (≥3 files), identify dependencies. No modifications during this phase.
2. **Task File Creation** – Create a three-part task file in `docs/tasks/YY-MMDD_name.md`:
   - **CRITICAL**: Before creating any task file, MUST read `docs/tasks/README.md` to understand the required three-part format and guidelines.
   - **Part 1: Task Brief** – Background, objectives, deliverables, risk assessment, dependencies, references, acceptance criteria.
   - **Part 2: Implementation Plan** – Architecture overview, Phase 1/2/3... (decomposed by technical dependencies), detailed design with function signatures, complete test case lists, acceptance criteria.
   - **Part 3: Completion Report** (added after execution) – Technical blog-style summary with implementation details, debugging processes, test verification, reflections.
3. **Context Gathering** – Pull architectural/protocol knowledge from `docs/knowledge_base/` and `docs/api_reference/`.
   - **Best Practice**: Always read README files in relevant directories before creating or modifying documentation.
4. **Risk & History** – Search `docs/learn/` for similar incidents, capturing lessons in your task file.
5. **Future Alignment** – Ensure changes respect items in `docs/Future_Roadmap.md`.
6. **Wait for Approval** – User reviews and approves the task file before execution begins.
7. **Execute Implementation** – Follow TDD workflow (RED → GREEN → REFACTOR), commit frequently.
8. **Append Completion Report** – Add Part 3 to the same task file with technical blog-style documentation.
9. Cite every consulted document in your task file and completion report.

## Build, Test, and Development Commands
- Backend: `python -m venv .venv`, `source .venv/bin/activate`, `pip install -r requirements.txt`, `python -m nexus.main`
- Frontend: `cd aura && pnpm install`, `pnpm dev`, `pnpm build`, `pnpm lint`, `pnpm test`, `pnpm test:run`, `pnpm test:coverage`
- Full stack: `scripts/shell/run.sh` (local) or `docker-compose up --build`

## Coding Style & Naming Conventions
- Python: `black` (line length 88), `flake8`, snake_case modules, CapWords classes, `_async` suffix where helpful, Google-style docstrings, explicit typing.
- TypeScript/React: Prettier + ESLint, `PascalCase.tsx` for components, `useCamelCase.ts` hooks, camelCase utilities, Tailwind grayscale tokens only.

## Testing Guidelines
- Follow TDD (RED → GREEN → REFACTOR).
- Backend: emphasize service-level integration tests asserting bus publications; use `pytest.mark.asyncio` for async behavior.
- Frontend: Vitest + Testing Library, colocated `__tests__/`, snapshot only stable UI fragments.
- Run relevant suites (`pytest`, `pnpm test:run`) and record commands in hand-offs.

## Commit & Pull Request Guidelines
- Conventional Commits in English (e.g., `feat: add config hot reload`).
- Every commit must build/run with associated tests.
- Pull requests require summary, risks, and explicit test plan.

## Security & Configuration Tips
- Duplicate `.env.example` → `.env`; supply `MONGO_URI`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `TAVILY_API_KEY`, `DEEPSEEK_API_KEY`, `NEXUS_ENV`.
- Respect `config.example.yml` schema when adjusting runtime behavior.
- Protect WebSocket endpoints with authenticated tunnels during demos; never seed production data.

## Frontend Design Principles
Always follow `docs/rules/frontend_design_principles.md` for motion, rhythm, and grayscale styling.

## Reference Materials
- `docs/developer_guides/01_SETUP_AND_RUN.md`
- `docs/developer_guides/04_AI_COLLABORATION_CHARTER.md`
- `docs/tasks/` – Single-conversation task files
- `docs/strategic_plans/` – Multi-conversation strategic initiatives
- `docs/learn/` – Postmortems and lessons learned
- `docs/knowledge_base/` – Architecture and technical references
- `docs/api_reference/` – API specifications
- `docs/Future_Roadmap.md`
