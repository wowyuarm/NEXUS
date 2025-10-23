# Documentation Operating Guide

The `docs/` directory is the knowledge nervous system for YX NEXUS. Every AI contributor must use it to plan work, understand architecture, avoid past pitfalls, and surface future risks. This README explains how the documentation ecosystem fits together and how to keep it alive.

## Directory Map & Usage
- **`developer_guides/`** – Process manuals (setup, contributing, testing, AI collaboration). Read before you touch code; they define the baseline workflow.
- **`rules/`** – Non-negotiable design and behavior principles (e.g., `frontend_design_principles.md`). Apply these anytime you work on matching areas.
- **`tasks/`** – Three-part task files (Task Brief → Implementation Plan → Completion Report) for single-conversation work. Each file is a complete lifecycle document from planning to delivery. See `tasks/README.md` for detailed format specifications.
- **`strategic_plans/`** – Strategic planning documents for large-scale initiatives requiring multiple conversations or exceeding context limits. Each strategic plan decomposes into multiple task files.
- **`knowledge_base/`** – Conceptual and architectural references (vision, backend/frontend architecture, technical deep dives). Use these to understand "why" and "how" before proposing changes.
- **`api_reference/`** – Precise contracts for WebSocket, REST, configuration schemas, etc. Consult when altering protocols or building integrations.
- **`learn/`** – Postmortems and lessons learned. Review relevant entries before debugging; add new entries after resolving incidents so future agents inherit the fix.
- **`future/Future_Roadmap.md`** – Upcoming initiatives and deferred ideas. Check for conflicts or dependencies during planning.

## Workflow Integration

Choose the appropriate workflow based on task complexity:

### Simple Changes (Direct Commit)
**Use for:** Documentation updates, minor config changes, simple fixes (≤3 files, no business logic).

1. Make changes directly on current branch (typically `main`)
2. Test and commit with clear message

**No branch creation, no task file required.**

---

### Medium Tasks (Branch + Task File)
**Use for:** Feature additions, bug fixes, refactoring, or any work involving ≤15 files.

1. **Exploration Phase (Read-Only)**: Read foundational docs, scan related code (≥3 files), identify dependencies and risks. No modifications during this phase.
2. **Branch Creation**: Create a dedicated feature branch following `[type]/[descriptive-name]` pattern.
3. **Task File Creation**: Create a three-part task file in `tasks/YY-MMDD_name.md`:
   - **Part 1: Task Brief** – Background, objectives, deliverables, pragmatic risk assessment, real technical dependencies, references, acceptance criteria.
   - **Part 2: Implementation Plan** – Architecture overview, phase-based decomposition (by technical dependencies), detailed design with function signatures, complete test case lists.
   - **Part 3: Completion Report** – (Added after execution) Technical blog-style documentation with implementation details, debugging processes, reflections.
4. **Wait for Approval**: Present task file to user for review and approval.
5. **Execution**: Follow TDD workflow (RED → GREEN → REFACTOR), commit frequently.
6. **Append Completion Report**: Add Part 3 to the same task file with real debugging stories, technical decisions, test verification, and reflections.

---

### Large Initiatives (Branch + Strategic Plan)
**Use for:** Multi-conversation work, tasks exceeding context limits (>15 files).

1. **Exploration & Research**: Deep dive into architecture, dependencies, and scope.
2. **Branch Creation**: Create feature branch for the initiative.
3. **Strategic Plan Creation**: Create plan in `strategic_plans/` that decomposes into multiple sub-tasks, each with its own task file in `tasks/`.
4. **Wait for Approval**: Present strategic plan to user.
5. **Execute Sub-Tasks**: Follow Medium Tasks workflow for each sub-task.

## Keeping Docs Alive (AI Responsibilities)
- **Exploration**: During contextual scans, note mismatches between docs and code. Log gaps in your task file; propose doc updates alongside code changes.
- **Iteration**: If a doc lacks clarity, add front-matter (summary, owners, updated date) or cross-links to related material. Prefer augmenting over duplicating content.
- **Validation**: After implementing changes, ensure referenced docs still reflect reality. Update specs, diagrams, or examples when behavior shifts.
- **Completion Reports**: Use Part 3 of task files to document real challenges, debugging processes, and lessons learned – creating a knowledge base for future developers.
- **Escalation**: When systemic reorganizations are needed, outline a proposal in your task file and confirm before restructuring.

## Continuous Improvement Checklist
- [ ] Documentation cited in task file (Part 1 and Part 3)
- [ ] New lessons recorded in `docs/learn/` where applicable
- [ ] Completion report (Part 3) added with technical blog-level detail
- [ ] Cross references added/adjusted in `knowledge_base/` and `api_reference`
- [ ] Roadmap reviewed and updated if scope changes impact future work

## Suggested Future Enhancements
- Add front-matter (summary, tags, owners) to major docs for faster scanning.
- Consolidate overlapping content and maintain a master index highlighting inter-document links.
- Periodically audit `learn/` entries and promote stable patterns back into `knowledge_base` or process guides.
- Evaluate merging `api_reference/` into `knowledge_base/technical_references/` when structure is ready.

Treat documentation as living infrastructure: every change should either consume relevant knowledge or produce new insights for the next contributor.
