# The NEXUS & AURA Testing Charter

This document is the foundational law governing all quality assurance practices within the NEXUS project. It defines our testing philosophy, mandatory workflows, and the strategic purpose of each layer of our test suite. Adherence to this charter is non-negotiable for all contributions.

## I. Core Principles

1.  **Test-Driven Development (TDD) is Mandatory**:
    All new features, bug fixes, and refactors **must** begin with a test. For new features, this test will initially fail (RED). For bug fixes, this test must replicate the bug and fail before the fix is applied. The primary goal of any code change is to make the corresponding test pass (GREEN).

2.  **Tests as First-Class Code**:
    Test code is not an afterthought; it is a core part of our product. It must be written with the same standards of clarity, simplicity, and maintainability as our production code. Tests are subject to the same rigorous code review process.

3.  **The Pragmatic Testing Pyramid**:
    Our strategy focuses on maximizing confidence while minimizing cost and brittleness. We prioritize tests that are fast, reliable, and provide the most value for our specific project context.

---

## II. The TDD Workflow (The RED-GREEN-REFACTOR Cycle)

Every code change must follow this sequence:

1.  **RED**: Write a failing test that precisely defines the new requirement or bug. Run it and watch it fail. This proves the test works and the feature/fix is not already present.
2.  **GREEN**: Write the **absolute minimum** amount of production code required to make the test pass. Do not add any extra features or optimizations at this stage.
3.  **REFACTOR**: With the safety net of a passing test, refactor both the production code and the test code for clarity, simplicity, and adherence to our architectural principles. Run the test again to ensure it still passes.
4.  **REPEAT**: Continue the cycle for the next small increment of functionality.

---

## III. The Testing Pyramid: Our Strategic Layers

### Layer 1 (The Foundation): Backend Unit & Integration Tests (NEXUS)

-   **Location**: `tests/nexus/unit/`, `tests/nexus/integration/`
-   **Core Focus**: This is the **bedrock of our quality assurance**. We combine unit and service-level integration tests to form a powerful, fast, and reliable suite.
-   **What to Test**:
    -   **Unit Tests**: Pure logic functions, data models, and individual providers (e.g., `MongoProvider`).
    -   **Integration Tests**: The behavior of a single service in response to simulated `NexusBus` events. This is our **default and most important** type of backend test.
-   **CI/CD Status**: **Mandatory & Automated**. These tests run on every commit in our CI pipeline. A failure here blocks all deployments.

### Layer 2 (The Core): Frontend Component Tests (AURA)

-   **Location**: Colocated `__tests__/` directories inside each feature or service folder (e.g., `aura/src/features/chat/components/__tests__/`).
-   **Core Focus**: Ensuring our UI components are visually correct, functionally robust, and resilient to change.
-   **What to Test**:
    -   Individual React components in isolation (e.g., `ToolCallCard`, `ChatInput`).
    -   Simulated user interactions (clicks, typing) to assert rendered output and function calls.
-   **Tools**: `Vitest` + `React Testing Library` (commands: `pnpm test`, `pnpm test:run`, `pnpm test:coverage`).
-   **CI/CD Status**: **Mandatory & Automated**. These tests also run on every commit. A failure here blocks all deployments.

### Layer 3 (The Apex): Backend End-to-End (E2E) Tests (NEXUS)

-   **Location**: `tests/nexus/e2e/`
-   **Core Focus**: To be used as a **manually-triggered diagnostic tool**, not as a regular CI gate.
-   **What it is**: A "full system health check" that starts the entire backend stack and simulates a real user journey.
-   **Why it's Manual**: E2E tests are inherently slow and can be "flaky" (fail due to external factors like network latency). For our "personal sanctuary" project, the high cost of maintaining them as an automated CI gate outweighs the benefits, which are already largely covered by our robust integration tests.
-   **When to Run**:
    -   Before a major new feature release.
    -   When diagnosing a complex, system-wide bug that is difficult to replicate with integration tests.
    -   Periodically, to ensure the overall health of the deployed environment.

---

## IV. Fixtures & Helpers

-   **Location**: `tests/fixtures/`
-   **Purpose**: To store reusable test data, mock objects, and helper functions. This avoids code duplication in our tests and keeps test cases focused on the specific behavior being tested.
-   **Example**: A fixture that provides a pre-configured, mock `NexusBus` instance, or a helper function that creates a standard `Run` object for use in multiple tests.
