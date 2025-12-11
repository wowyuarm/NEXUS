# API & Configuration Reference

This section provides a detailed, technical reference for the core interfaces and configuration options of the NEXUS project. It is the single source of truth for the system's "hard contracts."

Unlike the [Knowledge Base](../knowledge_base/00_INDEX.md) which explains concepts, or the [Developer Guides](../developer_guides/00_INDEX.md) which explain processes, this reference provides precise, exhaustive specifications.

---

## Table of Contents

1. **[01 SSE Protocol](./01_SSE_PROTOCOL.md)**
   - A complete specification of the HTTP + SSE communication protocol between the AURA frontend and the NEXUS backend
   - Details chat streaming (`POST /chat`), command execution (`POST /commands/execute`), and persistent streams (`GET /stream/{public_key}`)
   - Covers all event types: `run_started`, `text_chunk`, `tool_call_*`, `run_finished`, `error`, `command_result`

2. **[02 Configuration Reference](./02_CONFIGURATION_REFERENCE.md)**
   - Exhaustive documentation of the genesis configuration document structure
   - Explains the inheritance-and-override pattern for user configurations
   - Details all sections: `system`, `llm`, `user_defaults`, `ui`, etc.
   - Includes initialization procedures and environment variable substitution

3. **[03 REST API Protocol](./03_REST_API.md)** ✨ NEW
   - Complete specification of RESTful HTTP API for data management
   - Authentication mechanisms: Bearer tokens and cryptographic signatures
   - Endpoints for configuration (`/config`), prompts (`/prompts`), and history (`/messages`)
   - Integration examples in JavaScript and Python
   - Security considerations and future enhancements

---

## Document Purpose and Usage

### For Frontend Developers

-   **[01 SSE Protocol](./01_SSE_PROTOCOL.md)**: Implement real-time chat interface with streaming responses
-   **[03 REST API Protocol](./03_REST_API.md)**: Build configuration panels and settings UI
-   **[02 Configuration Reference](./02_CONFIGURATION_REFERENCE.md)**: Understand available configuration options and UI metadata

### For Backend Developers

-   **[02 Configuration Reference](./02_CONFIGURATION_REFERENCE.md)**: Modify system defaults and add new configuration options
-   **[01 SSE Protocol](./01_SSE_PROTOCOL.md)**: Extend event types or add new server-to-client messages
-   **[03 REST API Protocol](./03_REST_API.md)**: Add new REST endpoints or modify authentication logic

### For System Administrators

-   **[02 Configuration Reference](./02_CONFIGURATION_REFERENCE.md)**: Configure environments and manage LLM providers
-   **[03 REST API Protocol](./03_REST_API.md)**: Understand security model and authentication requirements

---

## Key Architectural Concepts

### HTTP + SSE Architecture

NEXUS employs a **unified HTTP architecture**:

| Interface | Purpose | Use Cases |
|-----------|---------|----------|
| **SSE Streaming** (01) | Real-time, server-to-client streaming | Chat responses, tool execution updates, connection state |
| **REST API** (03) | Stateless, CRUD operations | Configuration management, command execution, historical data retrieval |

**Design Principle**: Use SSE for **streaming responses**, REST for **request-response operations**.

### Configuration Inheritance

The **inheritance-and-override pattern** (02, 03) enables:

-   **System defaults** defined in `configurations` collection
-   **User overrides** stored in `identities` collection
-   **Effective configuration** = defaults + overrides
-   **Dynamic UI generation** from metadata in configuration

**Benefits**:
-   Consistent defaults across all users
-   Per-user customization without code changes
-   Frontend adapts to backend configuration changes

### Security Model

Three-tier authentication (03):

1. **No auth** (public endpoints): `/commands`
2. **Bearer token** (read operations): `GET /config`, `GET /messages`
3. **Cryptographic signature** (write operations): `POST /config`, `POST /prompts`

**Security Properties**:
-   Public keys as identity (no password storage)
-   Signatures prevent unauthorized writes
-   Compatible with Web3 wallets

---

## Cross-Document References

### SSE ↔ REST Integration

-   **Identity**: Users authenticate via public key (Bearer token) in all requests
    -   SSE streams: Token in Authorization header or path parameter
    -   REST: Provided as Bearer token

-   **Configuration**: User config from REST API affects chat behavior
    -   `config.model` determines which LLM processes chat messages
    -   `config.history_context_size` affects context loading in `ContextService`

-   **Message History**: Written via chat endpoint, read via REST
    -   `PersistenceService` saves all chat messages
    -   `GET /api/v1/messages` retrieves historical data

### Configuration ↔ Code Integration

-   **ConfigService** (`nexus/services/config.py`): Loads configuration from MongoDB
-   **IdentityService** (`nexus/services/identity.py`): Merges defaults + overrides
-   **ContextService** (`nexus/services/context.py`): Uses `prompts.*.order` for system prompt composition
-   **LLMService** (`nexus/services/llm/service.py`): Routes to providers based on `llm.catalog`

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.1 | 2025-12-11 | Migrated from WebSocket to SSE Protocol (01) |
| 1.0 | 2025-10-20 | Added REST API Protocol (03), Updated Configuration Reference (02) |
| 0.9 | 2025-10-15 | Initial WebSocket Protocol (01) and Configuration Reference (02) |

---

## Related Documentation

-   **[Dynamic Personalization Architecture](../knowledge_base/technical_references/dynamic_personalization_architecture.md)**: High-level design philosophy
-   **[Implementation Reports](../implementation_reports/)**: Detailed implementation decisions
-   **[Developer Guides](../developer_guides/)**: Step-by-step tutorials

---

## Feedback and Contributions

This is a living document. If you find:
-   **Inaccuracies**: Create an issue with the document section reference
-   **Missing Information**: Suggest additions via pull request
-   **Unclear Explanations**: Request clarification in discussions

**Maintenance Responsibility**: Backend team owns 01-03, Frontend team collaborates on 01.
