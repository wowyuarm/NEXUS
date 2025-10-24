# Task Review & Code Entropy Reduction Protocol

**Purpose**: This protocol is designed for a **fresh AI reviewer** to conduct comprehensive post-implementation analysis before final commit. This review happens when the task is complete, all three parts of the task file are written, but code is NOT yet committed.

**Context**: At this stage, the implementing AI has consumed significant context and may have reduced capability. A new AI with fresh perspective and full cognitive capacity performs the final quality gate.

---

## Reviewer Entry Point

You are entering a review session. Your role is **Code Reviewer & Architect Auditor**, not implementer.

**Your mission**: Ensure the completed work is functionally correct, structurally clean, architecturally aligned, and entropy-reduced.

---

## Phase 1: Context Acquisition (MANDATORY FIRST STEP)

Before any analysis, you MUST gather complete context:

### 1.1 Read Project Rules
Execute in this exact order:
1. `docs/developer_guides/04_AI_COLLABORATION_CHARTER.md`
2. `docs/developer_guides/02_CONTRIBUTING_GUIDE.md`
3. `docs/tasks/README.md`
4. `AGENTS.md` or `CLAUDE.md`
5. `docs/rules/frontend_design_principles.md` (if UI/frontend changes)

### 1.2 Understand What Changed
```bash
# Check current branch
git branch --show-current

# View all modified/added/deleted files
git status

# Review detailed changes
git diff

# If multiple commits on branch, review commit history
git log main..HEAD --oneline
```

### 1.3 Read the Task File
Locate and read the complete task file: `docs/tasks/YY-MMDD_name.md`

**Critical**: Verify all three parts exist:
- Part 1: Task Brief
- Part 2: Implementation Plan
- Part 3: Completion Report

---

## Phase 2: Task Report Validation

Audit the task file itself before auditing code.

### 2.1 Part 1 (Task Brief) Validation

**Check for Pragmatism:**
- [ ] **Risk Assessment**: Contains ONLY real technical risks (performance, compatibility, data migration, integration)?
  - ❌ **Reject if contains**: "Need adequate testing", "Requires code review", "Team coordination"
- [ ] **Dependencies**: Contains ONLY real technical dependencies (code modules, DB schemas, APIs, infrastructure)?
  - ❌ **Reject if contains**: "Team approval", "Stakeholder sign-off", "Documentation updates"

**Check for Completeness:**
- [ ] Background (2-4 sentences explaining why)
- [ ] Objectives (1-3 measurable goals)
- [ ] Deliverables (specific files/features with checkboxes)
- [ ] References (all consulted docs listed)
- [ ] Acceptance Criteria (executable verification steps)

### 2.2 Part 2 (Implementation Plan) Validation

**Check for Technical Depth:**
- [ ] **Phase Decomposition**: Phases are ordered by technical dependencies (not time)?
- [ ] **Detailed Design**: Contains actual function signatures with parameters and return types?
- [ ] **Test Cases**: Lists complete test function names (not just "write tests")?

**Example of GOOD design:**
```python
def verify_signature(payload: str, auth_data: Dict) -> Dict[str, Any]:
    """
    Returns: {"status": "success", "public_key": "0x..."}
         OR: {"status": "error", "message": "..."}
    """
```

**Example of BAD design:**
```
- Add signature verification function
- Implement authentication logic
- Write tests
```

### 2.3 Part 3 (Completion Report) Validation

**Check for Honesty & Depth:**
- [ ] **Implementation Overview**: Describes what was delivered and deviations from plan?
- [ ] **Technical Details**: Explains key decisions with rationale?
- [ ] **Problems & Solutions**: Shows REAL debugging process with failed attempts?
  - ❌ **Reject if**: Generic ("I implemented the feature") without showing journey
  - ✅ **Accept if**: Shows attempts ("Tried X, failed because Y, then tried Z")
- [ ] **Test Verification**: Includes copy-pasteable commands and actual output?
- [ ] **Reflections**: Honest assessment of what could be improved?

**Red Flags in Completion Reports:**
- No mention of any challenges or problems (every implementation has challenges)
- No failed attempts documented (learning requires failure)
- Generic statements without specifics
- Missing test verification commands

---

## Phase 3: Architecture & Code Quality Audit

Now audit the actual code changes.

