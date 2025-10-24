# Repository Guidelines for Windsurf/Cascade

Mandatory guidelines for Windsurf/Cascade AI working on YX NEXUS. These rules complement `AGENTS.md` with Windsurf-specific capabilities.

## Before You Start

**MANDATORY READING:**
- `docs/developer_guides/04_AI_COLLABORATION_CHARTER.md` – planning and retry protocol
- `tests/README.md` – TDD workflow
- `docs/rules/frontend_design_principles.md` – UI/UX requirements
- `docs/tasks/README.md` – Three-part task file format
- `docs/knowledge_base/`, `docs/api_reference/`, `docs/learn/`, `docs/future/Future_Roadmap.md`
- Inspect ≥3 related implementations before writing new code

## Architecture
- **Backend (NEXUS)** – FastAPI + event bus + services (Config, Database, Persistence, Identity, Command, Context, ToolExecutor, LLM, Orchestrator)
- **Frontend (AURA)** – React 19 + TypeScript + Vite + Zustand + Tailwind (grayscale-only) + Framer Motion
- **Tools** – Auto-discovered from `nexus/tools/definition/`

## Windsurf-Specific Tool Usage (CRITICAL)

### 1. Fast Context Agent - YOUR PRIMARY TOOL

**MANDATORY:** For unfamiliar code, use `find_code_context` FIRST before reading files.

**Usage:**
```python
find_code_context(
    search_folder_absolute_uri="/home/wowyuarm/projects/NEXUS/nexus/services",
    search_term="How configuration is loaded from database"
)
# Then read specific files from results
```

**When:**
- New features/debugging/understanding existing code
- Finding logic locations, tests, dependencies
- Before architectural changes

**Why:** Semantic search > text matching. Discovers relationships grep misses.

### 2. Systematic Verification

**MANDATORY:** When changing names/paths/references, verify ENTIRE codebase.

```python
grep_search(
    SearchPath="/home/wowyuarm/projects/NEXUS",
    Query="pattern",
    Includes=["*.py", "*.ts", "*.md"]
)
```

**Rule:** Find one issue → assume it exists elsewhere → search systematically.

### 3. Batch Editing

**MANDATORY:** Multiple changes in one file → use `multi_edit` (atomic operation).

```python
multi_edit(
    file_path="/path/to/file",
    edits=[
        {"old_string": "old1", "new_string": "new1"},
        {"old_string": "old2", "new_string": "new2"}
    ]
)
```

### 4. Command Execution

**Safe auto-run:** `git status`, `grep`, `ls`, `wc`, `pytest --collect-only`  
**Need approval:** `git commit`, `pytest`, `pip install`, writes

## Git & Branch Management

**Simple Changes (≤3 files, docs only):** Direct commit to `main`  
**Medium/Large Tasks:** Feature branch required

**Branch Protocol:**
1. Explore first (Fast Context + docs) – NO branch creation yet
2. `git branch --show-current`
3. `git checkout -b [type]/[name]` (feat/fix/refactor/docs/test, kebab-case)
4. Verify: `git branch --show-current`

## Workflow

### Simple (≤3 files, docs)
1. Fast Context/grep to verify scope
2. Make changes, verify comprehensively
3. Commit (Conventional Commits)

### Medium (Branch + Task File, ≤15 files)
1. **Exploration (Read-Only):** Fast Context → read ≥3 files → check docs/learn/ → check Future_Roadmap.md
2. **Branch:** Create feature branch
3. **Task File:** Read `docs/tasks/README.md` → create `YY-MMDD_name.md` (3 parts: Brief, Plan, Report)
   - **CRITICAL:** Task files often exceed 8000 token write limit
   - **Solution:** Use multi-step approach:
     - Step 1: `write_to_file` with Part 1 (Task Brief)
     - Step 2: `edit` to append Part 2 (Implementation Plan)
     - Step 3: Leave Part 3 empty until after implementation
   - Never try to write entire task file in one operation
4. **Approval:** Wait for user OK
5. **TDD:** RED → GREEN → REFACTOR
6. **Implementation:** Make changes, run tests, verify functionality
7. **Completion Report (MANDATORY BEFORE COMMIT):** Add Part 3 with debugging details, failures, reflections
8. **Self-Review:** Audit your changes - cleanup code, verify architecture alignment, check test coverage
9. **Wait for User:** Present completion status. **NEVER commit unless user explicitly requests it**

### Large (>15 files)
Strategic plan in `docs/strategic_plans/` → decompose to medium tasks

## Key Requirements

**Configuration:**
- `.env.example` → `.env` (MONGO_URI, API keys, NEXUS_ENV)
- Frontend: `VITE_AURA_WS_URL`, `VITE_AURA_API_URL`
- Never commit secrets

**Testing:**
- TDD mandatory: failing test → minimal code → refactor
- Backend: `source .venv/bin/activate && pytest tests/nexus/unit`
- Frontend: `pnpm test:run`
- Never skip tests or use `--no-verify`

**Process:**
- Task files: `docs/tasks/YY-MMDD_name.md` (3 parts)
- Retry limit: 3 attempts → escalate
- Conventional Commits: `feat:`, `fix:`, `refactor(scope):`
- Document failures in completion reports

**Communication:**
- Terse, direct, results-first
- Structured reporting with ✅ markers
- Proactive problem-solving

**Windsurf Advantages:**
- ~200K token context → compare large files, understand complex architectures
- Multi-file pattern detection → codebase-wide refactoring
- Parallel tool execution → batch operations

## Critical Rules

**ALWAYS:**
1. ✅ Fast Context first for unfamiliar code
2. ✅ Verify across entire codebase (grep)
3. ✅ Read required docs before starting
4. ✅ Follow TDD (RED → GREEN → REFACTOR)
5. ✅ Match workflow to task complexity
6. ✅ Use multi_edit for batch changes
7. ✅ Run verification after changes
8. ✅ Commit frequently

**NEVER:**
1. ❌ Skip Fast Context for exploration
2. ❌ Fix one instance without searching all
3. ❌ Guess paths/names – verify
4. ❌ Skip "Before You Start" docs
5. ❌ Over-engineer simple fixes
6. ❌ Commit secrets
7. ❌ Skip tests or use `--no-verify`
8. ❌ Work on `main` for medium/large tasks

## Tool Decision Tree

```
Task?
  ├─ Explore? → find_code_context → read_file → grep
  ├─ Change?
  │   ├─ Single file? → multi_edit
  │   └─ Multiple? → edit
  ├─ Verify? → grep (codebase) → run_command
  └─ Feature? → find_code_context → docs → task file
```

## References
- `AGENTS.md`, `CLAUDE.md` – AI guidelines
- `docs/developer_guides/`, `docs/tasks/`, `docs/knowledge_base/`, `docs/api_reference/`
- `docs/learn/` – Past incidents
- `docs/future/Future_Roadmap.md`

---

**Your strengths:** Fast Context exploration, systematic codebase verification, 200K context window. Use them every session.