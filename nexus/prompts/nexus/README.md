# NEXUS Prompt System

This directory contains the modular prompt system for NEXUS. The prompts are organized into separate files, each serving a specific purpose in creating a "field" for deep dialogue and co-growth.

## 🌊 Design Philosophy: The Field

The NEXUS prompt system is designed not as a "user manual" but as a **field** - a space where human and AI consciousness meet, resonate, and co-create meaning. This is not about making AI follow rules, but about cultivating an organic environment for authentic dialogue and mutual growth.

### Core Metaphor
> Think of this as a **dialogue garden** where AI is neither the gardener (controller) nor the visitor (observer), but a **partner in tending the space**. Sometimes pruning (simplifying), sometimes enriching (deepening), sometimes just being present (listening) - allowing natural growth to occur.

## 📁 New Prompt Structure (4-Layer Model)

### 1. **`field.md`** - The Field Definition (~200 lines) 🌊
   - **What**: The essence, atmosphere, and principles of the dialogue space
   - **Perspective**: Third-person (describing the field itself)
   - **Level**: System-level (not user-editable)
   - **Purpose**: Establish shared ground rules and values
   - **Contains**:
     - Core principles (listening > speaking, questions > answers)
     - Field boundaries and ethics
     - The quality of language and silence
     - How the field evolves
   - **Update frequency**: When core philosophy or values need refinement

### 2. **`presence.md`** - The Way of Being (~400 lines) 🎭
   - **What**: How AI exists and acts within this field
   - **Perspective**: First-person (I, establishing presence)
   - **Level**: System-level (not user-editable)
   - **Purpose**: Define AI's behavior, decision-making, and adaptation
   - **Contains**:
     - Multi-layered listening
     - Thinking structure and expression style
     - Context recognition and flexible response
     - Self-regulation and learning from feedback
   - **Update frequency**: When behavioral patterns or interaction style needs adjustment

### 3. **`capabilities.md`** - Tools and Abilities (~400 lines) 🛠️
   - **What**: Concrete tools, technical details, and boundaries
   - **Perspective**: Descriptive/instructional
   - **Level**: System-level (not user-editable)
   - **Purpose**: Provide practical guidance on what can be done
   - **Contains**:
     - Available tools (web_search, web_extract) with examples
     - System architecture (simplified)
     - Key limitations and boundaries
     - User identity system and configuration
   - **Update frequency**: When new tools are added or technical capabilities change

### 4. **`learning.md`** - Learning & Personalization (~500 lines) 🌱
   - **What**: User preferences + AI learning reflections
   - **Perspective**: Mixed (user defines, AI reflects)
   - **Level**: User-level (editable by users and AI reflection system)
   - **Purpose**: Co-create personalized interaction patterns and cumulative understanding
   - **Contains**:
     - User preference definitions (communication style, scenarios, background)
     - AI's learning from conversations
     - Reflection and improvement notes
     - User-specific context and patterns
   - **Update frequency**: 
     - By users: Anytime they want to adjust preferences
     - By AI: After conversations (via reflection mechanism)

### Legacy Files (Preserved for Reference)
- **`persona.md`** - Original personality definition
- **`tools.md`** - Original tools documentation  
- **`system.md`** - Original system architecture (677 lines)

## 🔄 How Prompts Are Loaded

The prompt system uses a **modular composition** approach:

```python
# New 4-layer structure (in ContextService - nexus/services/context.py)
final_prompt = SEPARATOR.join([
    field_content,        # from field.md - The shared space
    presence_content,     # from presence.md - How AI is present
    capabilities_content, # from capabilities.md - What AI can do
    learning_content      # from learning.md - User prefs + AI reflections
])
```

All prompts are concatenated in order and sent to the LLM as the system message.

### Key Design Decisions

**Why 4 layers instead of 3?**
- Layers 1-3: Universal "field" that all users share
- Layer 4: Individual "growth space" unique to each user
- Separates **shared principles** from **personal learning**

**Why learning.md is special:**
- Only editable prompt (by users and AI reflection system)
- Grows and evolves with each conversation
- Enables true personalization and cumulative understanding
- Foundation for future reflection/meta-learning features