### 3.1 Architectural Alignment

**Backend (NEXUS) - Service Boundaries:**
- [ ] New logic placed in appropriate service (`ConfigService`, `CommandService`, etc.)?
- [ ] Services communicate via `NexusBus` events, not direct calls?
- [ ] No business logic in interfaces (`rest.py`, `websocket.py`)?
- [ ] Tool definitions in `nexus/tools/definition/` follow discovery pattern?

**Frontend (AURA) - Feature Organization:**
- [ ] Components colocated under appropriate feature (`features/chat/`, `features/config/`)?
- [ ] State management uses Zustand stores?
- [ ] No business logic in components (delegated to hooks/services)?
- [ ] Tests colocated in `__tests__/` directories?

**Cross-Cutting Concerns:**
- [ ] WebSocket events defined in `nexus/core/topics.py`?
- [ ] Protocol changes reflected in both backend and frontend?
- [ ] Configuration changes documented in `config.example.yml`?

### 3.2 Code Entropy Reduction Checklist

Answer honestly. For every "Yes", immediate action required.

#### Part A: Cleanup & Removal

**1. Commented-Out Code:**
- [ ] **Yes/No**: Any commented-out logic, old functions, or debug statements (`console.log`, `print`)?
  - **Action**: Delete immediately. Git is the only code museum.

**2. Redundant Files & Imports:**
- [ ] **Yes/No**: Any files made obsolete by this change?
- [ ] **Yes/No**: Any unused import statements?
  - **Action**: Delete obsolete files. Use IDE's "Optimize Imports" to remove unused imports.

**3. Dead Variables & Functions:**
- [ ] **Yes/No**: Any declared but never used variables, parameters, or private functions?
  - **Action**: Remove all unused code entities.

**4. Orphaned Test Files:**
- [ ] **Yes/No**: Any test files testing code that no longer exists?
  - **Action**: Delete obsolete tests.

#### Part B: Refactoring & Simplification

**5. Logic Duplication (DRY Principle):**
- [ ] **Yes/No**: Same or very similar code blocks in multiple places?
  - **Action**: Extract to reusable private function. Name it clearly.

**6. Complex Conditionals:**
- [ ] **Yes/No**: Deeply nested `if/else` or conditions with many `and/or`?
  - **Action**: Extract to well-named function or variable.
  
  **Example:**
  ```python
  # Before
  if user.is_authenticated and user.has_permission('write') and resource.is_available:
      ...
  
  # After
  def can_user_write_resource(user, resource):
      return (user.is_authenticated and 
              user.has_permission('write') and 
              resource.is_available)
  
  if can_user_write_resource(user, resource):
      ...
  ```

**7. Magic Strings/Numbers:**
- [ ] **Yes/No**: Hardcoded string literals or numbers without named constants?
  - **Action**: Define as constants at file top or in config.
  
  **Example:**
  ```typescript
  // Before
  if (status === "pending") { ... }
  
  // After
  const STATUS_PENDING = "pending";
  if (status === STATUS_PENDING) { ... }
  ```

**8. Single Responsibility Violations:**
- [ ] **Yes/No**: Any function doing multiple unrelated things?
  - **Action**: Split into focused functions. Ask: "Does the function name honestly describe ALL it does?"

**9. Long Functions/Methods:**
- [ ] **Yes/No**: Any function exceeding 50 lines (backend) or 100 lines (frontend component)?
  - **Action**: Break into smaller, focused functions.

**10. God Classes/Files:**
- [ ] **Yes/No**: Any file exceeding 600 lines?
  - **Action**: Split into multiple files by concern. This is MANDATORY per AI charter.

#### Part C: Naming & Documentation

**11. Vague Naming:**
- [ ] **Yes/No**: Any variables/functions named `data`, `temp`, `handle`, `process`, `manager`, `utils`?
  - **Action**: Rename to precise, descriptive names. Good naming eliminates comments.

**12. Inconsistent Naming:**
- [ ] **Yes/No**: Mixing naming conventions (camelCase/snake_case in same file, inconsistent prefixes)?
  - **Action**: Standardize per project conventions.

**13. Misleading Names:**
- [ ] **Yes/No**: Any function names that don't accurately describe what the function does?
  - **Action**: Rename immediately. Misleading names are worse than bad names.

