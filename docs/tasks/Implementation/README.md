# Implementation Plans

Use this space to store long-form `IMPLEMENTATION_PLAN.md` documents for multi-phase initiatives. Plans here should track collaborative execution across releases.

## When to Create an Implementation Plan
- A task brief spans multiple milestones or squads.
- Work needs 4+ stages or external dependencies.
- The plan must persist beyond a single PR or pairing session.

## Required Sections
```
## Stage 1: <Stage Name>
**Goal**: <Specific, testable outcome>
**Success Criteria**: <Measurable signals>
**Tests**: <Planned suites/cases>
**References**: <Docs, briefs, learnings>
**Status**: Not Started | In Progress | Complete
```
Repeat for each stage. Link back to the originating `docs/tasks/*.md` brief and cite supporting references from `docs/knowledge_base/`, `docs/api_reference/`, and `docs/learn/`.

## Maintenance Guidelines
- Update status after each stage completes; include relevant PR or commit IDs.
- Archive the plan (move to `/archive` or embed in the originating brief) once the initiative ships.
- Keep only active plans in this directory; retire old ones to avoid noise.

_Placeholders are acceptable while scoping, but promote them to full plans before coding begins._
