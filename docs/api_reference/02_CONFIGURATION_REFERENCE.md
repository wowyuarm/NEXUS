# 02: Configuration Reference

This document specifies the structure of the genesis configuration document stored in the `configurations` collection in MongoDB. This template serves as the foundation for all user configurations through an inheritance-and-override pattern.

---

## I. Document Schema

The configuration document is stored once per environment (`development`, `production`) and provides system defaults that can be overridden by individual users.

### Top-Level Fields

-   **`environment`**: `string` - Environment identifier (`"development"` or `"production"`)
-   **`system`**: `object` - Core system settings (administrator-defined, not user-overridable)
-   **`server`**: `object` - HTTP server configuration
-   **`security`**: `object` - Security policies and authentication requirements
-   **`llm`**: `object` - LLM provider directory and model catalog
-   **`user_defaults`**: `object` - Default configuration inherited by all new users
-   **`ui`**: `object` - UI rendering metadata for frontend panels

---

## II. System Section

Core system laws that control fundamental behavior and safety boundaries.

```yaml
system:
  log_level: "INFO"              # Logging verbosity: DEBUG, INFO, WARNING, ERROR
  max_tool_iterations: 5         # Safety valve for agentic loop
  tool_execution_timeout: 20     # Timeout for tool execution in seconds
  app_name: "YX Nexus"           # Application name (可下发给前端)
```

**Fields**:
-   `log_level`: Controls logging verbosity throughout the system
-   `max_tool_iterations`: Prevents infinite loops in tool-calling sequences
-   `tool_execution_timeout`: Maximum time allowed for tool execution
-   `app_name`: Display name for the application (future: user-customizable)

---

## III. Server Section

HTTP server listen configuration.

```yaml
server:
  host: "0.0.0.0"  # Listen address (overridden by HOST env var in production)
  port: 8000       # Listen port (overridden by PORT env var in production)
```

**Production Override**:
Environment variables `HOST` and `PORT` take precedence over these values.

---

## IV. Security Section

Security policies and command-level authentication requirements.

```yaml
security:
  signature_required_commands:
    - "identity"
    - "config"
    - "prompt"
```

**Fields**:
-   `signature_required_commands`: List of command names requiring cryptographic signatures
-   Frontend can query this list to determine when to prompt for signatures

---

## V. LLM Section

Defines the "model-as-provider" catalog architecture.

### Providers Subsection

Connection information for LLM service providers (not user-overridable).

```yaml
llm:
  providers:
    google:
      api_key: "${GEMINI_API_KEY}"
      base_url: "https://generativelanguage.googleapis.com/v1beta"
    deepseek:
      api_key: "${DEEPSEEK_API_KEY}"
      base_url: "https://api.deepseek.com/v1"
    openrouter:
      api_key: "${OPENROUTER_API_KEY}"
      base_url: "https://openrouter.ai/api/v1"
```

**Notes**:
-   API keys use environment variable substitution (`${VAR_NAME}`)
-   Loaded via `ConfigService` during initialization

### Catalog Subsection

Model directory mapping friendly names to providers.

```yaml
llm:
  catalog:
    gemini-2.5-flash:
      provider: google
      id: gemini-2.5-flash           # Provider-specific model ID
      aliases: ["Gemini-2.5-Flash"]  # Friendly names for UI
      default_params:
        temperature: 0.7
        max_tokens: 8192
    
    deepseek-chat:
      provider: deepseek
      id: deepseek-chat
      aliases: ["DeepSeek-Chat"]
      default_params:
        temperature: 0.9
        max_tokens: 8192
    
    moonshotai/kimi-k2:free:
      provider: openrouter
      id: moonshotai/kimi-k2:free
      aliases: ["Kimi-K2"]
      default_params:
        temperature: 0.8
        max_tokens: 8192
```

**Fields**:
-   `provider`: References a key in `llm.providers`
-   `id`: Provider-specific model identifier (can match catalog key)
-   `aliases`: User-friendly names displayed in UI (dynamically loaded into `field_options`)
-   `default_params`: Provider-specific default parameters

**Dynamic UI Integration**:
The `aliases` field is used to dynamically populate `ui.field_options.config.model.options`:

```python
# In IdentityService.get_effective_profile()
llm_catalog = genesis_template.get('llm', {}).get('catalog', {})
model_aliases = []
for model_key, model_meta in llm_catalog.items():
    aliases = model_meta.get('aliases', [])
    model_aliases.extend(aliases or [model_key])

field_options['config.model']['options'] = sorted(set(model_aliases))
```

---

## VI. User Defaults Section

Default configuration and prompts inherited by all new users.

### Config Subsection

Runtime configuration defaults (user-overridable via `config_overrides`).

```yaml
user_defaults:
  config:
    model: "gemini-2.5-flash"     # Default LLM model (catalog key)
    temperature: 0.8              # Sampling temperature
    max_tokens: 4096              # Maximum response tokens
    history_context_size: 20      # Number of recent messages in context
```