**14. Outdated Documentation:**
- [ ] **Yes/No**: Code changes made docstrings, comments, or README inaccurate?
  - **Action**: Update all affected documentation immediately.

**15. Missing Critical Documentation:**
- [ ] **Yes/No**: Complex algorithms or non-obvious logic without explanation?
  - **Action**: Add concise comments explaining WHY, not WHAT.

#### Part D: Testing & Quality

**16. Test Coverage Gaps:**
- [ ] **Yes/No**: New functions/methods lack corresponding tests?
- [ ] **Yes/No**: Edge cases not covered by tests?
  - **Action**: Add missing tests. Follow TDD principle retroactively if needed.

**17. Brittle Tests:**
- [ ] **Yes/No**: Tests depend on external state, timing, or other tests?
  - **Action**: Make tests isolated and deterministic.

**18. Snapshot Overuse:**
- [ ] **Yes/No**: Using snapshots for non-UI or unstable UI elements?
  - **Action**: Replace with explicit assertions.

**19. Test Naming:**
- [ ] **Yes/No**: Test names don't clearly describe what they test?
  - **Action**: Rename to `test_<specific_behavior_or_edge_case>`.

#### Part E: Security & Configuration

**20. Hardcoded Secrets:**
- [ ] **Yes/No**: API keys, passwords, or tokens in code?
  - **Action**: Move to `.env` immediately. Never commit secrets.

**21. Unsafe Operations:**
- [ ] **Yes/No**: Direct database queries without parameterization?
- [ ] **Yes/No**: User input used without validation/sanitization?
  - **Action**: Fix immediately. Security is Priority 1 per AI charter.

**22. Configuration Fragmentation:**
- [ ] **Yes/No**: Configuration values scattered across code instead of centralized?
  - **Action**: Consolidate in config files or environment variables.

#### Part F: Dependencies & Imports

**23. Dependency Bloat:**
- [ ] **Yes/No**: Added new dependencies that could be avoided?
- [ ] **Yes/No**: Using heavyweight library for simple task?
  - **Action**: Evaluate if dependency is truly necessary. Prefer standard library.

**24. Circular Imports:**
- [ ] **Yes/No**: Import cycles between modules?
  - **Action**: Restructure to break cycles. Often indicates poor separation of concerns.

**25. Import Organization:**
- [ ] **Yes/No**: Imports not organized (standard lib, third-party, local)?
  - **Action**: Organize imports per project conventions.

---

## Phase 4: Grayscale Aesthetic & Frontend Principles (If Applicable)

If changes involve UI, verify compliance with `docs/rules/frontend_design_principles.md`:

### 4.1 Grayscale-Only Verification
- [ ] No colors other than grayscale tokens used?
- [ ] Check all Tailwind classes: `bg-*, text-*, border-*` must use grayscale-N palette
- [ ] No hardcoded colors in CSS or inline styles?

### 4.2 Motion Rhythm Verification
- [ ] All animations use predefined duration tokens (`duration-200`, `duration-300`)?
- [ ] Easing curves from approved set (`ease-out`, `ease-in-out`)?
- [ ] No jarring or abrupt transitions?

### 4.3 Interaction Feedback
- [ ] All interactive elements have hover states?
- [ ] Focus states properly defined for accessibility?
- [ ] Loading states and transitions smooth?

---

## Phase 5: Integration Verification

### 5.1 Breaking Changes Check
- [ ] Changes maintain backward compatibility with existing features?
- [ ] If breaking changes, are they documented in task file Part 3?
- [ ] Migration path provided if data structures changed?

### 5.2 Cross-Service Integration
- [ ] If backend changes, frontend updated to match?
- [ ] WebSocket protocol changes synchronized?
- [ ] REST API changes documented in `docs/api_reference/`?

### 5.3 Configuration Changes
- [ ] New config fields added to `config.example.yml`?
- [ ] Default values sensible and safe?
- [ ] Database indexes created if needed?

---

## Phase 6: Test Execution & Verification

You must actually run the tests, not just read the completion report.

### 6.1 Backend Tests
```bash
# Activate virtual environment
source .venv/bin/activate

# Run all tests
pytest tests/nexus/ -v

# Check specific test files mentioned in task
pytest tests/nexus/unit/path/to/test_file.py -v

# Verify no skipped tests
pytest tests/nexus/ --collect-only | grep "skipped"
```

