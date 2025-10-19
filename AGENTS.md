# Repository Guidelines

## Project Structure & Module Organization
NEXUS backend code lives in `nexus/`, structured by domain: `core/` for bus infrastructure, `services/` for orchestrators and adapters, `commands/` for CLI routines, and `prompts/` for AI system prompt templates. Real-time interfaces sit under `nexus/interfaces/` (`rest` API and WebSocket bridge). The AURA frontend in `aura/` follows a feature-first layout inside `src/`, and shared UI primitives stay in `src/components`. Tests are mirrored in `tests/unit`, `tests/integration`, while reference material lives in `docs/`.

## Build, Test, and Development Commands
Use a virtualenv at root dir with `source .venv/bin/activate` and start the backend with `python -m nexus.main`; `scripts/shell/run.sh` will bootstrap both services if you prefer one command. Run backend checks with `pytest` (all suites) or target scopes such as `pytest tests/integration`. Frontend tasks live under `aura/`: `pnpm dev` runs Vite locally, `pnpm build` emits production assets, and `pnpm test` executes Vitest suites.

## Coding Style & Naming Conventions
Format Python with `black` (line length 88) and lint with `flake8`; modules and packages stay lowercase with underscores, while classes use `CapWords` and async coroutines end in `_async` where it clarifies intent. Docstrings follow Google style and every service exposes explicit type hints. In AURA, run `pnpm lint` (ESLint) and keep Prettier enabled in your editor; components use `PascalCase.tsx`, hooks use `useCamelCase.ts`, and Tailwind utilities favor neutral palette tokens from `globals.css`.

## Testing Guidelines
Unit tests belong beside the code under `tests/unit/nexus`, integration tests focus on service contracts with a mocked `NexusBus`, and E2E tests simulate the full websocket flow. Name tests after behavior, e.g., `test_orchestrator_handles_identity_gate`, and keep fixtures in `tests/conftest.py`. Write the failing test first, assert publications instead of implementation details, and prefer `pytest.mark.asyncio` for async workflows. For the frontend, rely on `vitest` + Testing Library, and snapshot only stable UI fragments.

## Commit & Pull Request Guidelines
Follow Conventional Commits (`feat:`, `fix:`, `refactor(ui):`) so release notes stay predictable. Group logically related changes per commit and reference issue IDs in the subject or body when applicable. Pull requests need a short summary, an itemized test plan (include console commands you ran), and screenshots or recordings for UI-visible changes. Confirm `pytest` and `pnpm test` both pass before requesting review.

## Security & Configuration Tips
Copy `.env.example` to `.env` to provide `MONGO_URI`, `GEMINI_API_KEY`, and `TAVILY_API_KEY`; never commit secrets. Local config documents live in `config.example.yml`—derive new variants there rather than editing production values in place. When seeding data, run `python scripts/seed_config.py` against disposable databases only, and verify Mongo indexes after migrations. Keep WebSocket endpoints private when demoing by tunneling through vetted tools such as `ngrok` with password protection.

## Frontend Design Principles

When need to develop or optimize frontend components and specific UI/UX effects, you must follow the frontend design principles; see `docs/rules/frontend_design_principles.md`, which is very important.