**User Override Mechanism**:
Users can override these via `POST /api/v1/config`:
```python
# Stored in identities collection:
{
  "public_key": "0x...",
  "config_overrides": {
    "model": "deepseek-chat",
    "temperature": 0.9
  }
}

# Effective config = user_defaults.config + config_overrides
```

### Prompts Subsection

Modular prompt system with structured metadata.

```yaml
user_defaults:
  prompts:
    field:
      content: ""      # Loaded from nexus/prompts/nexus/field.md
      editable: false  # System-managed, defines the interaction space
      order: 1         # Concatenation order in system prompt
    
    presence:
      content: ""      # Loaded from nexus/prompts/nexus/presence.md
      editable: false  # System-managed, defines AI's way of being
      order: 2
    
    capabilities:
      content: ""      # Loaded from nexus/prompts/nexus/capabilities.md
      editable: false  # System-managed, defines tools and abilities
      order: 3
    
    learning:
      content: ""      # Loaded from nexus/prompts/nexus/learning.md
      editable: true   # User can customize, includes user profile & learning log
      order: 4
```

**Fields**:
-   `content`: Actual prompt text (loaded from `.md` files during initialization)
-   `editable`: Whether user can modify this prompt (only `learning` is editable)
-   `order`: Concatenation sequence for final system prompt composition

**Prompt Loading**:
```python
# In scripts/database_manager.py
def load_prompt_files(prompts_dir: Path) -> Dict[str, str]:
    prompts = {}
    for prompt_name in ['field', 'presence', 'capabilities', 'learning']:
        file_path = prompts_dir / f"{prompt_name}.md"
        if file_path.exists():
            prompts[prompt_name] = file_path.read_text(encoding='utf-8')
    return prompts
```

**User Override Mechanism**:
Users can override `learning` via `POST /api/v1/prompts` or it can be updated by the Memory Agent:
```python
# Stored in identities collection:
{
  "public_key": "0x...",
  "prompt_overrides": {
    "learning": "用户档案：我是一个创意写作助手..."
  }
}

# Effective prompts preserve metadata:
{
  "learning": {
    "content": "用户档案：我是一个创意写作助手...",  # User's override
    "editable": true,    # From user_defaults
    "order": 4           # From user_defaults
  }
}
```

---

## VII. UI Section