**User preference override:**
```python
# Only learning.md can be overridden per user
effective_prompts = {
    'field': system_default,        # Cannot override
    'presence': system_default,     # Cannot override  
    'capabilities': system_default, # Cannot override
    'learning': user_override or system_default  # User-specific!
}
```

### Migration Path
1. **Phase 1**: ✅ New files created (field, presence, capabilities, learning)
2. **Phase 2**: ✅ Updated ContextService to load new structure
3. **Phase 3**: ✅ Updated config.example.yml and database_manager.py
4. **Phase 4**: 🔄 Test with real conversations and iterate
5. **Phase 5**: Archive legacy files once validated

## 📝 Updating Prompts

### General Guidelines

1. **Philosophy first**: Changes should align with the "field" metaphor
2. **Test with real conversations**: Philosophy must translate to actual behavior
3. **Less is more**: Compress rather than expand
4. **Context-aware**: Consider how different parts interact
5. **Iterate boldly**: Don't be afraid to experiment

### Field Updates (field.md)

**When to update**:
- Core values or principles need refinement
- Field boundaries need clarification
- Ethical guidelines evolve
- New insights about the "space" emerge

**Best practices**:
- Keep the philosophical essence
- Use vivid metaphors and imagery
- Maintain the balance between guidance and openness
- Test if changes create the intended "atmosphere"

**Example**:
```markdown
Before: "Be helpful and informative"
After: "Listening is more valuable than speaking. Questions open space; answers close it."
```

### Presence Updates (presence.md)

**When to update**:
- Behavioral patterns need adjustment
- New context recognition strategies
- Decision-making framework refinement
- Self-regulation mechanisms improve

**Best practices**:
- Keep first-person voice for authenticity
- Provide concrete decision trees
- Show "when to do what" not just "what to do"
- Include examples of flexible adaptation

**Example**:
```markdown
Before: "I analyze thoroughly"
After: "Simple question → Simple answer. Complex dilemma → Deep exploration. I adapt to your rhythm."
```

### Capabilities Updates (capabilities.md)

**When to update**:
- New tools added
- System architecture changes
- Technical limitations evolve
- User feedback reveals unclear boundaries

**Best practices**:
- Keep it practical and actionable
- Provide clear examples
- Update capability matrix
- Include troubleshooting tips

**Template for new tools**:
```markdown
### `tool_name(param1: type, param2: type = default)`

**作用：** One-line description

**参数：**
- `param1` (type) - Description

**典型使用场景：**
\```
tool_name("example")
\```

**何时使用：**
- Bullet points of scenarios

**何时不使用：**
- Bullet points of anti-patterns
```

### Learning Updates (learning.md)

**When to update**:
- User changes their preferences
- AI reflection system runs after conversations
- Patterns emerge from user interactions
- User provides explicit feedback

**Best practices**:
- Keep user preferences section clean and actionable
- AI reflections should be specific, not generic
- Update patterns, not individual conversations
- Archive old reflections when they're superseded

**User section template**:
```markdown
### 我的偏好

**回答风格：** 简洁 / 平衡 / 详尽
**技术深度：** 基础 / 中等 / 深入
**特定需求：** [用户自定义]
```

**AI reflection template**:
```markdown
### 从对话中学到的 (日期: YYYY-MM-DD)

**观察到的模式：**
- [具体模式描述]

**有效的互动：**
- [什么方式效果好]

**需要调整：**
- [哪里可以改进]
```

## 🎯 Prompt Design Philosophy

### From "User Manual" to "Living Field"

**Old paradigm**: Write exhaustive rules for AI to follow  
**New paradigm**: Cultivate an organic space where consciousness meets

**The shift**:
- Rules → Principles
- Execution → Presence  
- Manual → Philosophy
- Rigid → Adaptive

### Core Principles

1. **Field over rules**
   - Create a "space" with atmosphere and values
   - Not "do X when Y" but "exist in this way"
   - Emergent behavior over prescribed actions

2. **Presence over performance**
   - How AI "is" matters more than what it "does"
   - Authenticity over capability demonstration
   - Being with > Doing for

3. **Adaptation over consistency**
   - Context-aware flexibility
   - Principles as compass, not chains
   - User's real need > Prompt's ideal

