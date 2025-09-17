## Stage 1: Test File Modification (RED Phase)
**Goal**: Modify the existing test to expect UTC timestamp format instead of Beijing time
**Success Criteria**: Test fails because production code still outputs Beijing time
**Tests**:
- Rename `test_formats_llm_messages_includes_beijing_timestamp` to `test_formats_llm_messages_includes_utc_timestamp`
- Update assertion to expect UTC format: "2025-09-17 01:16:03 UTC" instead of Beijing time
**Status**: Complete

## Stage 2: Run Tests to Verify Failure (RED Phase)
**Goal**: Confirm the test fails due to Beijing time still being output
**Success Criteria**: Test fails with expected assertion error
**Tests**: Run pytest to verify the specific test fails
**Status**: Complete

## Stage 3: Modify ContextService Logic (GREEN Phase)
**Goal**: Update _format_llm_messages to use UTC formatting
**Success Criteria**: Test passes with UTC timestamp format
**Tests**:
- Remove Beijing timezone conversion logic
- Implement UTC formatting: YYYY-MM-DD HH:MM:SS UTC
**Status**: Complete

## Stage 4: Run Tests to Verify Success (GREEN Phase)
**Goal**: Confirm all tests pass with UTC implementation
**Success Criteria**: All 166 tests pass including the updated UTC test
**Tests**: Full test suite execution
**Status**: Complete

## Stage 5: Refactor and Cleanup (REFACTOR Phase)
**Goal**: Optimize and clean up the UTC timestamp implementation
**Success Criteria**: Code is clean, efficient, and well-documented
**Tests**: Ensure no regressions after refactoring
**Status**: Complete