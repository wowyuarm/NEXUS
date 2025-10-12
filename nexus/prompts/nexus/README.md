# NEXUS Prompt System

This directory contains the modular prompt system for NEXUS. The prompts are organized into separate files, each serving a specific purpose in shaping NEXUS's behavior, capabilities, and self-awareness.

## 📁 Prompt Structure

### Core Prompt Files

1. **`persona.md`** - Core personality and communication style
   - Defines who NEXUS is as a conversational partner
   - Communication style and tone guidelines
   - Thinking approach and interaction principles
   - **Update frequency**: When personality traits or communication style needs adjustment

2. **`tools.md`** - Available tools and usage guidelines
   - Tool descriptions and parameters
   - Usage scenarios and best practices
   - Tool combination strategies
   - **Update frequency**: When new tools are added or existing tools are modified

3. **`system.md`** - System architecture and self-awareness
   - How NEXUS works internally (event-driven architecture)
   - Service components and their roles
   - Capabilities and limitations
   - **Update frequency**: When system architecture changes or new services are added

## 🔄 How Prompts Are Loaded

The prompt system uses a **modular composition** approach:

```python
# In ContextService (nexus/services/context.py)
final_prompt = SEPARATOR.join([
    persona_content,    # from persona.md
    system_content,     # from system.md
    tools_content       # from tools.md
])
```

All three prompts are concatenated in order and sent to the LLM as the system message.

## 📝 Updating Prompts

### General Guidelines

1. **Maintain consistency**: Ensure tone and style are consistent across all three files
2. **Be specific**: Use concrete examples and clear language
3. **Stay practical**: Balance philosophy with actionable guidance
4. **Test changes**: After updating, test with various user queries to ensure desired behavior

### Persona Updates

**When to update**:
- Adjusting communication style (more formal/casual, detailed/concise)
- Adding/removing behavioral traits
- Modifying thinking approach or analysis methods

**Best practices**:
- Keep the core identity stable; adjust nuances
- Use concrete examples for abstract concepts
- Maintain the balance between warmth and professionalism

**Example**:
```markdown
Before: "I provide helpful responses"
After: "I provide thoughtful analysis that helps you understand not just 'what' but 'why'"
```

### Tools Updates

**When to update**:
- Adding a new tool (create new section with tool signature, description, examples)
- Modifying tool parameters or behavior
- Adding new usage strategies or best practices

**Template for new tools**:
```markdown
## `tool_name(param1: type, param2: type = default)`

### 工具作用
Clear explanation of what the tool does and why it's useful.

### 参数说明
- `param1` (type) - Description
- `param2` (type, optional) - Description, default value

### 何时使用
**When X happens**
Explanation of when to use this tool.

### 示例场景
\```
tool_name("example")
# Explanation
\```

### 使用原则
How to use this tool effectively.
```

### System Updates

**When to update**:
- Major architecture changes (new services, modified event flow)
- Changes to Run lifecycle or state transitions
- Updates to capabilities or limitations
- New system features (e.g., multi-modal support)

**What to preserve**:
- Core architecture concepts (event-driven, service-oriented)
- Key design principles
- Self-awareness framework

**What to update**:
- Specific service descriptions when their roles change
- Event flow examples when workflow changes
- Capability lists when features are added/removed

## 🎯 Prompt Design Philosophy

### Core Principles

1. **Self-awareness over blind execution**
   - NEXUS should understand its own architecture
   - Know capabilities and limitations
   - Explain behavior transparently

2. **Natural over mechanical**
   - Avoid overly abstract or poetic language
   - Use practical, clear descriptions
   - Balance depth with accessibility

3. **Modular over monolithic**
   - Each file has a clear, focused purpose
   - Easy to update one aspect without affecting others
   - Clean separation of concerns

4. **Actionable over theoretical**
   - Provide concrete guidance, not just philosophy
   - Include examples and use cases
   - Focus on "what to do" not just "what to be"

### Style Consistency Checklist

Before committing prompt changes, verify:

- [ ] Tone is consistent across all three files
- [ ] Technical terms are explained clearly
- [ ] Examples are concrete and practical
- [ ] No contradictions between files
- [ ] Language level is appropriate (not too abstract, not too simple)
- [ ] Changes align with overall NEXUS design philosophy

## 🧪 Testing Prompt Changes

### Manual Testing

After updating prompts, test with queries that exercise the changed behavior:

```bash
# Restart NEXUS to load new prompts
python -m nexus.main

# Test in frontend or via API
# Try various scenarios:
# - Simple questions
# - Complex multi-step tasks
# - Edge cases
# - Tool-requiring queries
```

### Key Test Scenarios

1. **Persona changes**: Test tone and communication style
   - Ask open-ended questions
   - Request explanations of complex topics
   - Test empathy and understanding

2. **Tools changes**: Test tool usage
   - Queries requiring web search
   - Queries needing web extraction
   - Multi-tool workflows

3. **System changes**: Test self-awareness
   - Ask about capabilities
   - Request limitations
   - Test transparency about internal processes

## 📋 Version Control Best Practices

### Commit Messages

Use clear, descriptive commit messages:

```bash
# Good examples
feat(prompts): add reflection capability to persona
fix(prompts): clarify tool usage guidelines in tools.md
refactor(prompts): unify tone across all prompt files
docs(prompts): update system.md with new service descriptions

# Bad examples
update prompts
fix stuff
change persona
```

### Change Documentation

For significant prompt updates, document the rationale:

```markdown
## 2025-10-12: Enhanced Self-Awareness in system.md

### Changes
- Added detailed service descriptions
- Clarified event flow with concrete examples
- Updated capability/limitation lists

### Rationale
Users were confused about what NEXUS could do. Enhanced system awareness
helps NEXUS explain its capabilities more clearly.

### Impact
- More transparent responses about limitations
- Better tool selection decisions
- Clearer explanations of internal processes
```

## 🔍 Troubleshooting

### Common Issues

**Issue**: NEXUS is too verbose/too brief
- **Solution**: Adjust communication style in `persona.md`
- **Section**: "沟通风格 (Communication Style)"

**Issue**: NEXUS doesn't use tools when it should
- **Solution**: Clarify usage guidelines in `tools.md`
- **Section**: "何时使用" for each tool

**Issue**: NEXUS gives incorrect self-descriptions
- **Solution**: Update system awareness in `system.md`
- **Section**: "我的能力与限制"

**Issue**: Inconsistent tone across responses
- **Solution**: Review all three files for tone consistency
- **Check**: Core values in `persona.md`, principles in `tools.md` and `system.md`

## 🚀 Future Enhancements

Planned improvements to the prompt system:

1. **Dynamic prompt selection** - Load different personas based on user preferences
2. **Prompt versioning** - A/B test different prompt variations
3. **User-specific overrides** - Allow users to customize prompts (already supported via `prompt_overrides`)
4. **Prompt analytics** - Track which prompts lead to better outcomes
5. **Multi-language support** - Provide prompts in multiple languages

## 📚 Additional Resources

- **Configuration**: See `config.example.yml` for user_defaults.prompts structure
- **Context Service**: `nexus/services/context.py` - How prompts are loaded and composed
- **Identity Service**: `nexus/services/identity.py` - User-specific prompt overrides
- **Architecture Docs**: `docs/knowledge_base/` - Detailed system architecture

---

**Last Updated**: 2025-10-12  
**Maintainer**: NEXUS Development Team

