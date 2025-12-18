# LOGIC_MAP (Project Logic Map)

This file is the project-specific instance of `docs/rules/LOGIC_SCHEMA.md`.
It is both:

- a prompt for agents (task → nodes → anchors → code)
- a logic-first README for humans (flows + graph + invariants)

## How to use (agents)

1. Convert the user request into one or more candidate nodes:
   - `FLOW-*` if it is behavior/time-ordered
   - `CMP-*` if it is a module/subsystem
   - `INV-*` if it is a rule/constraint
2. Traverse `relations` to find adjacent nodes.
3. Follow `anchors` / `refs` into code/tests/config.
4. If the map is insufficient, improve the map (add anchors/edges) before broad scanning.

## How to read (humans)

1. `system` (what it is)
2. `flows` (how it behaves)
3. `components` (who owns responsibilities)
4. `relations` (how pieces connect)
5. `invariants` + `evidences` (constraints + proof)

```yaml
system:
  id: SYS-nexus
  title: NEXUS (backend) + AURA (frontend)
  purpose: "Event-driven AI assistant with HTTP+SSE streaming UI, tool calling, and identity-gated personalization."
  languages:
    - python
    - typescript
  entrypoints:
    - kind: command
      target: "poetry run python -m nexus.main"
      why: "Start FastAPI + NexusBus runtime (backend)."
    - kind: command
      target: "pnpm dev"
      why: "Start Vite dev server (frontend, run from ./aura)."
  key_configs:
    - kind: file
      target: ".env.example"
      why: "Backend env vars (MONGO_URI, GEMINI_API_KEY, ALLOWED_ORIGINS, etc.)."
    - kind: code
      target: "nexus/main.py#main"
      why: "Reads env vars (NEXUS_ENV/HOST/PORT/ALLOWED_ORIGINS) and wires services."
    - kind: code
      target: "aura/src/config/nexus.ts#getNexusConfig"
      why: "Resolves backend base URL via Vite env vars (VITE_AURA_API_URL/VITE_NEXUS_BASE_URL)."
    - kind: file
      target: "docs/api_reference/01_SSE_PROTOCOL.md"
      why: "Authoritative SSE event shapes and endpoints (chat/stream/commands)."

components:
  - id: CMP-nexus-entrypoint
    title: Backend Boot + Dependency Injection
    purpose: "Boots NEXUS runtime: connects DB, loads config, discovers tools, wires services, starts FastAPI and NexusBus."
    anchors:
      - kind: code
        target: "nexus/main.py#main"
        why: "Authoritative boot sequence (services + app + bus task)."

  - id: CMP-nexus-bus-topics
    title: NexusBus + Topics + Core Models
    purpose: "Defines the event-driven backbone: topics, message/run models, and async publish/subscribe bus."
    anchors:
      - kind: code
        target: "nexus/core/bus.py#NexusBus"
        why: "Per-topic queues, subscriber fan-out, run_forever listener model."
      - kind: code
        target: "nexus/core/topics.py#Topics"
        why: "Single source of truth for event topic names."
      - kind: code
        target: "nexus/core/models.py#Message"
        why: "Atomic payload unit flowing through the bus."
      - kind: code
        target: "nexus/core/models.py#Run"
        why: "Run lifecycle container (status/history/tools/metadata)."

  - id: CMP-nexus-interfaces
    title: HTTP REST + SSE Interfaces
    purpose: "Implements external IO surfaces: REST endpoints and SSE stream routing for UI events."
    anchors:
      - kind: code
        target: "nexus/interfaces/rest.py#chat"
        why: "POST /api/v1/chat returns SSE stream (per-run)."
      - kind: code
        target: "nexus/interfaces/rest.py#execute_command"
        why: "POST /api/v1/commands/execute executes commands synchronously."
      - kind: code
        target: "nexus/interfaces/rest.py#event_stream"
        why: "GET /api/v1/stream/{public_key} persistent SSE connection."
      - kind: code
        target: "nexus/interfaces/sse.py#SSEInterface"
        why: "Routes UI_EVENTS and COMMAND_RESULT into active SSE streams."
      - kind: code
        target: "nexus/interfaces/sse.py#SSEInterface.create_run_and_publish"
        why: "Creates Run + first human Message, publishes to Topics.RUNS_NEW."

  - id: CMP-orchestrator
    title: Orchestrator Service
    purpose: "Coordinates run state machine: identity gate, context build, LLM loop, tool orchestration, UI event forwarding."
    anchors:
      - kind: code
        target: "nexus/services/orchestrator.py#OrchestratorService"
        why: "Central agentic loop coordinator."
      - kind: code
        target: "nexus/services/orchestrator.py#OrchestratorService.handle_new_run"
        why: "Identity gate + start run + request context."
      - kind: code
        target: "nexus/services/orchestrator.py#OrchestratorService.handle_llm_result"
        why: "Tool-call detection, safety valve, UI forwarding."
      - kind: code
        target: "nexus/services/orchestrator.py#OrchestratorService.handle_tool_result"
        why: "Multi-tool sync + follow-up LLM call."

  - id: CMP-context-builder
    title: Context Builder
    purpose: "Builds LLM messages using tagged sections: identity/capabilities/history/friends_info/this_moment."
    anchors:
      - kind: code
        target: "nexus/services/context/builder.py#ContextBuilder"
        why: "Build + publish CONTEXT_BUILD_RESPONSE."
      - kind: code
        target: "nexus/services/context/builder.py#ContextBuilder.build_context"
        why: "Canonical message list used for LLM calls."

  - id: CMP-llm-service
    title: LLM Service (streaming + tool calls)
    purpose: "Selects provider/model, streams text chunks, aggregates tool call deltas, and publishes results."
    anchors:
      - kind: code
        target: "nexus/services/llm/service.py#LLMService"
        why: "Dynamic provider selection + streaming orchestration."
      - kind: code
        target: "nexus/services/llm/service.py#LLMService.handle_llm_request"
        why: "Entry handler for Topics.LLM_REQUESTS."
      - kind: code
        target: "nexus/services/llm/service.py#LLMService._process_streaming_chunks"
        why: "Ensures text_chunk ordering before tool_call_started."

  - id: CMP-tool-executor
    title: Tool Execution
    purpose: "Discovers tools, executes tool functions with timeout, and publishes standardized tool results."
    anchors:
      - kind: code
        target: "nexus/services/tool_executor.py#ToolExecutorService"
        why: "Executes tools and publishes TOOLS_RESULTS."
      - kind: code
        target: "nexus/services/tool_executor.py#ToolExecutorService.handle_tool_request"
        why: "Timeout + sync/async tool execution path."
      - kind: code
        target: "nexus/tools/registry.py#ToolRegistry.discover_and_register"
        why: "Auto-discovers tools from nexus.tools.definition.*"

  - id: CMP-command-identity-auth
    title: Command + Identity + Signature Verification
    purpose: "Executes commands, verifies signatures for sensitive operations, and exposes identity-gated personalization."
    anchors:
      - kind: code
        target: "nexus/services/command.py#CommandService"
        why: "Command discovery + execution + publishes COMMAND_RESULT."
      - kind: code
        target: "nexus/core/auth.py#verify_signature"
        why: "Shared Ethereum-style signature verification."
      - kind: code
        target: "nexus/services/identity.py#IdentityService"
        why: "Backend identity store (visitor vs member)."

  - id: CMP-persistence-config-db
    title: Persistence + Config + Database
    purpose: "DB access, config loading, and message persistence for conversation history."
    anchors:
      - kind: code
        target: "nexus/services/database/service.py#DatabaseService"
        why: "Async wrapper for Mongo provider + configuration IO."
      - kind: code
        target: "nexus/services/config.py#ConfigService"
        why: "Loads config from DB, resolves provider/catalog/defaults."
      - kind: code
        target: "nexus/services/persistence.py#PersistenceService"
        why: "Persists validated-member history and exposes get_history."

  - id: CMP-memory-learning
    title: Memory Learning Service
    purpose: "Automatically learns user profiles from conversation history every N turns, updating the friends_profile used in [FRIENDS_INFO]."
    anchors:
      - kind: code
        target: "nexus/services/memory_learning.py#MemoryLearningService"
        why: "Subscribes to CONTEXT_BUILD_REQUEST, increments turn counts, triggers LLM-based profile extraction."
      - kind: code
        target: "nexus/services/memory_learning.py#MemoryLearningService.handle_context_build_request"
        why: "Checks learning threshold and triggers learning process."
      - kind: code
        target: "nexus/services/database/providers/mongo.py#MongoProvider.increment_turn_count_and_check_threshold"
        why: "Atomic turn counting with threshold check."

  - id: CMP-aura-app-shell
    title: Frontend App Shell + Chat UI
    purpose: "Boots AURA UI, mounts chat experience, renders messages and command palette UI."
    anchors:
      - kind: code
        target: "aura/src/app/main.tsx"
        why: "Frontend entry + theme bootstrap."
      - kind: code
        target: "aura/src/app/App.tsx#App"
        why: "Top-level UI composition (ChatView + modals)."
      - kind: code
        target: "aura/src/features/chat/ChatContainer.tsx#ChatContainer"
        why: "Chat logic container (uses useAura + auto-scroll)."
      - kind: code
        target: "aura/src/features/chat/components/ChatView.tsx#ChatView"
        why: "Presentation layer for chat + command palette."

  - id: CMP-aura-streaming-transport
    title: Frontend Streaming Transport (HTTP+SSE)
    purpose: "Implements persistent SSE + per-chat SSE response parsing; emits events via EventEmitter."
    anchors:
      - kind: code
        target: "aura/src/services/stream/manager.ts#StreamManager"
        why: "connect() persistent stream + sendMessage() chat stream parsing."
      - kind: code
        target: "aura/src/services/stream/protocol.ts"
        why: "Type-level contract for SSE events and payloads."
      - kind: code
        target: "aura/src/config/nexus.ts#getNexusConfig"
        why: "Determines baseUrl used by StreamManager."

  - id: CMP-aura-state-command-identity
    title: Frontend Bridge (useAura) + Stores + Identity
    purpose: "Bridges transport events into UI state: subscribes to StreamManager events, updates Zustand stores, executes commands, signs requests."
    anchors:
      - kind: code
        target: "aura/src/features/chat/hooks/useAura.ts#useAura"
        why: "Subscribes to StreamManager events and routes to stores."
      - kind: code
        target: "aura/src/features/chat/store/chatStore.ts#useChatStore"
        why: "Chat state machine: messages/currentRun/tool calls/visitor mode."
      - kind: code
        target: "aura/src/features/command/commandExecutor.ts#executeCommand"
        why: "Command routing (client/server/rest/gui), signs server commands when needed."
      - kind: code
        target: "aura/src/services/identity/identity.ts#IdentityService"
        why: "Local identity + signing implementation (matches backend verify_signature)."

flows:
  - id: FLOW-backend-startup
    title: Backend Startup
    intent: "Initialize NEXUS services and start FastAPI + NexusBus runtime."
    steps:
      - do: "Load env vars, connect DB, load ConfigService, discover tools, wire and subscribe services"
        refs:
          - kind: code
            target: "nexus/main.py#main"
            why: "Boot sequence + dependency injection overrides for REST interface."
      - do: "Run NexusBus listeners and uvicorn concurrently"
        refs:
          - kind: code
            target: "nexus/main.py#main"
            why: "asyncio.gather(bus.run_forever(), server.serve())"

  - id: FLOW-frontend-startup
    title: Frontend Startup
    intent: "Boot AURA UI and connect to backend streams."
    steps:
      - do: "Mount React app, apply theme bootstrap"
        refs:
          - kind: code
            target: "aura/src/app/main.tsx"
            why: "ensureThemeOnLoad() then render <App />"
      - do: "Auto-connect persistent SSE stream and subscribe to events"
        refs:
          - kind: code
            target: "aura/src/features/chat/hooks/useAura.ts#useAura"
            why: "useEffect() subscribes + connect()"
          - kind: code
            target: "aura/src/services/stream/manager.ts#StreamManager.connect"
            why: "GET /api/v1/stream/{publicKey}"

  - id: FLOW-chat-turn
    title: Chat Turn (HTTP + SSE)
    intent: "User sends message; backend runs agentic loop; frontend renders streaming output."
    steps:
      - do: "User sends message (AURA)"
        refs:
          - kind: code
            target: "aura/src/features/chat/store/chatStore.ts#useChatStore"
            why: "sendMessage() pushes HUMAN message then StreamManager.sendMessage()."
          - kind: code
            target: "aura/src/services/stream/manager.ts#StreamManager.sendMessage"
            why: "POST /api/v1/chat and parse SSE response."
      - do: "Create Run and publish Topics.RUNS_NEW (Backend)"
        refs:
          - kind: code
            target: "nexus/interfaces/rest.py#chat"
            why: "Calls SSEInterface.create_run_and_publish()."
          - kind: code
            target: "nexus/interfaces/sse.py#SSEInterface.create_run_and_publish"
            why: "Creates Run + publishes RUNS_NEW."
      - do: "Orchestrator identity gate: visitor guidance OR proceed with context/LLM/tools"
        refs:
          - kind: code
            target: "nexus/services/orchestrator.py#OrchestratorService.handle_new_run"
            why: "Member/visitor branching + run_started + context request."
      - do: "ContextBuilder builds LLM messages and Orchestrator requests LLM"
        refs:
          - kind: code
            target: "nexus/services/context/builder.py#ContextBuilder.handle_build_request"
            why: "Builds context and publishes CONTEXT_BUILD_RESPONSE."
          - kind: code
            target: "nexus/services/orchestrator.py#OrchestratorService.handle_context_ready"
            why: "Publishes LLM_REQUESTS (messages + tools + user_profile)."
      - do: "LLM streams text_chunk and tool_call_started; Orchestrator forwards to UI_EVENTS; SSEInterface routes to chat SSE response"
        refs:
          - kind: code
            target: "nexus/services/llm/service.py#LLMService._publish_text_chunk"
            why: "Publishes streaming events to LLM_RESULTS."
          - kind: code
            target: "nexus/services/orchestrator.py#OrchestratorService.handle_llm_result"
            why: "Forwards streaming events to UI_EVENTS."
          - kind: code
            target: "nexus/interfaces/sse.py#SSEInterface.handle_ui_event"
            why: "Routes UI_EVENTS into run_id chat queue (SSE response)."
      - do: "AURA receives SSE events, updates stores, renders ChatView"
        refs:
          - kind: code
            target: "aura/src/services/stream/manager.ts#StreamManager.parseSSEStream"
            why: "Parses event/data lines and emits EventEmitter events."
          - kind: code
            target: "aura/src/features/chat/hooks/useAura.ts#useAura"
            why: "Subscribes to events and calls chatStore handlers."
          - kind: code
            target: "aura/src/features/chat/components/ChatView.tsx#ChatView"
            why: "Renders message stream + thinking + tool cards."

  - id: FLOW-command-execute
    title: Command Execution (client/server/rest)
    intent: "Execute commands via palette; server commands are signed and sent via HTTP; results are applied as command_result events (from HTTP response, and optionally via persistent SSE for proactive results)."
    steps:
      - do: "User triggers command (palette)"
        refs:
          - kind: code
            target: "aura/src/features/command/commandExecutor.ts#executeCommand"
            why: "Routes by handler type (client/server/rest/gui)."
      - do: "For server commands: optionally sign with IdentityService, POST /api/v1/commands/execute"
        refs:
          - kind: code
            target: "aura/src/services/identity/identity.ts#IdentityService.signCommand"
            why: "Creates keccak256 signature without Ethereum prefix (matches backend)."
          - kind: code
            target: "aura/src/services/stream/manager.ts#StreamManager.executeCommand"
            why: "POST /api/v1/commands/execute"
          - kind: code
            target: "nexus/interfaces/rest.py#execute_command"
            why: "Executes command synchronously and returns JSON."
      - do: "Command results are delivered as JSON and emitted to the UI as command_result events (persistent SSE may also deliver proactive command_result events)"
        refs:
          - kind: code
            target: "aura/src/services/stream/manager.ts#StreamManager.sendCommand"
            why: "Wraps HTTP result and emits 'command_result' for UI consumption."
          - kind: code
            target: "nexus/interfaces/sse.py#SSEInterface.handle_command_result"
            why: "Wraps and routes command_result to persistent stream queue."
          - kind: code
            target: "aura/src/features/chat/store/chatStore.ts#useChatStore"
            why: "handleCommandResult() updates pending SYSTEM message."

invariants:
  - id: INV-event-bus-only
    statement: "Backend services coordinate via NexusBus topics; cross-service calls are expressed as publish/subscribe events."
    refs:
      - kind: code
        target: "nexus/core/bus.py#NexusBus"
        why: "Single pub/sub backbone."
      - kind: code
        target: "nexus/core/topics.py#Topics"
        why: "Central topic registry."

  - id: INV-ui-events-gateway
    statement: "Frontend-visible real-time updates must flow through UI_EVENTS and be routed by SSEInterface to preserve ordering."
    refs:
      - kind: code
        target: "nexus/services/orchestrator.py#OrchestratorService.handle_llm_result"
        why: "Forwards streaming events to UI_EVENTS."
      - kind: code
        target: "nexus/interfaces/sse.py#SSEInterface.handle_ui_event"
        why: "Routes UI events to the correct active SSE stream."

  - id: INV-visitor-gatekeeper
    statement: "Unregistered users (visitors) must not trigger normal run processing; they receive guidance and the run is closed."
    refs:
      - kind: code
        target: "nexus/services/orchestrator.py#OrchestratorService.handle_new_run"
        why: "Identity check + visitor guidance + run_finished early return."
      - kind: code
        target: "nexus/services/persistence.py#PersistenceService.handle_context_build_request"
        why: "Persistence subscribes after identity gate (CONTEXT_BUILD_REQUEST)."
      - kind: code
        target: "aura/src/features/chat/store/chatStore.ts#useChatStore"
        why: "SYSTEM role text_chunk enters visitorMode in UI."

  - id: INV-signature-verification
    statement: "Sensitive operations require cryptographic signatures verified by the backend (Ethereum-style ECDSA + keccak)."
    refs:
      - kind: code
        target: "nexus/core/auth.py#verify_signature"
        why: "Backend signature verification."
      - kind: code
        target: "aura/src/services/identity/identity.ts#IdentityService.signCommand"
        why: "Frontend signing (raw keccak256, no prefix)."
      - kind: code
        target: "nexus/interfaces/rest.py#verify_request_signature"
        why: "Canonical JSON signing for REST writes (sort_keys=True)."

  - id: INV-sse-keepalive
    statement: "SSE streams should send periodic keepalive comments and clients must ignore comment lines."
    refs:
      - kind: code
        target: "nexus/interfaces/rest.py#chat"
        why: "format_sse_keepalive() yields ': keepalive'."
      - kind: code
        target: "nexus/interfaces/sse.py#SSEInterface.format_sse_keepalive"
        why: "Keepalive comment format."
      - kind: file
        target: "docs/api_reference/01_SSE_PROTOCOL.md"
        why: "Protocol reference for keepalive behavior."

evidences:
  - id: EVD-orchestrator-integration
    title: "Orchestrator flow integration tests"
    refs:
      - kind: test
        target: "tests/nexus/integration/services/test_orchestrator_service.py#TestOrchestratorFlows.test_simple_dialogue_flow"
        why: "Asserts run_started/context/llm/run_finished sequence."
      - kind: test
        target: "tests/nexus/integration/services/test_orchestrator_service.py#TestOrchestratorFlows.test_multi_tool_sync_flow"
        why: "Asserts multi-tool sync (wait for both tools)."

  - id: EVD-aura-chat-store
    title: "AURA chat store unit tests"
    refs:
      - kind: test
        target: "aura/src/features/chat/store/__tests__/chatStore.test.ts"
        why: "Asserts streaming + tool call state transitions and message updates."

  - id: EVD-aura-command-store
    title: "AURA command store unit tests"
    refs:
      - kind: test
        target: "aura/src/features/command/store/__tests__/commandStore.test.ts"
        why: "Asserts palette state + command filtering/selection behavior."

  - id: EVD-aura-identity
    title: "AURA identity service unit tests"
    refs:
      - kind: test
        target: "aura/src/services/identity/identity.test.ts"
        why: "Asserts key derivation, signing, mnemonic import/export."

relations:
  - id: REL-backend-startup-implements-entrypoint
    from: FLOW-backend-startup
    to: CMP-nexus-entrypoint
    kind: implements
    note: "Backend boot flow is implemented by nexus/main.py#main"
    refs:
      - kind: code
        target: "nexus/main.py#main"
        why: "Boots services and runs FastAPI + bus."

  - id: REL-entrypoint-uses-bus
    from: CMP-nexus-entrypoint
    to: CMP-nexus-bus-topics
    kind: uses
    note: "Entry point instantiates NexusBus and relies on Topics + core models."
    refs:
      - kind: code
        target: "nexus/main.py#main"
        why: "Creates bus and starts bus.run_forever()."

  - id: REL-entrypoint-uses-data-services
    from: CMP-nexus-entrypoint
    to: CMP-persistence-config-db
    kind: uses
    note: "Boot loads DB/config and wires persistence."
    refs:
      - kind: code
        target: "nexus/main.py#main"
        why: "DatabaseService.connect() then ConfigService.initialize()."

  - id: REL-entrypoint-uses-interfaces
    from: CMP-nexus-entrypoint
    to: CMP-nexus-interfaces
    kind: uses
    note: "Boot wires REST + SSE interfaces and DI overrides."
    refs:
      - kind: code
        target: "nexus/main.py#main"
        why: "Creates SSEInterface and includes rest.router."

  - id: REL-interfaces-use-bus
    from: CMP-nexus-interfaces
    to: CMP-nexus-bus-topics
    kind: uses
    note: "Interfaces publish and subscribe bus messages for runs/UI routing."
    refs:
      - kind: code
        target: "nexus/interfaces/sse.py#SSEInterface.subscribe_to_bus"
        why: "Subscribes UI_EVENTS and COMMAND_RESULT."

  - id: REL-sse-interfaces-start-run
    from: CMP-nexus-interfaces
    to: CMP-orchestrator
    kind: calls
    note: "POST /chat creates a Run and publishes RUNS_NEW which Orchestrator consumes."
    refs:
      - kind: code
        target: "nexus/interfaces/sse.py#SSEInterface.create_run_and_publish"
        why: "Publishes Topics.RUNS_NEW."
      - kind: code
        target: "nexus/services/orchestrator.py#OrchestratorService.handle_new_run"
        why: "Subscribed handler for Topics.RUNS_NEW."

  - id: REL-orchestrator-calls-context
    from: CMP-orchestrator
    to: CMP-context-builder
    kind: calls
    note: "Orchestrator requests context building via Topics.CONTEXT_BUILD_REQUEST."
    refs:
      - kind: code
        target: "nexus/services/orchestrator.py#OrchestratorService.handle_new_run"
        why: "Publishes CONTEXT_BUILD_REQUEST with Run object."
      - kind: code
        target: "nexus/services/context/builder.py#ContextBuilder.handle_build_request"
        why: "Consumes CONTEXT_BUILD_REQUEST and responds."

  - id: REL-context-uses-persistence
    from: CMP-context-builder
    to: CMP-persistence-config-db
    kind: uses
    note: "ContextBuilder loads recent history via PersistenceService."
    refs:
      - kind: code
        target: "nexus/services/context/builder.py#ContextBuilder._get_history"
        why: "Calls persistence_service.get_history()."

  - id: REL-orchestrator-calls-llm
    from: CMP-orchestrator
    to: CMP-llm-service
    kind: calls
    note: "Orchestrator publishes Topics.LLM_REQUESTS; LLMService streams results to LLM_RESULTS."
    refs:
      - kind: code
        target: "nexus/services/orchestrator.py#OrchestratorService.handle_context_ready"
        why: "Publishes Topics.LLM_REQUESTS."
      - kind: code
        target: "nexus/services/llm/service.py#LLMService.handle_llm_request"
        why: "Subscribed handler for Topics.LLM_REQUESTS."

  - id: REL-llm-results-forwarded-to-ui
    from: CMP-llm-service
    to: CMP-nexus-interfaces
    kind: calls
    note: "LLM streaming events are forwarded by Orchestrator to UI_EVENTS, then routed by SSEInterface to SSE streams."
    refs:
      - kind: code
        target: "nexus/services/llm/service.py#LLMService._publish_text_chunk"
        why: "Publishes text_chunk to LLM_RESULTS."
      - kind: code
        target: "nexus/services/orchestrator.py#OrchestratorService.handle_llm_result"
        why: "Forwards to Topics.UI_EVENTS."
      - kind: code
        target: "nexus/interfaces/sse.py#SSEInterface.handle_ui_event"
        why: "Routes to active chat stream."

  - id: REL-orchestrator-calls-tools
    from: CMP-orchestrator
    to: CMP-tool-executor
    kind: calls
    note: "Orchestrator publishes TOOLS_REQUESTS when tool_calls are present."
    refs:
      - kind: code
        target: "nexus/services/orchestrator.py#OrchestratorService.handle_llm_result"
        why: "Publishes Topics.TOOLS_REQUESTS for each call."
      - kind: code
        target: "nexus/services/tool_executor.py#ToolExecutorService.handle_tool_request"
        why: "Consumes and executes tool requests."

  - id: REL-command-service-publishes-command-result
    from: CMP-command-identity-auth
    to: CMP-nexus-interfaces
    kind: calls
    note: "When commands are executed via the NexusBus path, CommandService publishes COMMAND_RESULT and SSEInterface can route it to the persistent SSE stream."
    refs:
      - kind: code
        target: "nexus/services/command.py#CommandService.handle_command"
        why: "Publishes Topics.COMMAND_RESULT."
      - kind: code
        target: "nexus/interfaces/sse.py#SSEInterface.handle_command_result"
        why: "Routes command_result to persistent stream queue."

  - id: REL-frontend-startup-implements-app
    from: FLOW-frontend-startup
    to: CMP-aura-app-shell
    kind: implements
    note: "Frontend boot is implemented by main.tsx and useAura auto-connect."
    refs:
      - kind: code
        target: "aura/src/app/main.tsx"
        why: "App entrypoint."

  - id: REL-aura-app-uses-bridge
    from: CMP-aura-app-shell
    to: CMP-aura-state-command-identity
    kind: uses
    note: "ChatContainer uses useAura to bind stores and transport to the UI."
    refs:
      - kind: code
        target: "aura/src/features/chat/ChatContainer.tsx#ChatContainer"
        why: "Calls useAura() and passes state/actions to ChatView."

  - id: REL-aura-bridge-uses-transport
    from: CMP-aura-state-command-identity
    to: CMP-aura-streaming-transport
    kind: uses
    note: "useAura subscribes to StreamManager events and triggers connect/sendMessage/sendCommand."
    refs:
      - kind: code
        target: "aura/src/features/chat/hooks/useAura.ts#useAura"
        why: "Subscribes to run_started/text_chunk/tool events."
      - kind: code
        target: "aura/src/services/stream/manager.ts#StreamManager"
        why: "EventSource + fetch-based SSE parsing."

  - id: REL-aura-transport-calls-backend
    from: CMP-aura-streaming-transport
    to: CMP-nexus-interfaces
    kind: calls
    note: "AURA calls NEXUS /chat, /commands/execute, and /stream/{public_key}."
    refs:
      - kind: code
        target: "aura/src/services/stream/manager.ts#StreamManager.connect"
        why: "GET /api/v1/stream/{publicKey}."
      - kind: code
        target: "aura/src/services/stream/manager.ts#StreamManager.sendMessage"
        why: "POST /api/v1/chat (streaming response)."
      - kind: code
        target: "aura/src/services/stream/manager.ts#StreamManager.executeCommand"
        why: "POST /api/v1/commands/execute."

  - id: REL-inv-visitor-gates-orchestrator
    from: INV-visitor-gatekeeper
    to: CMP-orchestrator
    kind: guards
    note: "Visitor mode short-circuits normal orchestration."
    refs:
      - kind: code
        target: "nexus/services/orchestrator.py#OrchestratorService.handle_new_run"
        why: "Early return on identity None."

  - id: REL-evd-orchestrator-flow
    from: EVD-orchestrator-integration
    to: FLOW-chat-turn
    kind: evidences
    note: "Integration tests cover key Orchestrator flows and tool loop behavior."
    refs:
      - kind: test
        target: "tests/nexus/integration/services/test_orchestrator_service.py#TestOrchestratorFlows.test_single_tool_call_flow"
        why: "Evidences tool loop orchestration."

  - id: REL-evd-aura-chat-store
    from: EVD-aura-chat-store
    to: FLOW-chat-turn
    kind: evidences
    note: "Frontend unit tests evidence chat state transitions for streaming events."
    refs:
      - kind: test
        target: "aura/src/features/chat/store/__tests__/chatStore.test.ts"
        why: "Evidences chat store behaviors." 

  - id: REL-evd-aura-command-store
    from: EVD-aura-command-store
    to: FLOW-command-execute
    kind: evidences
    note: "Frontend unit tests evidence command palette state and filtering behavior."
    refs:
      - kind: test
        target: "aura/src/features/command/store/__tests__/commandStore.test.ts"
        why: "Evidences command store behaviors."

  - id: REL-memory-learning-subscribes-context
    from: CMP-memory-learning
    to: CMP-orchestrator
    kind: subscribes
    note: "MemoryLearningService subscribes to Topics.CONTEXT_BUILD_REQUEST (published by Orchestrator) to increment turn counts and trigger learning."
    refs:
      - kind: code
        target: "nexus/services/memory_learning.py#MemoryLearningService.subscribe_to_bus"
        why: "Subscribes to CONTEXT_BUILD_REQUEST."
      - kind: code
        target: "nexus/services/orchestrator.py#OrchestratorService.handle_new_run"
        why: "Publishes CONTEXT_BUILD_REQUEST with Run object."

  - id: REL-memory-learning-uses-database
    from: CMP-memory-learning
    to: CMP-persistence-config-db
    kind: uses
    note: "MemoryLearningService uses DatabaseService for atomic turn counting and PersistenceService for conversation history."
    refs:
      - kind: code
        target: "nexus/services/memory_learning.py#MemoryLearningService._should_learn"
        why: "Calls database provider increment_turn_count_and_check_threshold."
      - kind: code
        target: "nexus/services/memory_learning.py#MemoryLearningService._get_recent_history"
        why: "Calls persistence_service.get_history."

  - id: REL-evd-aura-identity
    from: EVD-aura-identity
    to: INV-signature-verification
    kind: evidences
    note: "Frontend unit tests evidence key derivation and signing used for authenticated commands."
    refs:
      - kind: test
        target: "aura/src/services/identity/identity.test.ts"
        why: "Evidences signing and mnemonic handling."
```

## Maintenance

- Keep `id`s stable.
- Prefer `file#SymbolPath` anchors (line numbers are volatile).
- When behavior changes, update the nearest `FLOW-*` steps and affected `relations`.
- When adding a new invariant, add at least one `EVD-*` when possible.