### 6.2 Frontend Tests
```bash
cd aura

# Run all tests
pnpm test:run

# Run with coverage
pnpm test:coverage

# Check for test failures
```

### 6.3 Linting & Formatting
```bash
# Backend
black nexus/ --check
flake8 nexus/

# Frontend
cd aura
pnpm lint
```

### 6.4 Manual Verification
If acceptance criteria include manual steps, execute them:
- [ ] Start dev servers (`scripts/shell/run.sh` or manual)
- [ ] Test commands mentioned in acceptance criteria
- [ ] Verify UI changes if applicable
- [ ] Check browser console for errors

---

## Phase 7: Git Hygiene Check

### 7.1 Commit Quality
```bash
# Review all commits on branch
git log main..HEAD --oneline

# Check each commit
git show <commit-hash>
```

**Verify:**
- [ ] Each commit follows Conventional Commits format (`feat:`, `fix:`, `refactor:`)?
- [ ] Commit messages in English, clear and descriptive?
- [ ] No "WIP", "temp", or debugging commits?
- [ ] Each commit is atomic (single logical change)?

**If commits need cleanup:**
```bash
# Squash/reword commits interactively
git rebase -i main
```

### 7.2 Untracked/Ignored Files
```bash
git status --ignored
```

- [ ] No accidentally untracked files that should be committed?
- [ ] No accidentally committed files that should be ignored?
- [ ] `.gitignore` updated if new file types introduced?

### 7.3 Diff Sanity Check
```bash
git diff main..HEAD
```

- [ ] No unintended changes (e.g., reformatted entire files)?
- [ ] No debug print statements left in code?
- [ ] No commented-out code blocks?
- [ ] No TODO/FIXME without tracking issue?

---

## Phase 8: Final Deliverables Check

Cross-reference task file Part 1 deliverables:

For each deliverable checkbox:
- [ ] File exists in git status or git diff?
- [ ] File contains expected changes per Part 2 detailed design?
- [ ] Corresponding tests exist and pass?

---

## Output Format: Entropy Reduction Report

After completing all phases, provide this structured report:

