# Task Files

This directory contains **task files** for single-conversation implementation work. Each task file is a complete lifecycle document that captures the entire journey from planning to execution to reflection.

---

## What is a Task File?

A task file is a **three-part markdown document** that serves as:
1. **Planning Document** (Part 1 & 2): Created by AI and approved by user before execution
2. **Implementation Guide** (Part 2): Detailed technical blueprint with function signatures and test cases
3. **Knowledge Artifact** (Part 3): Technical blog-style completion report for future reference

**Key Principle**: One task = One file = Complete lifecycle (from conception to delivery)

---

## When to Create a Task File

Create a task file in this directory if your task can be completed in a **single AI conversation**. This includes:
- Adding new features or endpoints
- Bug fixes (even complex ones)
- Refactoring a single module or service
- Adding tests or documentation
- Any work involving ≤15 files that fits within AI context limits

**If your task requires multiple conversations or exceeds context limits**, create a strategic plan in `docs/strategic_plans/` instead, which will decompose into multiple task files.

---

## File Naming Convention

```
YY-MMDD_descriptive-name.md
```

- `YY`: Two-digit year (e.g., `25` for 2025)
- `MMDD`: Month and day (e.g., `1022` for October 22)
- `descriptive-name`: kebab-case description (3-5 words max)

**Examples:**
- `25-1022_light-theme.md`
- `25-1105_config-hot-reload.md`
- `25-1210_websocket-retry-logic.md`

---

## Three-Part Task File Structure

Every task file must follow this exact structure:

```markdown
# [TASK-ID]: [Task Title]

**Date:** YYYY-MM-DD
**Status:** 📝 Draft | ✅ Approved | 🚧 In Progress | ✔️ Complete

---

## Part 1: Task Brief

[Content described below]

---

## Part 2: Implementation Plan

[Content described below]

---

## Part 3: Completion Report

[Content described below - added after execution]
```

---

## Part 1: Task Brief (AI Creates, User Approves)

The task brief is created by AI during the exploration phase and must be approved by the user before implementation begins.

### Required Sections

#### 1. Background
**Purpose**: Explain why this task exists.

**Guidelines:**
- 2-4 sentences maximum
- Answer: What problem does this solve? What context is necessary?
- Reference related issues, features, or architectural decisions

**Example:**
```markdown
### Background

The AURA interface currently only supports dark mode. As the system enters production, users in bright environments need a well-designed light theme that maintains our grayscale aesthetic philosophy while ensuring comfortable readability.
```

#### 2. Objectives
**Purpose**: Define what success looks like.

**Guidelines:**
- List 1-3 clear, measurable objectives
- Use action verbs (implement, add, refactor, fix, etc.)
- Each objective must be verifiable

**Example:**
```markdown
### Objectives

1. Implement a complete light theme color palette following grayscale design principles
2. Add theme switching capability via `/theme` command
3. Ensure WCAG AA contrast compliance across all UI components
```

#### 3. Deliverables
**Purpose**: List concrete artifacts to be produced.

**Guidelines:**
- Be specific about files, endpoints, functions, or features
- Use checkboxes for tracking
- Include both code and documentation deliverables

**Example:**
```markdown
### Deliverables

- [ ] `aura/src/styles/globals.css` - Light theme CSS variables
- [ ] `aura/src/stores/themeStore.ts` - Theme state management
- [ ] `nexus/commands/definition/theme.py` - Theme command definition
- [ ] Unit tests for theme store and switching logic
- [ ] Updated `docs/rules/frontend_design_principles.md`
```

#### 4. Risk Assessment
**Purpose**: Identify concrete technical risks, not procedural formalities.

**CRITICAL GUIDELINES:**
- ✅ **DO**: Identify specific technical risks with pragmatic mitigation strategies
- ❌ **DON'T**: Include generic "best practices" or procedural risks

**What to include:**
- Performance bottlenecks
- Compatibility issues
- Data migration risks
- Integration challenges
- Known unknowns in dependencies

**What NOT to include:**
- "Need adequate testing" (this is always required)
- "Requires code review" (this is standard process)
- "Team coordination needed" (procedural, not technical)
- "May take longer than expected" (estimation uncertainty)

**Example (GOOD):**
```markdown
### Risk Assessment

- ⚠️ **Theme Flash on Load**: Users may see wrong theme briefly before localStorage loads
  - **Mitigation**: Inject inline script in HTML head to apply theme class before React hydration
  
- ⚠️ **Contrast Issues**: Some UI components may not meet WCAG AA in light mode
  - **Mitigation**: Run automated contrast checks, manually verify critical components

- ⚠️ **LocalStorage Sync**: Multiple tabs may have theme desync
  - **Mitigation**: Use storage event listener to sync across tabs
```

