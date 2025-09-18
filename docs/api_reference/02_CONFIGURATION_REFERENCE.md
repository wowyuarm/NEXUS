# 02: Configuration Reference

This document specifies the structure of configuration documents stored in the `system_configurations` collection in MongoDB.

## I. Document Schema

Each document in the collection represents the configuration for a specific environment.

-   **`_id`**: `string` - A unique identifier for the configuration set (e.g., `config_development`).
-   **`environment`**: `string` - The name of the environment this configuration applies to (`development`, `production`).
-   **`log_level`**: `string` - The minimum logging level for the application (`DEBUG`, `INFO`, etc.).
-   **`max_tool_iterations`**: `integer` - The safety valve for the agentic loop.
-   **`active_llm_provider`**: `string` - The key of the default LLM provider to use from the `llm_providers` object.
-   **`llm_providers`**: `object` - An object containing configurations for different LLM providers.
    -   Each key is the provider name (e.g., `google`).
    -   The value is an object with provider-specific parameters (`model`, `timeout`, etc.).
-   **`database`**: `object` - Contains database-specific settings.
    -   `db_name_template`: `string` - A template for the database name, using `{env}` as a placeholder (e.g., `NEXUS_DB_{ENV}`).
-   **`memory`**: `object` - Settings related to the memory system.
    -   `history_context_size`: `integer` - The number of recent messages to load for context.
-   **`aura_config`**: `object` - A dedicated object containing all configurations that will be exposed to the AURA frontend via the `/api/v1/config/aura` endpoint.
    -   `webSocketUrl_template`: `string` - A template for the public WebSocket URL, using `{host}` as a placeholder.

## II. Example `development` Configuration Document

```json
{
  "_id": "config_development",
  "environment": "development",
  "log_level": "DEBUG",
  "max_tool_iterations": 5,
  "active_llm_provider": "google",
  "llm_providers": {
    "google": {
      "model": "gemini-2.5-flash",
      "timeout": 60
    }
  },
  "database": {
    "db_name_template": "NEXUS_DB_{ENV}"
  },
  "memory": {
    "history_context_size": 20
  }
}