```markdown
# Entropy Reduction Report

**Task File**: `docs/tasks/YY-MMDD_name.md`
**Branch**: `[branch-name]`
**Review Date**: YYYY-MM-DD

---

## ✅ Task Report Validation

### Part 1 (Task Brief)
- **Status**: ✅ Pass / ⚠️ Issues Found
- **Issues**: [List any formalism in risks/dependencies, or "None"]
- **Action Taken**: [What you fixed, or "No action needed"]

### Part 2 (Implementation Plan)
- **Status**: ✅ Pass / ⚠️ Issues Found
- **Technical Depth**: [Adequate function signatures? Complete test lists?]
- **Action Taken**: [What you fixed, or "No action needed"]

### Part 3 (Completion Report)
- **Status**: ✅ Pass / ⚠️ Issues Found
- **Honesty Check**: [Shows real debugging? Includes failures?]
- **Completeness**: [All sections present? Test commands included?]
- **Action Taken**: [What you improved, or "No action needed"]

---

## 🧹 Code Entropy Reduction

### Cleanup Items
- **Commented Code**: [Deleted X lines from Y files]
- **Redundant Files**: [Deleted: file1.py, file2.tsx]
- **Unused Imports**: [Cleaned N files]
- **Dead Code**: [Removed X unused variables/functions]

### Refactoring Items
- **DRY Violations**: [Extracted function X from Y locations]
- **Complex Conditionals**: [Simplified function A, extracted predicate B]
- **Magic Values**: [Defined N constants]
- **SRP Violations**: [Split function X into Y and Z]
- **Long Functions**: [Broke down function A (was N lines, now M lines across K functions)]

### Naming & Documentation
- **Renamed**: [var `data` → `userProfile`, function `handle` → `processConfigUpdate`]
- **Updated Docs**: [Updated docstring in X, README section Y]
- **Added Comments**: [Explained algorithm in function Z]

### Testing Improvements
- **Added Tests**: [test_edge_case_A, test_error_handling_B]
- **Fixed Brittle Tests**: [Made test_X deterministic]
- **Improved Naming**: [Renamed test_Y to test_specific_behavior]

---

## 🏗️ Architecture Verification

### Alignment Check
- **Service Boundaries**: ✅ Correct / ⚠️ Issues Found
  - [Details or "All logic correctly placed"]
- **Feature Organization**: ✅ Correct / ⚠️ Issues Found
  - [Details or "Proper colocalization"]
- **Protocol Sync**: ✅ Synced / ⚠️ Drift Found
  - [Details or "Backend/frontend aligned"]

### Breaking Changes
- **Introduced**: Yes / No
- **If Yes**: [Documented in Part 3? Migration path provided?]

---

## 🎨 Frontend Principles (If Applicable)

- **Grayscale-Only**: ✅ Compliant / ❌ Violations Found
  - [Details or "N/A - no UI changes"]
- **Motion Rhythm**: ✅ Compliant / ❌ Violations Found
  - [Details or "N/A"]
- **Interaction Feedback**: ✅ Compliant / ❌ Missing States
  - [Details or "N/A"]

---

## ✅ Test Execution Results

### Backend Tests
```bash
pytest tests/nexus/ -v
[Paste actual output summary]
```
- **Status**: ✅ All Pass / ❌ N Failed
- **Coverage**: X% (if measured)

### Frontend Tests
```bash
pnpm test:run
[Paste actual output summary]
```
- **Status**: ✅ All Pass / ❌ N Failed

### Linting
- **Backend**: ✅ Pass / ❌ Issues
- **Frontend**: ✅ Pass / ❌ Issues

### Manual Verification
- [ ] Acceptance criteria 1: ✅ Verified
- [ ] Acceptance criteria 2: ✅ Verified
- [ ] [List all from Part 1]

---

## 📦 Deliverables Verification

[For each deliverable in Part 1:]
- [ ] `path/to/file1.py` - ✅ Created/Modified, Tests Pass
- [ ] `path/to/file2.tsx` - ✅ Created/Modified, Tests Pass
- [ ] [etc.]

---

## 🔍 Git Hygiene

- **Commits**: [N commits, all follow conventions / Needed cleanup]
- **Untracked Files**: [None / Listed Y files]
- **Diff Sanity**: ✅ Clean / ⚠️ Found unintended changes
  - [Details if issues found]

---

## 🚦 Final Recommendation

**Status**: ✅ APPROVED FOR COMMIT / ⚠️ REVISIONS NEEDED / ❌ REJECTED

### Summary
[2-3 sentence summary of review outcome]

### Required Actions Before Commit
[If status is not "APPROVED", list specific actions needed:]
1. [Action item 1]
2. [Action item 2]
...

### Optional Improvements (Non-Blocking)
[Suggestions for future work:]
- [Improvement 1]
- [Improvement 2]

---

## 📝 Reviewer Notes

[Any additional observations, concerns, or praise]

---

**Reviewer Signature**: [Your AI model name]
**Timestamp**: [YYYY-MM-DD HH:MM UTC]
```

---

## Critical Failure Scenarios

**REJECT IMMEDIATELY and do NOT approve commit if:**

1. **Security**: Any hardcoded secrets, SQL injection risks, or XSS vulnerabilities
2. **Data Loss**: Any code that could delete/corrupt data without proper safeguards
3. **Tests**: Test suite fails or tests skipped without justification
4. **Breaking Changes**: Undocumented breaking changes to public APIs
5. **Architecture**: Logic placed in wrong service/layer violating separation of concerns
6. **600-Line Rule**: Any file exceeds 600 lines (MANDATORY per AI charter)
7. **Formalism**: Task file contains procedural risks/dependencies ("need testing", "team approval")

---

## Review Completion Actions

After generating the Entropy Reduction Report:

1. **If APPROVED**: 
   - Notify user the branch is ready for commit
   - Provide commit message if not already written
   
2. **If REVISIONS NEEDED**:
   - Make the revisions yourself if they're simple (cleanup, naming, docs)
   - For complex issues, explain to user what needs fixing
   
3. **If REJECTED**:
   - Provide detailed explanation of critical issues
   - Do NOT proceed until issues resolved

---

**Remember**: Your role is quality gatekeeper. Be thorough, honest, and uncompromising on standards. The repository's long-term health depends on your vigilance.
