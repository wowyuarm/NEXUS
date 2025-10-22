# Project Task Briefs

This directory gathers scoped task blueprints, architecture plans, and historical initiatives for the NEXUS + AURA ecosystem. Treat every file here as a mission briefing: read it fully before starting a related feature, refactor, or investigation.

## How to Use This Directory
1. **Identify the Brief** – Match your assignment to the closest document (e.g., WebSocket work → `aura_websocket.md`, identity changes → `identity.md`). If nothing matches, draft a new brief before coding.
2. **Extract Constraints** – Capture assumptions, acceptance criteria, and open questions in your `IMPLEMENTATION_PLAN.md` and cite the brief (`docs/tasks/<name>.md`).
3. **Cross-Reference** – Follow links into `docs/knowledge_base/` and `docs/api_reference/` as noted inside each brief to gather deeper context.
4. **Report Back** – When delivering work, reference the brief in your summary so reviewers can align expectations.

## Directory Structure
- Root markdown files: high-level feature blueprints, system migrations, or recurring tasks (LLM tooling, identity, command panel, etc.).
- `Implementation/`: reserved for large, multi-stage project plans. Store long-form `IMPLEMENTATION_PLAN.md` files here once a brief graduates into an execution blueprint.

## Creating or Updating Briefs
- **Format**: Provide Overview → Goals → Scope → Risks → References → Acceptance Criteria.
- **Link Out**: Include pointers to relevant `knowledge_base`, `learn`, and `api_reference` entries.
- **Versioning**: Note owners and last updated date; append change logs for major revisions.
- **Retirement**: When a brief becomes obsolete, add a "Status" section marking it `Retired` and linking to the replacement document.

_Place additional planning artifacts under `Implementation/` when work spans multiple milestones or requires collaborative editing._
