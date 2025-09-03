# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🏗️ Architecture Overview

NEXUS is a dual-stack AI assistant platform with:
- **Backend (NEXUS)**: Python FastAPI service with event-driven architecture
- **Frontend (AURA)**: React + TypeScript + Vite chat interface

### Backend Architecture
- **Event Bus**: `NexusBus` (nexus/core/bus.py) - Pub/sub system for inter-service communication
- **Core Services**: LLM, Database, Context, ToolExecutor, Orchestrator services
- **WebSocket Interface**: Real-time communication with frontend
- **Tool System**: Dynamic tool discovery and execution

### Frontend Architecture  
- **React 19 + TypeScript**: Modern component-based UI
- **Zustand**: State management
- **WebSocket**: Real-time communication with backend
- **Tailwind CSS**: Styling with custom design system
- **Framer Motion**: Animations

## 🚀 Development Commands

### Backend (Python)
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run development server
python -m nexus.main

# Run with specific config (from project root)
python -m nexus.main
```

### Frontend (Node.js)
```bash
# Install dependencies (from aura/ directory)
cd aura && pnpm install

# Start development server
pnpm dev

# Build for production
pnpm build

# Lint code
pnpm lint

# Type check
pnpm typecheck  # Note: Add this script if missing
```

## 📁 Key Directories

### Backend (`./nexus/`)
- `core/`: Event bus, models, topics
- `services/`: Core services (LLM, Database, Context, etc.)
- `tools/definition/`: Tool definitions and registry
- `interfaces/`: WebSocket interface

### Frontend (`./aura/src/`)
- `app/`: App entry and global styles
- `components/`: Reusable UI components
- `features/chat/`: Chat functionality
- `hooks/`: Custom React hooks
- `services/`: External service interfaces
- `lib/`: Utility functions

## 🔧 Configuration

### Environment Variables (.env)
```
GEMINI_API_KEY=your_gemini_key
OPENROUTER_API_KEY=your_openrouter_key  
MONGO_URI=mongodb_atlas
```

### Config File (config.default.yml)
- System settings, LLM providers, database config
- Copy to `config.yml` and customize as needed

## 🧪 Testing

### Backend Testing
```bash
# Run Python tests (add pytest to requirements if needed)
python -m pytest
```

### Frontend Testing  
```bash
# Run tests (add testing framework if needed)
cd aura && pnpm test
```

## 📡 Communication Protocol

### WebSocket Events
- Messages flow through WebSocket between AURA and NEXUS
- Real-time streaming and tool execution status
- See `nexus/interfaces/websocket.py` and `aura/src/services/websocket.ts`

## 🎨 Design System

### Frontend Styling
- **Tailwind CSS** with custom design tokens
- **Grayscale palette** only - no colors allowed
- **Container/Presenter pattern** for component separation
- **TypeScript** for full type safety

### Component Guidelines
- PascalCase for component files (`ComponentName.tsx`)
- `use` prefix for hooks (`useHook.ts`)
- camelCase for utilities (`utilityFunction.ts`)

## 🔄 Development Workflow

1. **Backend first**: Start NEXUS service (`python -m nexus.main`)
2. **Frontend second**: Start AURA dev server (`cd aura && pnpm dev`)
3. **Environment**: Set required API keys in `.env`
4. **Database**: MongoDB required for persistence

## 🛠️ Tool System

- Tools are auto-discovered from `nexus/tools/definition/`
- Tool registry manages discovery and execution
- Tools can be called by LLM through tool calling mechanism

## 📊 Monitoring & Logging

- Backend uses Python logging with INFO level by default
- Log format: `%(asctime)s | %(levelname)s | %(name)s | %(message)s`
- Adjust log level in `config.yml`

## 🚨 Common Issues

- **Missing API keys**: Check `.env` file for required keys
- **MongoDB connection**: Ensure MongoDB is running
- **WebSocket connection**: Verify backend is running on correct port
- **Type errors**: Run `pnpm typecheck` in aura directory

## 🤖 Agent Collaboration Best Practices

### When delegating to test-engineer agent:
1. **Provide specific context**: Include file paths to existing test patterns, service implementations, and relevant constants
2. **Specify test scope**: Clearly define success/failure scenarios, edge cases, and expected behaviors
3. **Include project-specific patterns**: Mention pytest fixtures, mocking approaches, and async/await patterns used
4. **Verify enum values**: Always check actual enum definitions (Role.HUMAN vs Role.USER) before writing tests
5. **Review generated tests**: Check for proper mocking, async handling, and alignment with existing code patterns

### Test Writing Guidelines:
- Use `mocker` fixture for consistent mocking
- Follow existing test structure and naming conventions
- Test both success and failure paths comprehensively
- Verify async/await patterns match service implementations
- Check for proper constant usage from core models

## 🔍 Code Navigation Tips

- **Backend entry**: `nexus/main.py`
- **Frontend entry**: `aura/src/app/`
- **Event system**: `nexus/core/bus.py`
- **WebSocket**: `nexus/interfaces/websocket.py` and `aura/src/services/websocket.ts`
- **LLM integration**: `nexus/services/llm/service.py`
- **Database**: `nexus/services/database/service.py`