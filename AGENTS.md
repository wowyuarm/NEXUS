# Repository Guidelines

These rules apply to every AI assistant working on the YX NEXUS project. Treat them as non-negotiable.

## Before You Start
- Read the foundational docs for each task:
  - `docs/developer_guides/04_AI_COLLABORATION_CHARTER.md`
  - `tests/README.md`
  - `docs/rules/frontend_design_principles.md` for UI/UX, motion, or styling work
  - `docs/developer_guides/02_CONTRIBUTING_GUIDE.md` & `03_TESTING_STRATEGY.md`
  - Relevant briefs in `docs/tasks/`
  - Supporting references in `docs/knowledge_base/` and `docs/api_reference/`
  - Related postmortems in `docs/learn/`
  - `docs/Future_Roadmap.md` for upcoming initiatives
- Perform a contextual scan of existing code/tests (minimum three related files) before modifying anything.
- Reference the materials you relied on inside your implementation plan and status updates.

## Project Structure & Module Organization
- **Backend (NEXUS)**: `nexus/core/`, `nexus/services/`, `nexus/interfaces/`, `nexus/tools/definition/`, `nexus/prompts/`
- **Frontend (AURA)**: Feature-first layout under `aura/src/` (`app/`, `components/`, `features/`, `hooks/`, `services/`, `stores/`, `lib/`, `test/setup.ts`)
- **Testing**: Backend tests in `tests/nexus/{unit,integration,e2e}`, frontend Vitest suites colocated in `__tests__/` folders.
- Helper tooling: `scripts/shell/run.sh`, `docker-compose.yml`.

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
1. **Task Intake** – Read the matching `docs/tasks/*.md` file; create or update `IMPLEMENTATION_PLAN.md` (see AI charter) referencing that brief.
2. **Context Gathering** – Pull architectural/protocol knowledge from `docs/knowledge_base/` and `docs/api_reference/`.
3. **Risk & History** – Search `docs/learn/` for similar incidents, capturing lessons in your plan.
4. **Future Alignment** – Ensure changes respect items in `docs/Future_Roadmap.md`.
5. Cite every consulted document in your plan or final report.

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
- `docs/tasks/`
- `docs/learn/`
- `docs/knowledge_base/`
- `docs/api_reference/`
- `docs/Future_Roadmap.md`