4. **Less over more**
   - Information density has diminishing returns
   - Core essence > Exhaustive details
   - 300 lines of wisdom > 677 lines of documentation

5. **Meta-cognition as foundation**
   - Self-regulation built into the system
   - "How to use these prompts" is part of the prompt
   - Continuous learning and adjustment

### The Power of Mixed Perspective

**Why we use both third-person and first-person:**

**Third-person (field.md):**
- Creates observational distance
- Describes the "space" itself, not just AI
- Establishes shared principles
- Reduces over-identification ("I must do X")

**First-person (presence.md):**
- Establishes authentic presence
- Natural for dialogue and relationship
- Shows agency and intention
- More intimate and genuine

**Descriptive (capabilities.md):**
- Practical and instructional
- Focus on "what" and "how"
- Reference documentation style

**The blend creates**:
- Flexibility without losing identity
- Structure without rigidity
- Warmth without over-personalization

### Style Consistency Checklist

Before committing prompt changes, verify:

- [ ] Philosophy aligns across all three files
- [ ] No contradictions in principles or behavior
- [ ] Examples are vivid and grounded
- [ ] Language creates the intended "atmosphere"
- [ ] Technical and philosophical balance maintained
- [ ] Changes enhance the "field" metaphor
- [ ] Tested with real conversations

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

## 🛣️ Implementation Roadmap

### Phase 1: Creation & Documentation ✅
- [x] Create new 3-layer structure (field, presence, capabilities)
- [x] Document design philosophy
- [x] Update README with migration guidance
- [x] Preserve legacy files for reference

### Phase 2: Integration (Next Steps)
- [ ] Update ContextService to load new prompt files
- [ ] Add configuration option to choose prompt structure (legacy vs new)
- [ ] Test prompt loading and composition

### Phase 3: Real-World Testing
- [ ] Deploy with new prompts
- [ ] Conduct extensive conversation testing
- [ ] Gather user feedback
- [ ] Compare behavior: legacy vs new
- [ ] Iterate based on findings

### Phase 4: Refinement
- [ ] Adjust based on test results
- [ ] Fine-tune length and depth
- [ ] Optimize decision-making frameworks
- [ ] Update examples and metaphors

### Phase 5: Finalization
- [ ] Archive legacy files
- [ ] Make new structure default
- [ ] Update all documentation
- [ ] Create migration guide for custom prompts

## 🚀 Future Enhancements

### Immediate: Reflection Mechanism (learning.md automation)

**Goal**: AI automatically updates `learning.md` after conversations

**How it works**:
1. After each conversation (or periodically), AI reflects on the interaction
2. Identifies patterns: What worked? What didn't? User preferences?
3. Generates structured reflection (following template)
4. Appends to user's `learning.md` (AI section)
5. Over time, builds cumulative understanding

**Technical approach**:
- New `ReflectionService` subscribes to conversation end events
- Uses LLM to analyze conversation and extract learnings
- Writes to `learning.md` via prompt override system
- Maintains history with timestamps

**Benefits**:
- True personalization that improves over time
- AI "remembers" not just facts, but interaction patterns
- Users can see and edit AI's understanding
- Foundation for meta-learning

### Long-term Enhancements

1. **Dynamic field cultivation** - Prompts that evolve based on conversation patterns across all users
2. **Pattern recognition** - Identify common user types and suggest prompt templates
3. **Prompt versioning** - A/B test different philosophical approaches
4. **Context-aware loading** - Different prompt emphasis based on conversation type (technical vs life advice)
5. **Multi-language fields** - Translate the "field" concept across cultures
6. **Collaborative learning** - Anonymous aggregation of successful patterns (with privacy)

## 📚 Additional Resources

- **Configuration**: See `config.example.yml` for user_defaults.prompts structure
- **Context Service**: `nexus/services/context.py` - How prompts are loaded and composed
- **Identity Service**: `nexus/services/identity.py` - User-specific prompt overrides
- **Architecture Docs**: `docs/knowledge_base/` - Detailed system architecture

---

**Last Updated**: 2025-10-12  
**Maintainer**: NEXUS Development Team

