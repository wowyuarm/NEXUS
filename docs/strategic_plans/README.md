# Strategic Plans

This directory contains **strategic planning documents** for large-scale initiatives that cannot be completed in a single AI conversation due to context limitations or cross-cutting complexity.

---

## When to Create a Strategic Plan

Create a strategic plan document here if the task meets **at least two** of the following criteria:

1. **Context Limit Exceeded**: The task involves more than ~15 files or requires extensive code context that exceeds AI token limits.
2. **Multi-Conversation Requirement**: The task requires multiple separate AI conversations to complete (e.g., backend implementation → frontend implementation → integration).
3. **Cross-Cutting Changes**: The task spans multiple services, modules, or major architectural boundaries (e.g., backend + frontend + database migrations).
4. **Large-Scale Refactoring**: The task involves significant architectural changes or system-wide refactoring.

**Examples of strategic plan candidates:**
- Complete AURA 2.0 UI migration
- Multi-service authentication system overhaul
- Database schema migration affecting multiple services
- Major dependency upgrade across the entire codebase

**Not strategic plan candidates (use `docs/tasks/` instead):**
- Adding a new REST endpoint
- Implementing a single new feature
- Bug fixes, even if complex
- Refactoring a single module

---

## Strategic Plan Structure

A strategic plan document should contain:

### 1. Strategic Overview
- **Objective**: High-level goal of the initiative
- **Scope**: What is and isn't included
- **Success Criteria**: Measurable outcomes for the entire initiative

### 2. Architecture & Design
- System-level architecture decisions
- Key technical choices and rationale
- Integration points and dependencies

### 3. Task Decomposition
Break the initiative into independent sub-tasks, each documented as:

```markdown
### Task 1: [Descriptive Name]
**Task File**: `docs/tasks/YY-MMDD_name.md` (to be created)
**Dependencies**: None | Task 2, Task 3
**Status**: ⏳ Not Started | 🚧 In Progress | ✅ Complete
**Assignee**: [If applicable]
**Priority**: High | Medium | Low

**Brief Description**:
One paragraph describing what this sub-task accomplishes.
```

### 4. Implementation Roadmap
- Recommended execution order
- Critical path analysis
- Estimated complexity (per task)

### 5. Progress Tracking
Update this section as sub-tasks complete:

```markdown
## Progress Tracker

- [x] Task 1 - Complete (PR #123, 2025-01-15)
- [🚧] Task 2 - In Progress
- [ ] Task 3 - Not Started
- [ ] Task 4 - Blocked by Task 2
```

### 6. Lessons Learned (Post-Completion)
After all sub-tasks complete, document:
- What went well
- What could be improved
- Architectural insights gained
- Recommendations for future similar initiatives

---

## Workflow: Strategic Plan → Task Files

1. **Create Strategic Plan**: Author creates `docs/strategic_plans/initiative-name.md` with the structure above.
2. **Decompose into Tasks**: Break down into independent sub-tasks.
3. **Execute Sub-Tasks**: For each sub-task:
   - Create a new task file in `docs/tasks/YY-MMDD_name.md`
   - Follow the standard three-part task file workflow (Task Brief → Implementation Plan → Completion Report)
   - Link back to the strategic plan in the task file's references
4. **Update Progress**: Mark sub-tasks as complete in the strategic plan's progress tracker.
5. **Final Review**: Once all sub-tasks complete, add lessons learned to the strategic plan.

---

## Maintenance Guidelines

- **Active Plans Only**: Keep only active strategic plans in this directory root. Archive completed plans to `archives/` subdirectory.
- **Regular Updates**: Update progress tracker after each sub-task completes.
- **Link Traceability**: Ensure all sub-task files reference the parent strategic plan, and vice versa.
- **Deprecation**: If a strategic plan becomes obsolete, mark it as `[DEPRECATED]` in the title and explain why.

---

## Example Strategic Plans

**Good Examples:**
- `aura-v2-complete-migration.md` - Multi-phase UI framework upgrade spanning 10+ tasks
- `llm-provider-abstraction.md` - Backend + frontend changes to support dynamic LLM providers

**Bad Examples (should be in `docs/tasks/` instead):**
- `add-config-endpoint.md` - Single feature, single conversation scope
- `fix-websocket-bug.md` - Bug fix, even if complex

---

**For single-conversation tasks, always use `docs/tasks/` instead of strategic plans.**
