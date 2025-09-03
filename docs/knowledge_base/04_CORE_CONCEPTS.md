# 04: Core Concepts

This document serves as the official glossary for the YX NEXUS project. It defines the fundamental entities and processes that constitute our system. A clear understanding of these concepts is essential for comprehending our architecture and contributing to the codebase.

---

## 1. `Session` & `session_id`

-   **Definition**: A `Session` represents a **single, continuous stream of memory and context**. The `session_id` is its unique identifier.
-   **Analogy**: Think of it as the unique identifier for a single, unbroken "memory thread" or "consciousness stream."
-   **Implementation**:
    -   On the AURA frontend, the `session_id` is generated once and persisted in the browser's `localStorage`.
    -   This ensures that even if the user refreshes the page or reconnects, they are always rejoining the same memory stream.
    -   Every `Message` persisted in the database is tagged with this `session_id`, allowing NEXUS to retrieve the complete, ordered history of a conversation.
-   **Key Insight**: A `Session` is not a "user." It is an anonymous, client-side identifier for a specific conversational context.

This is the design and implementation of our current stage.

---

## 2. `Run` & `run_id`

-   **Definition**: A `Run` is an ephemeral object that represents the **entire lifecycle of a single interaction**, from the moment a user sends a message to the moment the AI provides its final response. The `run_id` is its unique identifier for that specific interaction.
-   **Analogy**: If a `Session` is a person's entire life story, a `Run` is a single, complete thought process or a single sentence they speak.
-   **Lifecycle**: A `Run` is born in the `WebsocketInterface` when a user message is received. It travels through the `NexusBus` to the `Orchestrator`, where its state (`RunStatus`) is managed as it moves through context building, LLM calls, and tool executions. Once the final AI response is sent, the `Run` object is destroyed.
-   **Key Insight**: The `run_id` is the primary key for tracing and debugging a single, complete "thought process" as it flows through the entire distributed system.

---

## 3. `Message`

-   **Definition**: A `Message` is the **atomic, immutable unit of information** that flows through the NEXUS system.
-   **Analogy**: It is the "neurotransmitter" of our system. Every piece of information—a user's query, an AI's response, a tool's output, an internal command—is encapsulated in a `Message`.
-   **Properties**: Every `Message` has a `role` (`HUMAN`, `AI`, `SYSTEM`, `TOOL`), `content`, a `timestamp`, and is tagged with both a `run_id` and a `session_id`.
-   **Key Insight**: The principle of "Event Sourcing" is built upon the `Message`. Our database is simply a chronological log of all `Message` events that have ever occurred in a `Session`.

---

## 4. `NexusBus`

-   **Definition**: The `NexusBus` is the central, asynchronous **"nervous system"** of the NEXUS backend.
-   **Function**: It is the sole communication channel for all backend services. Services `publish` `Message` objects to named channels (`Topics`), and other services `subscribe` to these topics to receive and react to them.
-   **Architectural Significance**:
    -   **Decoupling**: It ensures that services are completely independent of one another. The `Orchestrator` does not know or care that the `ToolExecutor` exists; it only knows how to publish a `TOOLS_REQUESTS` event.
    -   **Scalability**: New services can be added to listen to existing events without modifying any of the original services, allowing for infinite, non-disruptive system expansion.
-   **Key Insight**: The `NexusBus` transforms our backend from a rigid, monolithic call stack into a flexible, resilient, and observable organism.

---

## 5. `Agentic Loop`

-   **Definition**: The `Agentic Loop` is the core process by which NEXUS solves complex problems that require external tools. It is not a literal `while` loop in the code, but an emergent behavior of the `Orchestrator`'s state machine.
-   **The Flow**:
    1.  **Decision**: The `Orchestrator` sends a query to the LLM. The LLM decides it needs a tool and responds with `tool_calls`.
    2.  **Action**: The `Orchestrator` receives the `tool_calls`, dispatches requests to the `ToolExecutor`, and enters a `AWAITING_TOOL_RESULT` state.
    3.  **Observation**: The `ToolExecutor` runs the tool and publishes the result.
    4.  **Synthesis**: The `Orchestrator` receives the tool result, appends it to the conversation history, and **loops back** by sending the updated history to the LLM for the next step.
-   **Key Insight**: The `Agentic Loop` is the mechanism that elevates NEXUS from a simple conversational AI to a true, autonomous problem-solving agent.