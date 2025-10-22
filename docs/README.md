# Documentation Operating Guide

The `docs/` directory is the knowledge nervous system for YX NEXUS. Every AI contributor must use it to plan work, understand architecture, avoid past pitfalls, and surface future risks. This README explains how the documentation ecosystem fits together and how to keep it alive.

## Directory Map & Usage
- **`developer_guides/`** – Process manuals (setup, contributing, testing, AI collaboration). Read before you touch code; they define the baseline workflow.
- **`rules/`** – Non-negotiable design and behavior principles (e.g., `frontend_design_principles.md`). Apply these anytime you work on matching areas.
- **`tasks/`** – Mission briefs and architecture plans for major subsystems. Start here when scoping features/refactors; cite them in `IMPLEMENTATION_PLAN.md`. Long-running plans live in `tasks/Implementation/`.
- **`knowledge_base/`** – Conceptual and architectural references (vision, backend/frontend architecture, technical deep dives). Use these to understand “why” and “how” before proposing changes.
- **`api_reference/`** – Precise contracts for WebSocket, REST, configuration schemas, etc. Consult when altering protocols or building integrations.
- **`learn/`** – Postmortems and lessons learned. Review relevant entries before debugging; add new entries after resolving incidents so future agents inherit the fix.
- **`Future_Roadmap.md`** – Upcoming initiatives and deferred ideas. Check for conflicts or dependencies during planning.

## Workflow Integration
1. **Task Kickoff**: Read the relevant `docs/tasks/*.md`, pull supporting context from `knowledge_base/` and `api_reference/`, and search `learn/` for similar issues.
2. **Planning**: Draft or update `IMPLEMENTATION_PLAN.md`, citing every document consulted (path + key insight). Store long-form plans in `tasks/Implementation/` if work spans milestones.
3. **Execution**: Follow process checklists from `developer_guides/`, apply design rules, and stick to the tests spelled out in `03_TESTING_STRATEGY.md`.
4. **Delivery**: When handing off, link to the docs that informed your work and note any new knowledge captured in `learn/` or updates needed elsewhere.

## Keeping Docs Alive (AI Responsibilities)
- **Exploration**: During contextual scans, note mismatches between docs and code. Log gaps in your plan; propose doc updates alongside code changes.
- **Iteration**: If a doc lacks clarity, add front-matter (summary, owners, updated date) or cross-links to related material. Prefer augmenting over duplicating content.
- **Validation**: After implementing changes, ensure referenced docs still reflect reality. Update specs, diagrams, or examples when behavior shifts.
- **Escalation**: When systemic reorganizations are needed (e.g., moving `api_reference` under `knowledge_base`), outline a proposal in your plan and confirm before restructuring.

## Continuous Improvement Checklist
- [ ] Documentation cited in `IMPLEMENTATION_PLAN.md` and final summary
- [ ] New lessons recorded in `docs/learn/` where applicable
- [ ] Task briefs updated with outcomes, risks, or follow-ups
- [ ] Cross references added/adjusted in `knowledge_base/` and `api_reference`
- [ ] Roadmap reviewed and updated if scope changes impact future work

## Suggested Future Enhancements
- Add front-matter (summary, tags, owners) to major docs for faster scanning.
- Consolidate overlapping content and maintain a master index highlighting inter-document links.
- Periodically audit `learn/` entries and promote stable patterns back into `knowledge_base` or process guides.
- Evaluate merging `api_reference/` into `knowledge_base/technical_references/` when structure is ready.

Treat documentation as living infrastructure: every change should either consume relevant knowledge or produce new insights for the next contributor.
