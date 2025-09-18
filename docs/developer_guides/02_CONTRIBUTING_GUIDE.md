# 02: Contributing Guide

This guide outlines the standard procedures and best practices for contributing to the YX NEXUS project. Adhering to these guidelines ensures consistency, quality, and maintainability across the codebase.

## I. Core Philosophy

Before writing any code, internalize the principles outlined in the [Vision & Philosophy](../knowledge_base/01_VISION_AND_PHILOSOPHY.md) document. Every contribution will be evaluated based on its alignment with our core architectural and aesthetic philosophies.

-   **Backend**: Does it respect the event-driven, decoupled nature of NEXUS?
-   **Frontend**: Does it adhere to the "Grayscale Moderation" and "Living Interaction" principles of AURA?

## II. Development Workflow

We follow a standard Git workflow:

1.  Create a new feature branch from the `main` branch: `git checkout -b feature/your-feature-name`.
2.  Make your changes, committing frequently with clear, concise messages.
3.  Ensure your code is formatted using the project's standards (e.g., `black` for Python, `prettier` for TypeScript).
4.  Write or update tests that cover your changes.
5.  Push your branch and open a Pull Request against `main`.
6.  Ensure all automated checks (CI, tests) pass.

We follow a strict Test-Driven Development (TDD) workflow. Any new feature or bug fix must begin with a test.

1.  **RED**: Create a new branch. Write a failing test that precisely defines the new requirement or replicates the bug.
2.  **GREEN**: Write the absolute minimum amount of production code required to make the test pass.
3.  **REFACTOR**: Clean up both the production and test code for clarity and adherence to our principles, ensuring tests continue to pass.
4.  **COMMIT**: Commit your changes with a clear message.
5.  **PULL REQUEST**: Push your branch and open a Pull Request. Ensure all automated CI checks pass.

## III. Common Development Scenarios

This section provides recipes for the most common types of contributions.

### Scenario 1: Adding a New Tool to NEXUS

Adding a new tool is a purely additive process designed to be simple and non-disruptive.

1.  **Create the Definition File**:
    -   Navigate to `nexus/tools/definition/`.
    -   Create a new Python file for your tool or tool category (e.g., `file_system.py`).

2.  **Implement the Tool Function**:
    -   Write your tool as a standard, **synchronous** Python function.
    -   It should accept simple arguments (strings, numbers) and return a simple value (usually a formatted string).
    -   Ensure it handles its own errors and includes logging.

3.  **Define the Tool Metadata**:
    -   In the same file, create a dictionary constant named `YOUR_FUNCTION_NAME_TOOL` (e.g., `READ_FILE_TOOL`).
    -   This dictionary must conform to the JSON Schema expected by the LLM for tool definitions (`type`, `function.name`, `function.description`, `function.parameters`).

4.  **Automatic Registration**:
    -   That's it. The `ToolRegistry`'s `discover_and_register` mechanism will automatically find and load your new tool the next time the server starts. No other files need to be modified.

### Scenario 2: Adding a New UI Event

To introduce a new type of real-time feedback from NEXUS to AURA, you must update the "contract" between them.

1.  **Update Backend Topics (`nexus/core/topics.py`)**:
    -   If the new event warrants a new topic, add a new constant to the `Topics` class. More often, it will be a new event type within the existing `Topics.UI_EVENTS`.

2.  **Update Backend Broadcaster (`nexus/services/orchestrator.py`)**:
    -   In the appropriate state-transition method (e.g., `handle_...`), create and publish the new UI event `Message`. Ensure its `content` follows the standard structure: `{"event": "your_new_event", "run_id": ..., "payload": {...}}`.

3.  **Update Frontend Protocol (`aura/src/services/websocket/protocol.ts`)**:
    -   Define a new TypeScript interface for your event (e.g., `YourNewEventPayload`, `YourNewEvent`).
    -   Add it to the `NexusEvent` union type.
    -   Create a corresponding type guard function (e.g., `isYourNewEvent(...)`).

4.  **Update Frontend State (`aura/src/features/chat/store/auraStore.ts`)**:
    -   Add a new `action` to the store to handle the new event (e.g., `handleYourNewEvent(payload)`). This action will be responsible for mutating the state in response to the event.

5.  **Update Frontend Controller (`aura/src/features/chat/hooks/useAura.ts`)**:
    -   In the `useEffect` block, subscribe to the new event from the `websocketManager` and wire it to the new store action.

### Scenario 3: Creating a New Frontend Component

Follow the established patterns to ensure consistency.

1.  **Location**: Place new components in the appropriate directory:
    -   `src/components/ui/`: For generic, reusable UI elements (like a custom `Slider`).
    -   `src/components/common/`: For more complex, common components (like a `Modal`).
    -   `src/features/chat/components/`: For components specific to the chat feature.
2.  **Styling**: Use Tailwind CSS and the `cn` utility. Adhere strictly to the color palette and spacing system in `globals.css`.
3.  **State**: Components should be "dumb" and receive state via props. If local state is needed, use `useState`. For global state, access it via the `useAura` hook in a container component.

## IV. Code Style & Quality

-   **Python**: We use `black` for formatting and `flake8` for linting.
-   **TypeScript/React**: We use `prettier` for formatting and `eslint` for linting.
-   **Testing**: All new features must be accompanied by corresponding tests. All bug fixes must include a regression test that fails before the fix and passes after.