Metadata for frontend rendering (tells UI what's editable and how to display it).

### Editable Fields

List of configuration paths that users can modify.

```yaml
ui:
  editable_fields:
    - "config.model"
    - "config.temperature"
    - "config.max_tokens"
    - "config.history_context_size"
    - "prompts.learning"
```

**Usage**:
-   Frontend uses this to determine which fields to show edit controls for
-   Only fields in this list can be modified via `POST /config` or `POST /prompts`
-   Dot notation: `"config.model"` → `user_defaults.config.model`

### Field Options

UI rendering metadata for each editable field.

```yaml
ui:
  field_options:
    "config.model":
      type: "select"
      # Options are dynamically generated from llm.catalog.*.aliases
      options: ["Gemini-2.5-Flash", "DeepSeek-Chat", "Kimi-K2"]
    
    "config.temperature":
      type: "slider"
      min: 0.0
      max: 2.0
      step: 0.1
    
    "config.max_tokens":
      type: "slider"
      min: 1024
      max: 8192
      step: 1024
    
    "config.history_context_size":
      type: "slider"
      min: 10
      max: 50
      step: 10
```

**Field Types**:
-   `select`: Dropdown menu (with `options` list)
-   `slider`: Range input (with `min`, `max`, `step`)

**Dynamic Model Options**:
The `config.model.options` array is dynamically populated from `llm.catalog.*.aliases` when serving `GET /api/v1/config`. This ensures UI always shows currently available models without code changes.

---

## VIII. Example Complete Configuration

```yaml
environment: "development"

system:
  log_level: "INFO"
  max_tool_iterations: 5
  tool_execution_timeout: 20
  app_name: "YX Nexus"

server:
  host: "0.0.0.0"
  port: 8000

security:
  signature_required_commands:
    - "identity"
    - "config"
    - "prompt"

llm:
  providers:
    google:
      api_key: "${GEMINI_API_KEY}"
      base_url: "https://generativelanguage.googleapis.com/v1beta"
    deepseek:
      api_key: "${DEEPSEEK_API_KEY}"
      base_url: "https://api.deepseek.com/v1"

  catalog:
    gemini-2.5-flash:
      provider: google
      id: gemini-2.5-flash
      aliases: ["Gemini-2.5-Flash"]
      default_params:
        temperature: 0.7
        max_tokens: 8192
    
    deepseek-chat:
      provider: deepseek
      id: deepseek-chat
      aliases: ["DeepSeek-Chat"]
      default_params:
        temperature: 0.9
        max_tokens: 8192

user_defaults:
  config:
    model: "gemini-2.5-flash"
    temperature: 0.8
    max_tokens: 4096
    history_context_size: 20
  
  prompts:
    field:
      content: ""  # Loaded from nexus/prompts/nexus/field.md
      editable: false
      order: 1
    presence:
      content: ""  # Loaded from nexus/prompts/nexus/presence.md
      editable: false
      order: 2
    capabilities:
      content: ""  # Loaded from nexus/prompts/nexus/capabilities.md
      editable: false
      order: 3
    learning:
      content: ""  # Loaded from nexus/prompts/nexus/learning.md
      editable: true
      order: 4

ui:
  editable_fields:
    - "config.model"
    - "config.temperature"
    - "config.max_tokens"
    - "config.history_context_size"
    - "prompts.learning"
  
  field_options:
    "config.model":
      type: "select"
      options: ["Gemini-2.5-Flash", "DeepSeek-Chat"]
    "config.temperature":
      type: "slider"
      min: 0.0
      max: 2.0
      step: 0.1
    "config.max_tokens":
      type: "slider"
      min: 1024
      max: 8192
      step: 1024
    "config.history_context_size":
      type: "slider"
      min: 10
      max: 50
      step: 10
```

---

## IX. Configuration Initialization

### Using database_manager.py

```bash
python scripts/database_manager.py

# Select option: Initialize configurations
# Choose environment: development / production / all
```

The script will:
1. Load prompt files from `nexus/prompts/nexus/`
2. Populate `user_defaults.prompts.*.content`
3. Substitute environment variables in `llm.providers.*.api_key`
4. Insert/update document in `configurations` collection

### MongoDB Query

To view current configuration:

```javascript
// In MongoDB shell
use NEXUS_DB_DEV
db.configurations.findOne({ environment: "development" })
```

---

## X. Configuration Composition Flow

```
┌─────────────────────────┐
│ configurations          │
│ {environment: "dev"}    │──┐
└─────────────────────────┘  │
                             │ ConfigService.get_genesis_template()
                             ↓
                    ┌────────────────┐
                    │ Genesis        │
                    │ Template       │
                    └────────┬───────┘
                             │
                             │ user_defaults.config
                             │ user_defaults.prompts
                             ↓
┌─────────────────────────┐   ┌────────────────┐
│ identities              │   │ IdentityService│
│ {public_key: "0x..."}   │──→│ .get_effective │
│  config_overrides: {}   │   │ _profile()     │
│  prompt_overrides: {}   │   └────────┬───────┘
└─────────────────────────┘            │
                                       │ Merge
                                       ↓
                            ┌──────────────────┐
                            │ Effective Config │
                            │ {model, temp...} │
                            └──────────────────┘
                                       │
                                       ↓
                            ┌──────────────────┐
                            │ REST API         │
                            │ GET /config      │
                            └──────────────────┘
```

**Key Principle**: Inheritance-and-Override
-   System provides defaults via `user_defaults`
-   Users store only overrides in `identities` collection
-   Effective configuration = defaults + overrides
-   Changes to defaults apply to all users (unless overridden)

---

## XI. Environment Variable Substitution

Configuration values can reference environment variables using `${VAR_NAME}` syntax:

```yaml
llm:
  providers:
    google:
      api_key: "${GEMINI_API_KEY}"  # Loaded from .env file
```

**Substitution Logic** (in `ConfigService`):
```python
def _substitute_env_vars(self, value: Any) -> Any:
    if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
        var_name = value[2:-1]
        return os.getenv(var_name, value)
    return value
```

**Best Practices**:
-   Never commit API keys to version control
-   Use `.env` file for local development
-   Use environment variables in production deployments

---

## XII. Validation and Constraints

### Required Fields

-   `environment`: Must be "development" or "production"
-   `user_defaults.config.model`: Must exist in `llm.catalog`
-   `ui.editable_fields`: Must reference valid paths in `user_defaults`

### Type Constraints

-   `system.max_tool_iterations`: Positive integer
-   `system.tool_execution_timeout`: Positive number (seconds)
-   `llm.catalog.*.aliases`: Non-empty array of strings
-   `ui.field_options.*.min/max/step`: Numeric types

### Semantic Constraints

-   `ui.field_options` keys must be subset of `ui.editable_fields`
-   `user_defaults.prompts.*.order`: Unique positive integers
-   `llm.catalog.*.provider`: Must reference key in `llm.providers`

---

## XIII. Migration and Versioning

When updating the configuration schema:

1. **Add New Fields**: Safe, existing documents remain valid
2. **Remove Fields**: Requires migration script to clean up old documents
3. **Rename Fields**: Requires migration + code update in `ConfigService`

**Example Migration** (adding new field):
```javascript
// MongoDB shell
db.configurations.updateMany(
  {},
  { $set: { "system.new_field": "default_value" } }
)
```

**Versioning Strategy**:
-   Configuration schema version is not explicitly stored
-   Schema changes are tracked via git commits to `config.example.yml`
-   Production deployments should run migration scripts before code updates
