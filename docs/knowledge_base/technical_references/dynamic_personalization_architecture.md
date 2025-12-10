# Dynamic Personalization Architecture

## Overview

This document provides comprehensive technical documentation for the **Dynamic Personalization System** implemented in NEXUS. This system enables per-user configuration and prompt customization through an inheritance-and-override architecture, allowing each identity to have personalized AI behavior while maintaining a centralized default configuration ("Genesis Template").

**Key Capabilities:**
- Per-user AI model selection (e.g., user A uses GPT-4, user B uses Gemini)
- Per-user prompt customization (personalized AI personas)
- Per-user runtime parameter overrides (temperature, max_tokens, etc.)
- Dynamic LLM provider instantiation based on user preferences
- Zero-configuration defaults for new users

**Last Updated:** 2025-10-11  
**Version:** 1.0

---

## Architecture Context

### Position in NEXUS Ecosystem

The Dynamic Personalization System sits at the intersection of three major subsystems:

```
┌─────────────────────────────────────────────────────────────┐
│                    NEXUS Backend Core                        │
│                                                               │
│  ┌──────────────┐      ┌──────────────┐      ┌───────────┐ │
│  │IdentityService│ ───▶│ ConfigService│◀────│Database   │ │
│  └──────┬───────┘      └──────┬───────┘      │(MongoDB)  │ │
│         │                     │               └───────────┘ │
│         │ user_profile        │ genesis_template            │
│         ▼                     ▼                              │
│  ┌──────────────────────────────────────┐                   │
│  │      OrchestratorService             │                   │
│  │  (Injects user_profile into Run)     │                   │
│  └──────┬─────────────────────┬─────────┘                   │
│         │                     │                              │
│         ▼                     ▼                              │
│  ┌──────────────┐      ┌──────────────┐                     │
│  │ContextBuilder│      │  LLMService  │                     │
│  │(Multi-msg)   │      │(Provider sel)│                     │
│  └──────────────┘      └──────────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

### Core Principles

1. **Inheritance-and-Override:** Every user inherits from a centralized "Genesis Template" and can selectively override specific aspects
2. **Database as Truth:** The `configurations` collection in MongoDB is the authoritative source for all defaults
3. **Runtime Composition:** User-specific configs are merged at request time, not pre-computed
4. **Lazy Provider Instantiation:** LLM providers are created on-demand based on user's model choice

---

## Detailed Breakdown

### 1. Data Model

#### 1.1 Collections Structure

**`configurations` Collection:**
```javascript
{
  "environment": "development",  // or "production"
  "system": {
    "log_level": "INFO",
    "max_tool_iterations": 5,
    "app_name": "NEXUS"
  },
  "security": {
    "signature_required_commands": ["identity", "config.set", "prompt.set"]
  },
  "llm": {
    "providers": {
      "google": {
        "api_key": "${GEMINI_API_KEY}",
        "base_url": "https://generativelanguage.googleapis.com/v1beta"
      },
      "deepseek": { /* ... */ },
      "openrouter": { /* ... */ }
    },
    "catalog": {
      "gemini-2.5-flash": {
        "provider": "google",
        "id": "gemini-2.5-flash",
        "aliases": ["Gemini-2.5-Flash"],
        "default_params": {
          "temperature": 0.7,
          "max_tokens": 8192
        }
      },
      // ... other models
    }
  },
  "user_defaults": {
    "config": {
      "model": "gemini-2.5-flash",
      "temperature": 0.8,
      "max_tokens": 4096,
      "history_context_size": 20
    },
    "prompts": {
      "friends_profile": {
        "content": "",  // User profile and preferences
        "editable": true,
        "description": "About this friend - preferences, patterns, and context"
      }
      // Note: CORE_IDENTITY is now defined in code (nexus/services/context/prompts.py)
      // [CAPABILITIES] is dynamically generated from ToolRegistry
      // [SHARED_MEMORY] is fetched from messages collection
      // [THIS_MOMENT] is constructed from current input
    }
  },
  "ui": {
    "editable_fields": [
      "config.model",
      "config.temperature",
      "config.max_tokens",
      "config.history_context_size",
      "prompts.friends_profile"  // User profile for [FRIENDS_INFO] block
    ],
    "field_options": { /* UI metadata */ }
  }
}
```

**`identities` Collection:**
```javascript
{
  "public_key": "0x...",
  "created_at": ISODate("2025-10-11T..."),
  "metadata": {},
  "config_overrides": {
    // Optional: user-specific config overrides
    "model": "deepseek-chat",
    "temperature": 0.9
  },
  "prompt_overrides": {
    // Optional: user-specific prompt overrides
    // friends_profile: user profile and preferences for [FRIENDS_INFO] block
    "friends_profile": "I prefer concise answers. Interested in AI ethics."
    // Legacy: "learning" field still supported for backward compatibility
  }
}
```

**`messages` Collection:**
```javascript
{
  "id": "msg_...",
  "run_id": "run_...",
  "owner_key": "0x...",  // ✅ Required
  // NO session_id field
  "role": "human" | "ai" | "tool" | "system",
  "content": "...",
  "timestamp": ISODate("..."),
  "metadata": {}
}
```

#### 1.2 Database Initialization

**Script:** `scripts/database_manager.py --init-config`

**Purpose:** One-time initialization of the `configurations` collection

**Key Features:**
- Reads prompt files from `nexus/prompts/nexus/*.md`
- Constructs complete configuration document based on `config.example.yml` structure
- Supports idempotent operations (can be re-run safely)
- Environment-specific (`--environment development` or `production`)

**Usage:**
```bash
python scripts/database_manager.py --init-config --environment development
```

---

### 2. Core Services Architecture

#### 2.1 ConfigService

**File:** `nexus/services/config.py`

**Role:** The "Genesis Template" provider - serves as the centralized source of default configurations

**New Methods (Added in this refactor):**

```python
def get_genesis_template(self) -> Dict[str, Any]:
    """Return the complete configuration loaded from database.
    
    This is the authoritative source for all default values.
    Downstream services use this for inheritance-and-override composition.
    """
    return copy.deepcopy(self._config)

def get_user_defaults(self) -> Dict:
    """Get default user configuration (config + prompts).
    
    Returns:
        {
            "config": {"model": "...", "temperature": 0.8, ...},
            "prompts": {"field": {...}, "presence": {...}, "capabilities": {...}, "learning": {...}}
        }
    """
    return self.get("user_defaults", {})

def get_llm_catalog(self) -> Dict[str, Dict]:
    """Get LLM model catalog (model name -> provider mapping).
    
    Returns:
        {
            "gemini-2.5-flash": {"provider": "google", "id": "...", ...},
            "deepseek-chat": {"provider": "deepseek", "id": "...", ...},
            ...
        }
    """
    return self.get("llm.catalog", {})

def get_provider_config(self, provider_name: str) -> Dict:
    """Get configuration for a specific LLM provider.
    
    Args:
        provider_name: "google", "deepseek", "openrouter", etc.
        
    Returns:
        {"api_key": "...", "base_url": "...", ...}
    """
    return self.get(f"llm.providers.{provider_name}", {})
```

**Fallback Configuration:**

The hardcoded fallback in `_load_minimal_default_config()` was **significantly simplified**:

- **Old:** 121 lines with full config replication
- **New:** 47 lines with absolute minimum to prevent crashes
- **Philosophy:** Database is truth; fallback is emergency-only

```python
# Minimal emergency fallback
self._config = {
    "system": {"log_level": "INFO", "max_tool_iterations": 5},
    "database": {"mongo_uri": "${MONGO_URI}", "db_name": db_name},
    "llm": {
        "providers": {"google": {...}},
        "catalog": {"gemini-2.5-flash": {...}}
    },
    "user_defaults": {
        "config": {"model": "gemini-2.5-flash", ...},
        "prompts": {}
    }
}
```

---

#### 2.2 IdentityService

**File:** `nexus/services/identity.py`

**Role:** User identity and personalization settings manager

**New Methods (Added in this refactor):**

```python
async def get_user_profile(self, public_key: str) -> Dict[str, Any]:
    """Retrieve user's complete personalization profile.
    
    Returns:
        {
            "public_key": "0x...",
            "config_overrides": {},  # User's config overrides
            "prompt_overrides": {},  # User's prompt overrides
            "created_at": datetime
        }
    """
    identity = await self.get_identity(public_key)
    if not identity:
        return {
            'public_key': public_key,
            'config_overrides': {},
            'prompt_overrides': {},
            'created_at': None
        }
    
    return {
        'public_key': identity['public_key'],
        'config_overrides': identity.get('config_overrides', {}),
        'prompt_overrides': identity.get('prompt_overrides', {}),
        'created_at': identity.get('created_at')
    }

async def update_user_config(
    self, 
    public_key: str, 
    config_overrides: Dict[str, Any]
) -> bool:
    """Update user's configuration overrides (model, temperature, etc.)."""
    return await asyncio.to_thread(
        self.db_service.provider.update_identity_field,
        public_key,
        'config_overrides',
        config_overrides
    )

async def update_user_prompts(
    self, 
    public_key: str, 
    prompt_overrides: Dict[str, str]
) -> bool:
    """Update user's prompt overrides (currently only 'learning' is user-editable)."""
    return await asyncio.to_thread(
        self.db_service.provider.update_identity_field,
        public_key,
        'prompt_overrides',
        prompt_overrides
    )
```

**Identity Creation:**

When a new identity is created via `/identity` command, it now includes **empty override fields**:

```python
identity_data = {
    'public_key': public_key,
    'created_at': datetime.now(timezone.utc),
    'metadata': metadata or {},
    'config_overrides': {},  # ✅ Added
    'prompt_overrides': {}   # ✅ Added
}
```

---

#### 2.3 OrchestratorService

**File:** `nexus/services/orchestrator.py`

**Role:** Request coordinator and identity gatekeeper

**Key Changes:**

**User Profile Injection:**

After identity verification, Orchestrator builds and injects `user_profile` into `Run.metadata`:

```python
# In handle_new_run()
if self.identity_service:
    identity = await self.identity_service.get_identity(run.owner_key)
    
    if identity is None:
        # Visitor flow: send guidance, halt processing
        # (No changes to persistence or LLM flow)
        return
    
    # Member flow: build user_profile
    user_profile = {
        'public_key': identity['public_key'],
        'config_overrides': identity.get('config_overrides', {}),
        'prompt_overrides': identity.get('prompt_overrides', {}),
        'created_at': identity.get('created_at'),
    }
    
    # Inject into Run.metadata
    if run.metadata is None:
        run.metadata = {}
    run.metadata['user_profile'] = user_profile
```

**TODO for Future Optimization:**

```python
# TODO: Refactor with unified RunContext object
#   Current approach passes user_profile through Run.metadata -> ContextService -> LLMService
#   Future: Create a RunContext object that encapsulates run, user_profile, and metadata
#   to simplify the data passing chain and reduce coupling.
# See docs/future_roadmap.md for more details.
```

---

#### 2.4 ContextService

**File:** `nexus/services/context.py`

**Role:** Dynamic prompt composition engine

**Core Functionality: Prompt Merging**

```python
def _compose_effective_prompts(self, user_profile: Dict) -> Dict[str, str]:
    """Compose effective prompts by merging defaults with user overrides.
    
    Merge Strategy:
        effective_prompts = genesis_template.prompts ⊕ user_profile.prompt_overrides
        where ⊕ means "override takes precedence"
    
    Args:
        user_profile: User profile containing prompt_overrides
        
    Returns:
        {
            'field': <effective_field_content>,
            'presence': <effective_presence_content>,
            'capabilities': <effective_capabilities_content>,
            'learning': <effective_learning_content>
        }
    """
    # Step 1: Get default prompts from ConfigService (Genesis Template)
    user_defaults = self.config_service.get_user_defaults()
    default_prompts = user_defaults.get('prompts', {})
    
    # Step 2: Get user overrides
    prompt_overrides = user_profile.get('prompt_overrides', {})
    
    # Step 3: Merge (overrides take precedence)
    def get_prompt_content(prompt_value):
        if isinstance(prompt_value, dict):
            return prompt_value.get('content', '')
        return prompt_value if isinstance(prompt_value, str) else ''
    
    # Only 'learning' can be overridden by users; others are system-level
    effective_prompts = {
        'field': get_prompt_content(default_prompts.get('field', '')),
        'presence': get_prompt_content(default_prompts.get('presence', '')),
        'capabilities': get_prompt_content(default_prompts.get('capabilities', '')),
        'learning': prompt_overrides.get('learning', get_prompt_content(default_prompts.get('learning', '')))
    }
    
    logger.info(f"Composed effective prompts with overrides: {list(prompt_overrides.keys())}")
    return effective_prompts

def _build_system_prompt_from_prompts(self, prompts: Dict[str, str]) -> str:
    """Build complete system prompt from prompts dictionary.
    
    New 4-layer architecture concatenation order:
        system_prompt = field + "\n\n---\n\n" + presence + "\n\n---\n\n" + capabilities + "\n\n---\n\n" + learning
    """
    parts = []
    for key in ['field', 'presence', 'capabilities', 'learning']:  # Order matters
        content = prompts.get(key, '').strip()
        if content:
            parts.append(content)
    
    return CONTENT_SEPARATOR.join(parts) if parts else FALLBACK_SYSTEM_PROMPT
```

**Example Scenarios:**

**Scenario A: New User (No Overrides)**
```python
# user_profile.prompt_overrides = {}
# Result: Uses all default prompts from Genesis Template

effective_prompts = {
    'field': <content from nexus/prompts/nexus/field.md>,
    'presence': <content from nexus/prompts/nexus/presence.md>,
    'capabilities': <content from nexus/prompts/nexus/capabilities.md>,
    'learning': <content from nexus/prompts/nexus/learning.md>  # Default template
}
```

**Scenario B: User with Personalized Learning**
```python
# user_profile.prompt_overrides = {"learning": "用户档案内容..."}
# Result: System defaults + personalized learning profile

effective_prompts = {
    'field': <content from nexus/prompts/nexus/field.md>,            # Default (system-level)
    'presence': <content from nexus/prompts/nexus/presence.md>,      # Default (system-level)
    'capabilities': <content from nexus/prompts/nexus/capabilities.md>,  # Default (system-level)
    'learning': "用户档案内容..."  # ✅ Overridden (user's personalized profile, updated by Memory Agent)
}
```

---

#### 2.5 LLMService

**File:** `nexus/services/llm/service.py`

**Role:** Dynamic LLM provider orchestrator

**Core Functionality: Configuration Composition**

```python
def _compose_effective_config(self, user_profile: Dict) -> Dict:
    """Compose effective LLM configuration by merging defaults with user overrides.
    
    Merge Strategy:
        effective_config = genesis_template.user_defaults.config ⊕ user_profile.config_overrides
    
    Args:
        user_profile: User profile containing config_overrides
        
    Returns:
        {
            'model': <effective_model>,
            'temperature': <effective_temperature>,
            'max_tokens': <effective_max_tokens>
        }
    """
    # Step 1: Get default configuration from ConfigService
    user_defaults = self.config_service.get_user_defaults()
    default_config = user_defaults.get('config', {})
    
    # Step 2: Get user overrides
    config_overrides = user_profile.get('config_overrides', {})
    
    # Step 3: Merge (overrides take precedence)
    effective_config = {
        'model': config_overrides.get('model', default_config.get('model', 'gemini-2.5-flash')),
        'temperature': config_overrides.get('temperature', default_config.get('temperature', 0.7)),
        'max_tokens': config_overrides.get('max_tokens', default_config.get('max_tokens', 4096))
    }
    
    logger.info(f"Composed effective config with overrides: {list(config_overrides.keys())}")
    return effective_config
```

**Core Functionality: Dynamic Provider Selection**

```python
def _get_provider_for_model(self, model_name: str):
    """Dynamically instantiate the appropriate provider for a given model.
    
    Resolution Process:
        1. Look up model in LLM catalog (ConfigService.get_llm_catalog())
        2. Get provider name from catalog entry
        3. Get provider configuration (API key, base URL)
        4. Instantiate provider class (GoogleLLMProvider, DeepSeekLLMProvider, etc.)
    
    Args:
        model_name: Name of the model (e.g., "gemini-2.5-flash", "deepseek-chat")
        
    Returns:
        Instance of LLMProvider (GoogleLLMProvider, DeepSeekLLMProvider, OpenRouterLLMProvider)
    """
    # Step 1: Get model catalog
    catalog = self.config_service.get_llm_catalog()
    
    # Step 2: Check if model exists in catalog
    if model_name not in catalog:
        logger.warning(f"Model '{model_name}' not in catalog, falling back to default")
        user_defaults = self.config_service.get_user_defaults()
        model_name = user_defaults.get('config', {}).get('model', 'gemini-2.5-flash')
    
    # Step 3: Get provider name
    provider_name = catalog.get(model_name, {}).get('provider', 'google')
    logger.info(f"Using provider: {provider_name} for model: {model_name}")
    
    # Step 4: Get provider configuration
    provider_config = self.config_service.get_provider_config(provider_name)
    
    if not provider_config:
        raise ValueError(f"No configuration found for provider: {provider_name}")
    
    # Step 5: Instantiate provider
    if provider_name == "google":
        return GoogleLLMProvider(
            api_key=provider_config['api_key'],
            base_url=provider_config['base_url'],
            model=catalog.get(model_name, {}).get('id', model_name),
            timeout=timeout
        )
    elif provider_name == "deepseek":
        return DeepSeekLLMProvider(...)
    elif provider_name == "openrouter":
        return OpenRouterLLMProvider(...)
    else:
        raise ValueError(f"Unsupported provider: {provider_name}")
```

**Example Scenarios:**

**Scenario A: User with Default Model**
```python
# user_profile.config_overrides = {}
# effective_config.model = "gemini-2.5-flash" (from Genesis Template)
# Result: GoogleLLMProvider instance
```

**Scenario B: User with Custom Model**
```python
# user_profile.config_overrides = {"model": "deepseek-chat"}
# effective_config.model = "deepseek-chat" (overridden)
# Result: DeepSeekLLMProvider instance
```

**Key Insight:** Providers are **lazily instantiated** per request, not pre-created at startup. This enables true per-user model selection.

---

#### 2.6 PersistenceService

**File:** `nexus/services/persistence.py`

**Role:** Message persistence with identity-aware filtering

**Critical Architecture Change:**

**Problem Identified:**
- `PersistenceService` previously subscribed to `Topics.RUNS_NEW` in parallel with `OrchestratorService`
- Even though Orchestrator blocked visitors, Persistence would still receive and save visitor messages
- Redundant identity checking created performance overhead

**Solution:**
- **Event Subscription Change:**
  - ❌ Old: `Topics.RUNS_NEW` → `handle_new_run()`
  - ✅ New: `Topics.CONTEXT_BUILD_REQUEST` → `handle_context_build_request()`

- **Flow:**
  ```
  RUNS_NEW
    └─> OrchestratorService.handle_new_run()
          ├─> Visitor: Send guidance, STOP (no further events)
          └─> Member: Publish CONTEXT_BUILD_REQUEST
                └─> PersistenceService.handle_context_build_request()
                      └─> Save message
  ```

**Removed Code:**
```python
# ❌ Removed redundant identity check
if self.identity_service:
    identity = await self.identity_service.get_identity(message.owner_key)
    if identity is None:
        logger.info(f"Skipping persistence for visitor")
        return
```

**Added Comment:**
```python
# Trust OrchestratorService gatekeeper - if we received this message, user is a verified member
# No identity check needed here as Orchestrator already validated member status
```

**Dependency Injection Simplified:**
```python
# Old
def __init__(self, database_service: DatabaseService, identity_service: IdentityService | None = None):
    self.database_service = database_service
    self.identity_service = identity_service

# New
def __init__(self, database_service: DatabaseService):
    self.database_service = database_service
```

---

### 3. Database Layer Changes

#### 3.1 MongoProvider Unification

**File:** `nexus/services/database/providers/mongo.py`

**Change:** Unified configuration document structure (removed `config_data` wrapper support)

**Old Implementation (Dual Structure Support):**
```python
def get_configuration(self, environment: str):
    config_doc = self.config_collection.find_one({"environment": environment})
    
    if config_doc:
        # Support both wrapped (config_data) and direct structure
        if "config_data" in config_doc:
            config_data = config_doc["config_data"]  # Wrapped
        else:
            config_data = dict(config_doc)  # Direct
            config_data.pop("_id", None)
            config_data.pop("environment", None)
        return config_data
```

**New Implementation (Direct Structure Only):**
```python
def get_configuration(self, environment: str):
    config_doc = self.config_collection.find_one({"environment": environment})
    
    if config_doc:
        # Use direct structure only - configuration fields are stored at top level
        config_data = dict(config_doc)
        config_data.pop("_id", None)
        config_data.pop("environment", None)
        return config_data
```

**Upsert Method Change:**
```python
# Old: update_one with $set wrapper
def upsert_configuration(self, environment: str, config_data: Dict):
    result = self.config_collection.update_one(
        {"environment": environment},
        {"$set": {"config_data": config_data}},  # ❌ Wrapped
        upsert=True
    )

# New: replace_one with direct structure
def upsert_configuration(self, environment: str, config_data: Dict):
    document = {"environment": environment}
    document.update(config_data)  # ✅ Direct merge
    
    result = self.config_collection.replace_one(
        {"environment": environment},
        document,
        upsert=True
    )
```

**Rationale:** Eliminates architectural ambiguity, simplifies queries, reduces code complexity.

---

## Integration Points

### 4.1 End-to-End Flow: Member with Personalization

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. User Sends Message                                           │
│    - public_key: 0x_YU                                          │
│    - content: "Hello"                                            │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. OrchestratorService.handle_new_run()                         │
│    ├─> identity_service.get_identity("0x_YU")                   │
│    │     └─> Returns: {config_overrides: {model: "deepseek"}, │
│    │                   prompt_overrides: {learning: "档案..."}}  │
│    ├─> Build user_profile                                       │
│    └─> Inject into Run.metadata['user_profile']                 │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼ Publish CONTEXT_BUILD_REQUEST
┌─────────────────────────────────────────────────────────────────┐
│ 3. ContextService.handle_build_request()                        │
│    ├─> Extract user_profile from Run.metadata                   │
│    ├─> config_service.get_user_defaults()                       │
│    │     └─> Returns genesis template prompts                   │
│    ├─> _compose_effective_prompts(user_profile)                │
│    │     └─> Merges: default + user overrides                   │
│    │         Result: {field: <default>, presence: <default>,    │
│    │                  capabilities: <default>, learning: "档案"}│
│    └─> _build_system_prompt_from_prompts()                     │
│          └─> Concatenates: field + presence + capabilities + learning│
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼ Publish CONTEXT_BUILD_RESPONSE
┌─────────────────────────────────────────────────────────────────┐
│ 4. OrchestratorService.handle_context_ready()                   │
│    └─> Publish LLM_REQUESTS (with user_profile in content)      │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. LLMService.handle_llm_request()                              │
│    ├─> Extract user_profile from message.content                │
│    ├─> _compose_effective_config(user_profile)                 │
│    │     └─> Merges: default config + user overrides            │
│    │         Result: {model: "deepseek", temperature: 0.8, ...} │
│    ├─> _get_provider_for_model("deepseek")                     │
│    │     ├─> config_service.get_llm_catalog()                   │
│    │     │     └─> {"deepseek-chat": {provider: "deepseek"}}   │
│    │     ├─> config_service.get_provider_config("deepseek")    │
│    │     │     └─> {api_key: "...", base_url: "..."}           │
│    │     └─> Instantiate DeepSeekLLMProvider                    │
│    └─> provider.chat_completion(...)                           │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Visitor Flow (No Personalization)

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Visitor Sends Message                                        │
│    - public_key: 0x_GUEST                                       │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. OrchestratorService.handle_new_run()                         │
│    ├─> identity_service.get_identity("0x_GUEST")                │
│    │     └─> Returns: None                                       │
│    ├─> Publish UI_EVENTS (guidance message)                     │
│    └─> RETURN (halt processing)                                 │
└─────────────────────────────────────────────────────────────────┘
                        │
                        ✗ No further events
                        ✗ PersistenceService NOT triggered
                        ✗ ContextService NOT triggered
                        ✗ LLMService NOT triggered
```

**Key Difference:** By subscribing PersistenceService to `CONTEXT_BUILD_REQUEST` instead of `RUNS_NEW`, visitor messages are **automatically excluded** from persistence without redundant checks.

---

## Environment-Specific Behavior

### Local Development

**Database:** `NEXUS_DB_DEV`

**Initialization:**
```bash
python scripts/database_manager.py --init-config --environment development
```

**Fallback Behavior:**
- If database is unavailable, ConfigService loads minimal emergency fallback
- Warning logged: "Loading minimal emergency fallback configuration"
- System remains functional but without full feature set

### Production

**Database:** `NEXUS_DB_PROD`

**Initialization:**
```bash
python scripts/database_manager.py --init-config --environment production
```

**Critical Requirement:** Database must be properly initialized; fallback is **not suitable** for production use.

---

## Configuration Examples

### Example 1: Adding a New LLM Model

**1. Update `config.example.yml` (documentation):**
```yaml
llm:
  providers:
    anthropic:  # New provider
      api_key: "${ANTHROPIC_API_KEY}"
      base_url: "https://api.anthropic.com"
  
  catalog:
    claude-3-opus:  # New model
      provider: anthropic
      id: claude-3-opus-20240229
      aliases: ["Claude-3-Opus"]
      default_params:
        temperature: 0.7
        max_tokens: 4096
```

**2. Update `config.example.yml` and re-run initialization:**
```python
"llm": {
    "providers": {
        # ... existing providers ...
        "anthropic": {
            "api_key": "${ANTHROPIC_API_KEY}",
            "base_url": "https://api.anthropic.com"
        }
    },
    "catalog": {
        # ... existing models ...
        "claude-3-opus": {
            "provider": "anthropic",
            "id": "claude-3-opus-20240229",
            "aliases": ["Claude-3-Opus"],
            "default_params": {
                "temperature": 0.7,
                "max_tokens": 4096
            }
        }
    }
}
```

**3. Implement `AnthropicLLMProvider` in `nexus/services/llm/providers/anthropic.py`:**
```python
class AnthropicLLMProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str, model: str, timeout: int = 30):
        # ... implementation
```

**4. Update `LLMService._get_provider_for_model()`:**
```python
elif provider_name == "anthropic":
    return AnthropicLLMProvider(
        api_key=provider_config['api_key'],
        base_url=provider_config['base_url'],
        model=catalog.get(model_name, {}).get('id', model_name),
        timeout=timeout
    )
```

**5. Re-run database initialization:**
```bash
python scripts/database_manager.py --init-config --environment development
```

**6. User can now select the new model:**
```javascript
// Via future /config command or direct database update
{
  "public_key": "0x_USER",
  "config_overrides": {
    "model": "claude-3-opus"
  }
}
```

### Example 2: User-Specific Learning Profile

**Scenario:** User's personalized learning profile is automatically built and updated

**Step 1: User executes `/identity` to create identity**

**Step 2: Memory Agent learns from conversations:**
- Every 20 turns of dialogue, Memory Agent analyzes conversation
- Extracts user preferences, patterns, background
- Generates/updates personalized `learning.md` content
- Saves to `prompt_overrides.learning`

**Step 3: User can also actively add memories:**
```bash
# Via /memory command
/memory "我喜欢简洁的代码示例"

# Or via /prompt panel (edit learning.md directly in UI)
```

**Step 4: User sends next message**

**Result:**
- ContextService merges: default field/presence/capabilities + personalized learning
- LLM receives system prompt with user's unique profile
- AI adapts behavior based on learned preferences
- Other users remain unaffected (each has their own learning profile)

---

## Common Issues and Troubleshooting

### Issue 1: Visitor Messages Being Persisted

**Symptom:** Messages from unregistered users appear in `messages` collection

**Diagnosis:**
```bash
# Check PersistenceService subscription
grep -n "subscribe.*RUNS_NEW" nexus/services/persistence.py

# Should return NO results
# Correct subscription should be:
grep -n "subscribe.*CONTEXT_BUILD_REQUEST" nexus/services/persistence.py
```

**Resolution:** Ensure PersistenceService subscribes to `CONTEXT_BUILD_REQUEST`, not `RUNS_NEW`

### Issue 2: User's Custom Model Not Being Used

**Symptom:** User has `config_overrides.model` set, but default model is still used

**Diagnosis Steps:**

**1. Verify identity document:**
```javascript
db.identities.findOne({ "public_key": "0x_USER" })
// Should contain: { "config_overrides": { "model": "deepseek-chat" } }
```

**2. Check Orchestrator logs:**
```
# Should see:
INFO | OrchestratorService | Injected user_profile into Run.metadata for owner_key=0x_USER
```

**3. Check LLMService logs:**
```
# Should see:
INFO | LLMService | Composed effective config with overrides: ['model']
INFO | LLMService | Using provider: deepseek for model: deepseek-chat
```

**Possible Causes:**
- Model name not in catalog → Check `llm.catalog` in database
- Provider not implemented → Implement provider class
- Typo in model name → Verify spelling matches catalog key exactly

### Issue 3: Configuration Not Loaded from Database

**Symptom:** Logs show "Loading minimal emergency fallback configuration"

**Diagnosis:**
```bash
# Test database connection
python scripts/database_manager.py --init-config --environment development

# Check if configuration exists
mongo --eval 'db.configurations.find({"environment": "development"}).pretty()'
```

**Resolution:**
1. Ensure MongoDB is running
2. Verify `MONGO_URI` in `.env`
3. Run initialization script if configuration doesn't exist
4. Restart NEXUS backend

### Issue 4: Prompt Overrides Not Taking Effect

**Symptom:** User's custom learning profile doesn't appear to affect AI behavior

**Diagnosis:**
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Check ContextService logs
# Should see:
DEBUG | ContextService | Composed effective prompts with overrides: ['learning']
```

**Possible Causes:**
- Override value is empty string → Verify database content
- Prompt structure mismatch → Ensure overrides are simple strings, not objects
- Caching issue → Restart backend to clear any cached configurations

---

## Testing Strategy

### Unit Tests

**Key Test Files:**
- `tests/nexus/unit/services/test_identity_service.py` - Identity CRUD operations
- `tests/nexus/unit/services/test_config_service.py` - Configuration loading and fallback
- `tests/nexus/unit/services/test_context_service.py` - Prompt composition logic
- `tests/nexus/unit/services/database/providers/test_mongo_provider.py` - Database operations

**Critical Test Cases Added:**

```python
# Test: Context composition with overrides
async def test_context_composition_with_overrides():
    run = Run(
        metadata={
            "user_profile": {
                "prompt_overrides": {
                    "learning": "用户档案内容..."
                }
            }
        }
    )
    # Should use custom learning profile + default field/presence/capabilities

# Test: LLM dynamic provider selection
async def test_dynamic_provider_selection():
    user_profile = {
        "config_overrides": {
            "model": "deepseek-chat"
        }
    }
    # Should instantiate DeepSeekLLMProvider
```

### Integration Tests

**Key Test Files:**
- `tests/nexus/integration/services/test_orchestrator_service.py` - User profile propagation
- `tests/nexus/integration/services/test_persistence_service.py` - Event subscription validation
- `tests/nexus/integration/services/test_context_service.py` - End-to-end prompt composition

**Run Full Test Suite:**
```bash
python -m pytest tests/ -v
# Should show: 243 passed
```

---

## Performance Considerations

### 1. Provider Instantiation

**Current:** Providers are instantiated per request

**Cost:** Minimal (constructor overhead only, no connection pooling)

**Benefit:** True per-user model selection without pre-allocating all possible providers

**Future Optimization:** Implement provider pooling if instantiation becomes a bottleneck

### 2. Configuration Caching

**Current:** ConfigService loads configuration once at startup, caches in memory

**Refresh Strategy:** Configuration changes require backend restart

**Future Enhancement:** Implement configuration reload endpoint for hot-reloading

### 3. Identity Lookups

**Current:** Every request triggers identity lookup in Orchestrator

**Optimization:** MongoDB indexes on `public_key` ensure fast lookups

**Query Pattern:**
```javascript
db.identities.find({ "public_key": "0x..." }).hint({ "public_key": 1 })
// Uses unique index, O(log n) complexity
```

---

## Migration Guide

### Migrating from Pre-Personalization System

**If you have existing `identities` documents without `config_overrides` and `prompt_overrides`:**

**Migration Script:**
```javascript
// Run in MongoDB shell
db.identities.updateMany(
  { 
    $or: [
      { "config_overrides": { $exists: false } },
      { "prompt_overrides": { $exists: false } }
    ]
  },
  { 
    $set: {
      "config_overrides": {},
      "prompt_overrides": {}
    }
  }
)
```

**Verification:**
```javascript
db.identities.find({ 
  $or: [
    { "config_overrides": { $exists: false } },
    { "prompt_overrides": { $exists: false } }
  ]
}).count()
// Should return: 0
```

---

## References

### Related Documentation
- **Identity System:** `identity_and_data_sovereignty.md`
- **Architecture Overview:** `../../02_NEXUS_ARCHITECTURE.md`
- **Setup Guide:** `../../../developer_guides/01_SETUP_AND_RUN.md`
- **Future Roadmap:** `../../../future/Future_Roadmap.md`

### Key Files
- **Configuration Template:** `config.example.yml`
- **Initialization Script:** `scripts/database_manager.py --init-config`
- **Core Services:**
  - `nexus/services/config.py`
  - `nexus/services/identity.py`
  - `nexus/services/context.py`
  - `nexus/services/llm/service.py`
  - `nexus/services/orchestrator.py`
  - `nexus/services/persistence.py`

### External Resources
- **MongoDB Aggregation Pipeline:** https://docs.mongodb.com/manual/aggregation/
- **Pydantic Models:** https://docs.pydantic.dev/
- **AsyncIO Patterns:** https://docs.python.org/3/library/asyncio.html

---

## Appendix: Complete Configuration Schema

### Genesis Template Structure

```typescript
interface GenesisTemplate {
  environment: "development" | "production";
  
  system: {
    log_level: "DEBUG" | "INFO" | "WARNING" | "ERROR";
    max_tool_iterations: number;
    app_name: string;
  };
  
  security: {
    signature_required_commands: string[];
  };
  
  llm: {
    providers: {
      [providerName: string]: {
        api_key: string;  // Can use ${ENV_VAR} syntax
        base_url: string;
      };
    };
    catalog: {
      [modelName: string]: {
        provider: string;
        id: string;
        aliases?: string[];
        default_params?: {
          temperature?: number;
          max_tokens?: number;
        };
      };
    };
  };
  
  user_defaults: {
    config: {
      model: string;
      temperature: number;
      max_tokens: number;
      history_context_size: number;
    };
    prompts: {
      [promptKey: string]: {
        content: string;
        editable: boolean;
        order: number;
      };
    };
  };
  
  ui: {
    editable_fields: string[];
    field_options: {
      [fieldPath: string]: {
        type: "select" | "slider" | "text" | "textarea";
        options?: any[];
        min?: number;
        max?: number;
        step?: number;
      };
    };
  };
}
```

### Identity Document Schema

```typescript
interface Identity {
  _id: ObjectId;
  public_key: string;
  created_at: Date;
  metadata: Record<string, any>;
  
  config_overrides: {
    model?: string;
    temperature?: number;
    max_tokens?: number;
    history_context_size?: number;
    [key: string]: any;
  };
  
  prompt_overrides: {
    learning?: string;  // Only learning module is user-editable
    [key: string]: string;
  };
}
```

### User Profile Structure (Runtime)

```typescript
interface UserProfile {
  public_key: string;
  config_overrides: Record<string, any>;
  prompt_overrides: Record<string, string>;
  created_at: Date | null;
}
```

---

## 12. REST API Integration

The Dynamic Personalization System exposes its configuration management capabilities through RESTful HTTP APIs, enabling frontend panels and external tools to read and modify user preferences.

### 12.1 API Endpoints Overview

| Endpoint | Method | Purpose | Authentication |
|----------|--------|---------|----------------|
| `/api/v1/config` | GET | Retrieve effective configuration | Bearer token |
| `/api/v1/config` | POST | Update configuration overrides | Bearer + Signature |
| `/api/v1/prompts` | GET | Retrieve effective prompts | Bearer token |
| `/api/v1/prompts` | POST | Update prompt overrides | Bearer + Signature |
| `/api/v1/messages` | GET | Retrieve message history | Bearer token |

**For complete API specifications, see:** [`docs/api_reference/03_REST_API.md`](../../api_reference/03_REST_API.md)

### 12.2 GET /api/v1/config

**Flow Integration**:
```
Client Request (Authorization: Bearer <owner_key>)
  ↓
rest.py: verify_bearer_token()
  ↓
IdentityService.get_effective_profile(owner_key, config_service)
  ↓
  │→ ConfigService.get_genesis_template()  # System defaults
  │→ IdentityService.get_user_profile()     # User overrides
  │→ Merge: effective = defaults + overrides
  │→ Dynamic: Generate model options from llm.catalog.*.aliases
  ↓
Response: {
  effective_config,
  effective_prompts: {
    field: {content, editable: false, order},
    presence: {content, editable: false, order},
    capabilities: {content, editable: false, order},
    learning: {content, editable: true, order}
  },
  user_overrides,
  editable_fields,
  field_options
}
```

**Key Features**:
-   **Dynamic Model Options**: `field_options.config.model.options` is auto-generated from `llm.catalog.*.aliases`
-   **Prompt Structure Preservation**: Returns `{content, editable, order}` for each prompt module
-   **UI Metadata**: Provides `editable_fields` and `field_options` for frontend rendering

**Code Implementation** (`nexus/services/identity.py`):
```python
async def get_effective_profile(self, public_key: str, config_service) -> Dict[str, Any]:
    # Step 1: Get defaults from genesis template
    user_defaults = config_service.get_user_defaults()
    default_config = user_defaults.get('config', {})
    default_prompts = user_defaults.get('prompts', {})
    
    # Step 2: Get user overrides
    user_profile = await self.get_user_profile(public_key)
    config_overrides = user_profile.get('config_overrides', {})
    prompt_overrides = user_profile.get('prompt_overrides', {})
    
    # Step 3: Merge config
    effective_config = {**default_config, **config_overrides}
    
    # Step 4: Compose prompts (preserve structure)
    effective_prompts = {}
    for key in ['field', 'presence', 'capabilities', 'learning']:
        default_prompt = default_prompts.get(key, {})
        if key in prompt_overrides:
            effective_prompts[key] = {
                'content': prompt_overrides[key],
                'editable': default_prompt.get('editable', False),
                'order': default_prompt.get('order', 0)
            }
        else:
            effective_prompts[key] = {
                'content': default_prompt.get('content', ''),
                'editable': default_prompt.get('editable', False),
                'order': default_prompt.get('order', 0)
            }
    
    # Step 5: Dynamic model options
    genesis_template = config_service.get_genesis_template()
    llm_catalog = genesis_template.get('llm', {}).get('catalog', {})
    model_aliases = []
    for model_key, model_meta in llm_catalog.items():
        aliases = model_meta.get('aliases', [])
        model_aliases.extend(aliases or [model_key])
    
    field_options = genesis_template.get('ui', {}).get('field_options', {}).copy()
    if 'config.model' in field_options:
        field_options['config.model']['options'] = sorted(set(model_aliases))
    
    return {
        'effective_config': effective_config,
        'effective_prompts': effective_prompts,
        'user_overrides': {
            'config_overrides': config_overrides,
            'prompt_overrides': prompt_overrides
        },
        'editable_fields': genesis_template.get('ui', {}).get('editable_fields', []),
        'field_options': field_options
    }
```

### 12.3 POST /api/v1/config

**Authentication Flow**:
```
Client Request:
{
  "overrides": {"model": "deepseek-chat", "temperature": 0.9},
  "auth": {"publicKey": "0x...", "signature": "0x..."}
}
Headers: Authorization: Bearer <owner_key>

  ↓
rest.py: verify_bearer_token() ✓
  ↓
rest.py: verify_request_signature() ✓
  │→ nexus.core.auth.verify_signature()
  │→ Signature = eth_sign(keccak256(JSON.stringify(requestBody)))
  │→ Verify publicKey matches recovered address
  ↓
IdentityService.update_user_config(owner_key, overrides)
  ↓
DatabaseService.update_identity_field('config_overrides', overrides)
  ↓
MongoDB: Update identities.config_overrides
  ↓
Response: {"status": "success"}
```

**Security Properties**:
1. **Bearer Token**: Identifies user (prevents cross-user writes)
2. **Cryptographic Signature**: Proves ownership of private key
3. **Payload Binding**: Signature covers entire request body (prevents tampering)

**Signature Generation** (Client-side):
```javascript
import { ethers } from 'ethers';

const requestBody = {
  overrides: { model: 'deepseek-chat' },
  auth: { publicKey: wallet.address, signature: '' }
};

const payload = JSON.stringify(requestBody, Object.keys(requestBody).sort());
const messageHash = ethers.utils.keccak256(ethers.utils.toUtf8Bytes(payload));
const signature = await wallet.signMessage(ethers.utils.arrayify(messageHash));

requestBody.auth.signature = signature;
```

### 12.4 Prompt Structure in REST API

The REST API returns prompts as structured objects (not flat strings):

```json
{
  "effective_prompts": {
    "field": {
      "content": "场域：共同成长的对话空间...",
      "editable": false,   // System-managed, not user-editable
      "order": 1           // Concatenation order in system prompt
      "description": "对话空间的本质、原则和氛围"
    },
    "presence": {
      "content": "在场方式：我如何存在于这个空间...",
      "editable": false,   // System-managed, not user-editable
      "order": 2,
      "description": "AI如何存在和行动于这个场域"
    },
    "capabilities": {
      "content": "能力与工具：我可以做什么...",
      "editable": false,   // System-managed, not user-editable
      "order": 3,
      "description": "具体的工具、系统架构和边界"
    },
    "learning": {
      "content": "用户档案与学习记录...",
      "editable": true,    // ✅ User can modify via POST /prompts or /memory command
      "order": 4,
      "description": "用户偏好定义 + AI学习反思记录"
    }
  }
}
```

**Design Rationale**:
-   **`editable` metadata**: Frontend knows which prompts to show edit controls for
-   **`order` metadata**: Ensures consistent prompt composition in `ContextService`
-   **Separation of concerns**: UI doesn't hardcode knowledge of editable prompts

**Prompt Composition** (`ContextService`):
```python
def _build_system_prompt_from_prompts(self, prompts: Dict[str, Dict]) -> str:
    # Sort by order field
    sorted_prompts = sorted(
        prompts.items(),
        key=lambda x: x[1].get('order', 0)
    )
    
    # Concatenate content
    contents = [p[1].get('content', '') for p in sorted_prompts]
    return CONTENT_SEPARATOR.join(filter(None, contents))
```

### 12.5 Integration with Command System

REST API commands are registered in the command registry:

**`nexus/commands/definition/config.py`**:
```python
COMMAND_DEFINITION = {
    "name": "config",
    "description": "View or modify some configuration (model, temperature, etc.)",
    "usage": "/config",
    "handler": "rest",                    # Indicates REST handler
    "requiresGUI": True,                  # Requires dedicated UI panel
    "restOptions": {
        "getEndpoint": "/api/v1/config",
        "postEndpoint": "/api/v1/config",
        "method": "GET"
    }
}
```

**Frontend Routing**:
```typescript
// In AURA frontend
const command = await fetch('/api/v1/commands').then(r => r.json())
  .find(c => c.name === 'config');

if (command.handler === 'rest') {
  // Open REST-based UI panel
  openConfigPanel(command.restOptions.getEndpoint);
} else {
  // Send WebSocket command
  ws.send({ type: 'user_message', content: '/config' });
}
```

### 12.6 REST API vs WebSocket

| Aspect | REST API | WebSocket |
|--------|----------|-----------|
| **Purpose** | Configuration management, historical data | Real-time chat interactions |
| **State** | Stateless (per-request auth) | Stateful (persistent connection) |
| **Data Flow** | Request-response | Bidirectional streaming |
| **Auth** | Bearer + Signature (for writes) | Session-based (owner_key in context) |
| **Use Cases** | `/config` panels, `/prompt` editor, history viewer | Chat messages, tool execution, AI responses |

**Shared Components**:
-   Both use `IdentityService` for user profile resolution
-   Both use `ConfigService` for defaults
-   Both store to same MongoDB collections
-   Both use public key as identity

### 12.7 Testing REST API Integration

**Manual Testing**:
```bash
# Start backend
python -m nexus.main

# Test with provided script
./scripts/test_data_commands.sh 0xYourPublicKey
```

**Unit Tests**:
```bash
# Test signature verification
pytest tests/nexus/unit/core/test_auth.py

# Test configuration composition
pytest tests/nexus/unit/services/test_identity_service.py -k effective_profile
```

**Integration Points to Verify**:
1. ✅ Bearer token extraction and validation
2. ✅ Signature verification with eth_keys
3. ✅ Configuration merging (defaults + overrides)
4. ✅ Prompt structure preservation
5. ✅ Dynamic model options generation
6. ✅ Database write atomicity

---

**Document Status:** ✅ Complete  
**Last Updated:** 2025-10-20 (Added Section 12: REST API Integration)  
**Maintenance:** Update this document when adding new personalization features, modifying the configuration composition logic, or extending the REST API.

