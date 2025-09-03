# 02: Configuration Reference

This document provides an exhaustive reference for all parameters in the `config.default.yml` and `.env` files.

## I. Environment Variables (`.env`)

This file stores secrets and environment-specific connection strings. It should **never** be committed to version control.

-   **`GEMINI_API_KEY`**
    -   **Description**: Your secret API key for the Google Gemini LLM.
    -   **Required**: Yes
    -   **Example**: `AIzaSy...`

-   **`MONGO_URI`**
    -   **Description**: The full connection string for your MongoDB instance (local or Atlas).
    -   **Required**: Yes
    -   **Example**: `mongodb+srv://user:<password>@cluster.mongodb.net/?retryWrites=true&w=majority`

-   **`TAVILY_API_KEY`**
    -   **Description**: Your secret API key for the Tavily search service, used by the `web_search` tool.
    -   **Required**: Yes, if using the `web_search` tool.
    -   **Example**: `tvly-...`

## II. System Configuration (`config.default.yml`)

This file stores non-secret, application-level configurations.

### `system`

-   **`log_level`**
    -   **Description**: Sets the minimum logging level for the application.
    -   **Type**: `string`
    -   **Allowed Values**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
    -   **Default**: `INFO`

-   **`max_tool_iterations`**
    -   **Description**: A safety valve to prevent infinite agentic loops. Sets the maximum number of times the AI can call tools within a single `Run`.
    -   **Type**: `integer`
    -   **Default**: `5`

### `server`

-   **`host`**
    -   **Description**: The host address for the FastAPI/WebSocket server to bind to.
    -   **Type**: `string`
    -   **Default**: `127.0.0.1`

-   **`port`**
    -   **Description**: The port for the FastAPI/WebSocket server to listen on.
    -   **Type**: `integer`
    -   **Default**: `8000`

### `llm`

-   **`provider`**
    -   **Description**: Specifies which LLM provider to use. Currently, only "google" is supported.
    -   **Type**: `string`
    -   **Default**: `google`

-   **`providers.google`**
    -   **`api_key`**: References the `GEMINI_API_KEY` from `.env`.
    -   **`base_url`**: The base URL for the Gemini API.
    -   **`model`**: The specific Gemini model to use for chat completions.
    -   **`timeout`**: Request timeout in seconds.

### `database`

-   **`db_name`**
    -   **Description**: The name of the MongoDB database to use for storing messages.
    -   **Type**: `string`
    -   **Default**: `NEXUS_DB`

-   **`mongo_uri`**: References the `MONGO_URI` from `.env`.

### `memory`

-   **`history_context_size`**
    -   **Description**: The number of recent messages to retrieve from the database to build the context for a new `Run`.
    -   **Type**: `integer`
    -   **Default**: `20`