# Technical References

## 📚 What This Directory Contains

This directory houses **deep-dive technical documentation** for specific subsystems, modules, or cross-cutting concerns within the NEXUS project. Unlike the high-level architectural documents in the parent `knowledge_base/` directory, these references provide **exhaustive, implementation-level details** for engineers and AI agents working on specific technical domains.

Each document here is a **self-contained, comprehensive reference** that covers:
- Current implementation details
- Configuration mechanics
- Integration points between modules
- Environment-specific behaviors
- Troubleshooting and debugging guidance

---

## 🎯 Purpose and Scope

### What Goes Here
- **Environment and deployment configurations** (local vs. production)
- **Communication protocols** (WebSocket, REST API, event bus mechanics)
- **Authentication and identity systems** (key generation, signing, verification)
- **State management patterns** (store architecture, data flow)
- **Tool and command systems** (execution pipelines, handler types)
- **Database schemas and migration strategies**
- **Build and bundling processes** (Vite, Docker, nginx)

### What Does NOT Go Here
- High-level vision and philosophy → `knowledge_base/01_VISION_AND_PHILOSOPHY.md`
- Architectural overviews → `knowledge_base/02_NEXUS_ARCHITECTURE.md`
- Quick-start guides → `developer_guides/01_SETUP_AND_RUN.md`
- Troubleshooting logs → `learn/`

---

## 📝 Document Naming Convention

**Use descriptive, topic-based names without numbering prefixes.**

✅ Good examples:
- `environment_configuration.md`
- `websocket_protocol.md`
- `command_execution_pipeline.md`
- `identity_and_cryptography.md`

❌ Avoid:
- `01_environment.md` (no numbering)
- `notes.md` (too vague)
- `misc_config.md` (not specific)

---

## 🤖 Guide for AI Contributors

### When to Create a New Technical Reference

Create a new document when:
1. **A subsystem has grown complex** and needs detailed documentation
2. **Cross-module integration** requires deep explanation (e.g., how frontend and backend coordinate on authentication)
3. **Environment-specific behavior** needs comprehensive coverage (e.g., local dev vs. Render production)
4. **A recurring issue** needs a definitive reference (e.g., WebSocket connection lifecycle)
5. **Future maintenance** will require understanding low-level implementation details

### Writing Structure Template

```markdown
# [Topic Name]

## Overview
Brief summary of what this document covers and why it matters.

## Architecture Context
How this subsystem fits into the larger NEXUS/AURA ecosystem.

## Detailed Breakdown
### [Module/Aspect 1]
- Current implementation
- Configuration options
- Key files and code paths

### [Module/Aspect 2]
...

## Integration Points
How this subsystem interacts with others (cross-references).

## Environment-Specific Behavior
Differences between local development and production.

## Common Issues and Troubleshooting
Known gotchas, debugging tips, resolution strategies.

## References
Links to related knowledge base docs, external resources, or code files.
```

### Quality Standards
- **Be exhaustive**: Include all relevant configuration options, environment variables, and code paths
- **Be precise**: Use exact file paths, function names, and configuration keys
- **Be current**: Update documents when implementation changes
- **Cross-reference**: Link to related docs and code when helpful
- **Include examples**: Real configuration snippets, code samples, or console outputs

### Maintenance
- When modifying a subsystem, **update the corresponding technical reference**
- If a document becomes outdated, either update it or mark it as deprecated with a migration path
- Use git commit messages to reference doc updates when code changes

---

## 📖 Current Technical References

| Document | Description | Last Updated |
|----------|-------------|--------------|
| `environment_configuration.md` | Complete guide to environment setup (local/production), variable flow, and network architecture | 2025-10-07 |
| `command_system.md` | Exhaustive documentation of the command system: auto-discovery, execution handlers, WebSocket protocol, and signature verification | 2025-10-07 |

---

## 🔗 Related Documentation

- **High-Level Context**: `../01_VISION_AND_PHILOSOPHY.md`, `../02_NEXUS_ARCHITECTURE.md`
- **Setup Guides**: `../../developer_guides/01_SETUP_AND_RUN.md`
- **Troubleshooting Logs**: `../../learn/`
- **API Specs**: `../../api_reference/`

---

_This README serves as a living guide for maintaining the technical references collection. Update it as new categories or conventions emerge._