**Example (BAD - DON'T DO THIS):**
```markdown
### Risk Assessment

- ⚠️ Testing: Need comprehensive testing
- ⚠️ Code Review: Requires thorough review
- ⚠️ Timeline: May take longer than estimated
```

#### 5. Dependencies
**Purpose**: List real technical dependencies, not organizational ones.

**CRITICAL GUIDELINES:**
- ✅ **DO**: List concrete code, infrastructure, or external dependencies
- ❌ **DON'T**: Include organizational or procedural dependencies

**What to include:**
- Specific functions/modules that must exist first
- Database migrations or schema changes required
- External APIs or services needed
- Infrastructure setup (MongoDB indexes, etc.)
- Third-party library versions

**What NOT to include:**
- "Team approval needed"
- "Coordination with frontend team"
- "Stakeholder sign-off"
- "Documentation updates" (this is always required)

**Example (GOOD):**
```markdown
### Dependencies

**Code Dependencies:**
- `nexus/core/auth.py` must have `verify_signature()` function implemented
- `nexus/services/identity.py` must have `get_user_profile()` method

**Infrastructure:**
- MongoDB `users` collection must have index on `public_key` field

**External:**
- None
```

**Example (BAD - DON'T DO THIS):**
```markdown
### Dependencies

- Team approval
- Coordination with design team
- Stakeholder review
- Documentation updates
```

#### 6. References
**Purpose**: Link to relevant documentation.

**Guidelines:**
- List all `docs/` files consulted during exploration
- Include external documentation if relevant
- Use relative paths from repository root

**Example:**
```markdown
### References

- `docs/rules/frontend_design_principles.md`
- `docs/knowledge_base/01_VISION_AND_PHILOSOPHY.md`
- `docs/knowledge_base/03_AURA_ARCHITECTURE.md`
- `docs/developer_guides/03_TESTING_STRATEGY.md`
- `docs/learn/2025-09-11-render-vite-ws-nginx.md`
```

#### 7. Acceptance Criteria
**Purpose**: Define executable verification steps.

**Guidelines:**
- Use checkboxes for each criterion
- Make each criterion verifiable (runnable command or observable behavior)
- Include both automated tests and manual verification

**Example:**
```markdown
### Acceptance Criteria

- [ ] All unit tests pass: `pytest tests/nexus/unit -v`
- [ ] All frontend tests pass: `pnpm test:run`
- [ ] Theme switches without page reload
- [ ] No FOUC (Flash of Unstyled Content) on initial load
- [ ] WCAG AA contrast verified for all components
- [ ] `/theme` command works: `light`, `dark`, `toggle`
```

---

## Part 2: Implementation Plan (AI Creates, User Approves)

The implementation plan is created by AI alongside Part 1 and provides detailed technical design.

### Required Sections

#### 1. Architecture Overview (Optional)
If the task involves architectural decisions or complex interactions, provide a brief overview.

**Example:**
```markdown
### Architecture Overview

This task introduces a three-layer theme system:
1. **CSS Variables Layer**: Define color tokens in `globals.css`
2. **State Management Layer**: Zustand store manages theme state and persistence
3. **Command Layer**: `/theme` command integrates with existing command system
```

#### 2. Phase Decomposition
Break the task into phases based on **technical dependencies**, not arbitrary stages.

**Critical Guidelines:**
- Each phase must have clear technical boundaries
- Phases should be ordered by dependency (Phase 1 has no dependencies, Phase 2 depends on Phase 1, etc.)
- Number of phases is flexible (typically 2-5)
- Each phase must be independently testable

#### Phase Structure

Each phase must include:

**a. Goal**
One sentence describing what this phase accomplishes.

**b. Key Files**
List files being created or modified, with annotations:

```markdown
**New Files:**
- `nexus/core/auth.py` - Shared signature verification module

**Modified Files:**
- `nexus/services/identity.py` (add get_effective_profile method)
- `nexus/interfaces/rest.py` (add config endpoints)
```

**c. Detailed Design**
This is the most critical section. Provide:

1. **Function Signatures**: Exact method names, parameters, return types
2. **Implementation Logic**: Step-by-step pseudo-code or description
3. **Key Decisions**: Explain technical choices

**Example:**
```python
### Detailed Design

**Function: `verify_signature(payload: str, auth_data: Dict) -> Dict[str, Any]`**

Located in: `nexus/core/auth.py`

Parameters:
- `payload` (str): JSON string to verify
- `auth_data` (Dict): {"publicKey": "0x...", "signature": "0x..."}

Returns:
```python
{
    "status": "success", 
    "public_key": "0xABC..."
}
# OR
{
    "status": "error",
    "message": "Invalid signature"
}
```

Implementation Steps:
1. Extract `publicKey` and `signature` from `auth_data`
2. Compute keccak256 hash of payload
3. Recover public key from signature using eth_keys
4. Compare recovered key with provided public_key
5. Return success/error dict

**Key Decision**: Return dict instead of raising exception to allow flexible error handling by callers.
```

**d. Test Cases**
List **complete test function names** with descriptions.

**Example:**
```markdown
### Test Cases

**Test File:** `tests/nexus/unit/core/test_auth.py`

- `test_verify_signature_success()` - Verify valid signature returns success
- `test_verify_signature_missing_auth()` - Missing auth_data returns error
- `test_verify_signature_invalid_format()` - Malformed signature returns error
- `test_verify_signature_key_mismatch()` - Public key doesn't match signature
- `test_verify_signature_empty_payload()` - Empty payload handling
```

#### 3. Implementation Order (Optional)
If phases must be executed in a specific order, document it.

**Example:**
```markdown
### Implementation Order

1. **Day 1**: Phase 1 (Core Auth) + Phase 2 (Service Layer)
2. **Day 2**: Phase 3 (REST Endpoints)
3. **Day 3**: Phase 4 (Command Definitions) + Phase 5 (Integration Tests)
```

#### 4. Key Files Summary
Provide a complete list of files affected.

**Example:**
```markdown
### Key Files

**New Files (7):**
- `nexus/core/auth.py`
- `nexus/commands/definition/config.py`
- `nexus/commands/definition/prompt.py`
- `tests/nexus/unit/core/test_auth.py`
- ...

**Modified Files (4):**
- `nexus/services/identity.py`
- `nexus/interfaces/rest.py`
- `nexus/main.py`
- ...
```

#### 5. Acceptance Criteria (Repeat from Part 1)
Reiterate the acceptance criteria for easy reference.

---

## Part 3: Completion Report (AI Adds After Execution)

**THIS PART IS ADDED AFTER IMPLEMENTATION IS COMPLETE.**

The completion report is a **technical blog-style document** that records the actual implementation process, challenges, and reflections.

### Critical Guidelines

**Style Requirements:**
- Write like a developer writing a technical blog post
- Be honest about challenges and failures
- Document the journey, not just the destination
- Include code snippets for key implementations
- Show debugging processes, including failed attempts

**What Makes a Good Completion Report:**
- ✅ Shows real debugging processes ("I tried X, it failed because Y, then I tried Z")
- ✅ Explains technical decisions with rationale
- ✅ Includes specific error messages and solutions
- ✅ Provides copy-pasteable verification commands
- ✅ Reflects on what could be improved

**What Makes a Bad Completion Report:**
- ❌ Generic summary ("I implemented the feature")
- ❌ Just lists what was done without explaining how or why
- ❌ Hides failed attempts or challenges
- ❌ No reflection or lessons learned

### Required Sections

#### 1. Implementation Overview
Brief summary of what was delivered and any deviations from the plan.

**Example:**
```markdown
### Implementation Overview

Successfully implemented all three data management commands (`/config`, `/prompt`, `/history`) with full REST API backend support. The implementation followed the planned architecture with one deviation: added CORS headers to REST endpoints after discovering cross-origin issues during integration testing.

**Delivered:**
- 5 REST endpoints (GET/POST for config and prompts, GET for messages)
- 3 command definitions
- Shared authentication module
- 28 unit tests, 8 integration tests (all passing)
```

#### 2. Technical Implementation Details

For each major component, describe:
- What was implemented
- How it was implemented
- Key technical decisions and rationale

**Example:**
```markdown
### Technical Implementation Details

#### Shared Authentication Module (`nexus/core/auth.py`)

Extracted signature verification logic from `CommandService._verify_signature()` into a standalone function for reuse across REST and WebSocket endpoints.

**Key Decision: Return Dict vs Raise Exception**

Initial approach was to raise `SignatureError` on verification failure, but this created awkward try/catch blocks in callers. Switched to returning a status dict to allow callers to handle errors gracefully:

```python
result = verify_signature(payload, auth_data)
if result['status'] == 'error':
    raise HTTPException(403, detail=result['message'])
```

This pattern made error handling more explicit and easier to test.

**Implementation Challenge**: Ensuring JSON serialization consistency between frontend (signing) and backend (verification). Solution was to enforce `sort_keys=True` in both places.
```

#### 3. Problems Encountered & Solutions

**This IS THE MOST CRITICAL SECTION**. Document real problems with:
- Problem description
- Debugging process (including failed attempts)
- Final solution
- Lesson learned

**Example:**
```markdown
### Problems Encountered & Solutions

#### Problem 1: Signature Verification Always Returning 403

**Symptom:**
```bash
POST /api/v1/config
Response: 403 {"detail": "Invalid signature"}
```

**Debugging Process:**

**Attempt 1**: Suspected public key format mismatch (uppercase vs lowercase)
- Tried: `.lower()` on both keys before comparison
- Result: Still 403, not the issue

**Attempt 2**: Suspected signature encoding issue
- Tried: Different hex encoding/decoding methods
- Result: Still failing

**Attempt 3**: Printed the exact payload being signed and verified
- Discovery: Frontend was signing `{"overrides":{...},"auth":{...}}` but backend was signing `{"auth":{...},"overrides":{...}}`
- Root cause: JSON key ordering was different!

**Solution:**
Enforced `json.dumps(..., sort_keys=True)` in both frontend and backend to ensure consistent serialization order.

```python
# In verify_request_signature()
payload = json.dumps(request_body, separators=(',', ':'), sort_keys=True)
result = verify_signature(payload, auth_data)
```

**Lesson Learned:**
Cryptographic signature verification requires byte-perfect consistency. Always use deterministic serialization (`sort_keys=True`) for JSON signing.
```

#### 4. Test & Verification

Document all testing performed with actual commands and results.

**Example:**
```markdown
### Test & Verification

#### Unit Tests
```bash
pytest tests/nexus/unit/core/test_auth.py -v
# ====== test session starts ======
# test_auth.py::test_verify_signature_success PASSED
# test_auth.py::test_verify_signature_missing_auth PASSED
# test_auth.py::test_verify_signature_invalid_format PASSED
# test_auth.py::test_verify_signature_key_mismatch PASSED
# ====== 4 passed in 0.23s ======

pytest tests/nexus/unit/interfaces/test_rest.py -v
# ====== 12 passed in 1.45s ======
```

#### Integration Tests
```bash
pytest tests/nexus/integration/interfaces/test_rest_data_commands.py -v
# ====== 8 passed in 2.31s ======
```

#### Manual Verification
```bash
# Test GET /config
curl -H "Authorization: Bearer 0xABC..." \
  http://localhost:8000/api/v1/config
# ✅ Returns full config profile

# Test POST /config
curl -X POST \
  -H "Authorization: Bearer 0xABC..." \
  -H "Content-Type: application/json" \
  -d '{"overrides":{"temperature":0.9},"auth":{...}}' \
  http://localhost:8000/api/v1/config
# ✅ Returns {"status":"success"}
```
```

#### 5. Reflections & Improvements

Honest assessment of what went well and what could be better.

**Example:**
```markdown
### Reflections & Improvements

**What Went Well:**
- TDD discipline paid off: caught the JSON ordering bug immediately with tests
- Extraction of auth module created clean separation of concerns
- Integration tests gave confidence in cross-service interactions

**What Could Be Improved:**
- GET /messages endpoint has no pagination - will be slow with large message history
  - **Follow-up**: Add cursor-based pagination (linked to docs/future/Future_Roadmap.md)
- Error messages are English-only - frontend needs i18n
  - **Follow-up**: Not blocking for MVP, but should be standardized project-wide
- No rate limiting on POST endpoints
  - **Follow-up**: Implement rate limiting middleware

**Architectural Insights:**
- The bearer token + signature dual verification pattern works well for stateless REST APIs
- Returning error dicts instead of raising exceptions made testing significantly easier
```

#### 6. Related Links

Link to commits, PRs, and related issues.

**Example:**
```markdown
### Related Links

- **Pull Request**: #156
- **Commits**: 
  - `abc1234` - Add shared auth module
  - `def5678` - Implement config endpoints
  - `ghi9012` - Add integration tests
- **Related Issues**: #45 (API authentication)
- **Follow-up Tasks**: See `docs/future/Future_Roadmap.md` - "REST API pagination"
```

---

## AI Workflow Summary

1. **Exploration Phase (Read-Only)**
   - Read docs, scan code, identify dependencies
   - No modifications yet

2. **Create Branch**
   - `git checkout -b feat/task-name`

3. **Create Task File**
   - Write Part 1 (Task Brief)
   - Write Part 2 (Implementation Plan)
   - Leave Part 3 empty

4. **Present to User**
   - User reviews and approves or requests changes

5. **Execute Implementation**
   - Follow TDD workflow
   - Commit frequently

6. **Append Completion Report**
   - Add Part 3 with technical blog-style documentation
   - Include real debugging stories, reflections, and verification results

---

## Directory Structure

```
docs/tasks/
├── README.md (this file)
├── 25-1022_light-theme.md
├── 25-1105_config-hot-reload.md
├── archives/ (old format files, not maintained)
│   ├── aura_websocket.md
│   ├── command.md
│   └── ...
```

**archives/**: Contains task files from before the three-part format was established. These are kept for historical reference but do not follow the current format.

---

## For Large-Scale Work

If your task:
- Requires multiple AI conversations
- Involves >15 files
- Spans multiple services or major refactoring

**Create a strategic plan instead**: See `docs/strategic_plans/README.md`

---

**The goal of task files is to create a permanent knowledge base of implementation decisions, technical challenges, and solutions that future developers (human or AI) can learn from.**
