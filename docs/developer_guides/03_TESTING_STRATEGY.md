# 03: Testing Strategy

This document outlines the testing strategy for the YX NEXUS project. Our approach is based on the "Testing Pyramid" model, which emphasizes a healthy mix of test types to ensure code quality, maintainability, and developer confidence.

## I. The Testing Pyramid

Our strategy is structured in three layers:

1.  **Unit Tests (Base)**: Fast, isolated tests for individual functions and classes. They form the largest part of our test suite.
2.  **Integration Tests (Middle)**: Tests for individual services, verifying their interaction with mocked dependencies (like the `NexusBus`).
3.  **End-to-End (E2E) Tests (Peak)**: A small number of tests that run the entire application stack to verify a complete user flow.

## II. Unit Tests

-   **Purpose**: To verify the correctness of the smallest, isolated pieces of logic.
-   **Location**: `tests/unit/`
-   **Technology**: `pytest`, `pytest-mock`
-   **When to Write**: When adding or modifying a utility function, a provider (`MongoProvider`), or a class with pure logic (`ToolRegistry`, `ConfigService`).
-   **Key Principle**: **Isolation**. Unit tests must **never** touch the network, the filesystem (unless using a temporary fixture), or a real database. Use mocks to replace all external dependencies.

**Example**: Testing the `ConfigService` by mocking the `open` function and providing fake YAML content.

## III. Integration Tests

-   **Purpose**: To verify that a single service behaves correctly within the event-driven ecosystem. This is our **most critical testing layer**.
-   **Location**: `tests/integration/`
-   **Technology**: `pytest`, `pytest-asyncio`, `pytest-mock`
-   **When to Write**: When adding or modifying the logic of any service in the `nexus/services/` directory.
-   **Key Principle**: **Contract Testing**. We are not testing the dependencies, but rather our service's **contract** with them. We mock the `NexusBus` and assert that our service `publishes` the correct events to the correct topics in response to incoming events.

**Example**: Testing the `OrchestratorService` by:
1.  Creating an `OrchestratorService` instance with a mocked `NexusBus`.
2.  Manually calling a handler method (e.g., `await orchestrator.handle_new_run(...)`).
3.  Asserting that `mock_bus.publish` was called with the expected topic and message content.

## IV. End-to-End (E2E) Tests

-   **Purpose**: To verify that a complete user journey through the entire, integrated system works as expected.
-   **Location**: `tests/e2e/`
-   **Technology**: `pytest`, `pytest-asyncio`, `websockets`
-   **When to Write**: Sparingly. We only write E2E tests for the most critical user flows (e.g., a full dialogue with a tool call). They are not for testing edge cases.
-   **Key Principle**: **Black Box Testing**. The E2E test acts like a real user. It knows nothing about the internal workings of the system. It only interacts with the public interface (our WebSocket API) and asserts the final output.
-   **Environment**: Our E2E tests are designed to be self-contained. The `conftest.py` fixture automatically starts the NEXUS service in a separate process and connects it to a **temporary, isolated MongoDB database** that is destroyed after the test run.

**Example**: The `test_full_interaction_flow.py` script:
1.  The `nexus_service` fixture starts the entire application.
2.  The test connects to the WebSocket URL provided by the fixture.
3.  It sends a user message.
4.  It collects all UI events broadcast back from the server.
5.  It asserts that the sequence and content of these events match the expected user experience.
6.  The fixture tears down the service and the temporary database.

## V. How to Run Tests

From the project's root directory (`NEXUS/`):

```bash
# Run all tests
pytest

# Run only unit tests
pytest tests/unit/

# Run tests for a specific file
pytest tests/integration/services/test_orchestrator_service.py

# Run a specific test function
pytest tests/e2e/test_full_interaction_flow.py::test_tool_call_interaction