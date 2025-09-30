# 如何创建新的 NEXUS 指令

本指南提供了在 NEXUS 系统中创建新指令的完整步骤和最佳实践。

---

## 📋 概述

NEXUS 指令系统采用**自动发现机制**，只需在 `nexus/commands/definition/` 目录下创建符合规范的 Python 模块，系统启动时会自动注册。

### 核心原则

1. **后端是唯一事实来源**：所有指令的定义和元数据由后端声明
2. **执行位置透明**：通过 `execution_target` 明确指令在客户端或服务器端执行
3. **自动发现**：无需手动注册，符合规范即可被系统识别

---

## 🚀 快速开始

### 最小化示例

创建文件 `nexus/commands/definition/your_command.py`：

```python
"""
Your command description.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# 指令定义（必需）
COMMAND_DEFINITION = {
    "name": "your_command",
    "description": "Brief description of what this command does",
    "usage": "/your_command",
    "execution_target": "server",  # 'server' 或 'client'
    "examples": [
        "/your_command"
    ]
}

# 执行函数（必需）
async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the command.
    
    Args:
        context: Execution context containing services and metadata
    
    Returns:
        Dict with status, message, and optional data
    """
    logger.info(f"{COMMAND_DEFINITION['name']} command executed")
    
    # Your implementation here
    result = {
        "status": "success",
        "message": "Command executed successfully"
    }
    
    return result
```

---

## 📐 指令定义规范

### COMMAND_DEFINITION 字段

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `name` | `str` | ✅ | 指令名称（不含 `/` 前缀） |
| `description` | `str` | ✅ | 指令的简短描述 |
| `usage` | `str` | ✅ | 使用示例（含 `/` 前缀） |
| `execution_target` | `str` | ✅ | `"server"` 或 `"client"` |
| `examples` | `List[str]` | ✅ | 使用示例列表 |
| `parameters` | `Dict` | ❌ | 参数定义（未来支持） |

### execution_target 选择指南

#### 选择 `"server"`（服务器端执行）

- 需要访问数据库
- 需要调用其他服务（LLM、工具等）
- 需要后端业务逻辑处理
- 涉及敏感操作或权限控制

**示例**：`/ping`, `/help`, `/search`

#### 选择 `"client"`（客户端执行）

- 仅操作前端状态（如清空消息）
- 纯 UI 交互（如切换主题）
- 不需要后端数据或服务

**示例**：`/clear`

> ⚠️ **重要**：即使是客户端指令，也**必须**在后端创建定义文件。这是为了：
> 1. 维护"后端是唯一事实来源"原则
> 2. 确保 `/help` 指令能查询到完整的指令列表
> 3. 保证架构的形式完备性

---

## 🔧 execute 函数规范

### 函数签名

```python
async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
```

### context 参数

`context` 字典包含以下内容：

| 键 | 类型 | 说明 |
|-----|------|------|
| `command_name` | `str` | 当前指令名称 |
| `command_definitions` | `Dict` | 所有已注册指令的定义 |
| `database_service` | `DatabaseService` | 数据库服务实例 |
| 其他服务 | 各类型 | 根据 `CommandService` 初始化时注入 |

### 返回值规范

#### 成功响应

```python
{
    "status": "success",
    "message": "Human-readable success message",
    "data": {  # 可选
        "key": "value"
    }
}
```

#### 错误响应

```python
{
    "status": "error",
    "message": "Human-readable error message"
}
```

> 💡 **提示**：优先使用 `raise RuntimeError("message")` 抛出异常，`CommandService` 会自动捕获并格式化错误响应。

---

## 📝 完整示例

### 示例 1：服务器端指令（查询数据库）

```python
"""
Stats command - Display system statistics.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

COMMAND_DEFINITION = {
    "name": "stats",
    "description": "Display system statistics and metrics",
    "usage": "/stats",
    "execution_target": "server",
    "examples": [
        "/stats"
    ]
}

async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve and display system statistics.
    """
    try:
        logger.info("Stats command executed")
        
        # Access database service from context
        db_service = context.get('database_service')
        if not db_service:
            raise RuntimeError("Database service not available")
        
        # Perform database operations
        total_sessions = await db_service.count_documents('sessions')
        total_messages = await db_service.count_documents('messages')
        
        # Format response
        stats_message = f"""
📊 **System Statistics**

- Total Sessions: {total_sessions}
- Total Messages: {total_messages}
- Uptime: 99.9%
"""
        
        result = {
            "status": "success",
            "message": stats_message.strip(),
            "data": {
                "sessions": total_sessions,
                "messages": total_messages
            }
        }
        
        logger.info("Stats command completed successfully")
        return result
        
    except Exception as e:
        error_msg = f"Stats command failed: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
```

### 示例 2：客户端指令（声明性定义）

```python
"""
Theme command - Switch UI theme (client-side only).
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

COMMAND_DEFINITION = {
    "name": "theme",
    "description": "Toggle between light and dark theme",
    "usage": "/theme",
    "execution_target": "client",
    "examples": [
        "/theme"
    ]
}

async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    This command should not be executed on server.
    
    The execute function exists for architectural completeness but will
    raise an error if called, as theme switching is a client-side operation.
    """
    logger.warning("Theme command executed on server - should be client-side")
    
    raise RuntimeError(
        "Theme command should be executed on the client side. "
        "This indicates a routing error in the command dispatch system."
    )
```

---

## 🧪 测试指南

### 1. 创建测试文件

在 `tests/commands/` 目录下创建对应的测试文件：

```python
# tests/commands/test_your_command.py

import pytest
from nexus.services.command import CommandService
from nexus.core.bus import NexusBus

@pytest.mark.asyncio
async def test_your_command_execution():
    """Test your command executes successfully."""
    bus = NexusBus()
    command_service = CommandService(bus)
    
    # Verify command is registered
    assert command_service.is_command_registered('your_command')
    
    # Execute command
    context = command_service._build_execution_context('your_command')
    executor = command_service._command_registry['your_command']
    result = await executor(context)
    
    # Verify result
    assert result['status'] == 'success'
    assert 'message' in result
```

### 2. 运行测试

```bash
# 运行单个测试
pytest tests/commands/test_your_command.py -v

# 运行所有指令测试
pytest tests/commands/ -v
```

---

## ✅ 检查清单

在提交新指令之前，确保：

- [ ] 文件位于 `nexus/commands/definition/` 目录
- [ ] 包含符合规范的 `COMMAND_DEFINITION`
- [ ] 包含 `async def execute(context)` 函数
- [ ] `execution_target` 设置正确
- [ ] 添加了详细的文档字符串
- [ ] 包含适当的日志记录
- [ ] 错误处理完善（使用异常或返回错误状态）
- [ ] 创建了对应的测试文件
- [ ] 测试通过
- [ ] 无 linter 错误

---

## 🔄 系统工作流程

### 启动时自动注册

```
1. NEXUS 启动
2. CommandService 初始化
3. 扫描 nexus/commands/definition/ 目录
4. 导入所有模块
5. 提取 COMMAND_DEFINITION 和 execute 函数
6. 注册到内部注册表
7. 订阅 SYSTEM_COMMAND 总线主题
```

### 前端自动学习

```
1. AURA 启动
2. useCommandLoader 调用 /help
3. 后端返回所有指令元数据
4. 前端缓存到 commandStore
5. CommandPalette 显示可用指令
```

### 用户执行流程

```
1. 用户输入 / 触发 CommandPalette
2. 选择指令并执行
3. chatStore.executeCommand 分发
4. 根据 execution_target 路由：
   - client: 前端直接处理
   - server: WebSocket 发送到后端
5. 后端 CommandService 执行
6. 返回结果更新 UI
```

---

## 🎯 最佳实践

### 1. 命名规范

- 使用小写字母和下划线：`my_command`
- 避免与现有指令冲突
- 名称应简短且语义明确

### 2. 日志记录

```python
logger.info(f"{COMMAND_DEFINITION['name']} command executed")  # 开始
logger.debug("Processing step X")  # 中间步骤
logger.info("Command completed successfully")  # 成功
logger.error(f"Command failed: {error}")  # 失败
```

### 3. 错误处理

```python
try:
    # Your logic
    result = {"status": "success", "message": "..."}
    return result
except SpecificError as e:
    logger.error(f"Specific error: {e}")
    raise RuntimeError(f"User-friendly error message: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise RuntimeError("An unexpected error occurred")
```

### 4. 性能考虑

- 服务器端指令应避免长时间阻塞操作
- 对于耗时任务，考虑使用异步处理或后台任务
- 合理使用缓存减少数据库查询

---

## 🐛 故障排查

### 指令未被识别

**症状**：执行指令时提示 "Unknown command"

**排查步骤**：
1. 确认文件在 `nexus/commands/definition/` 目录
2. 检查 `COMMAND_DEFINITION` 拼写是否正确
3. 检查 `execute` 函数是否存在
4. 查看服务器启动日志中的注册信息
5. 重启 NEXUS 服务

### 客户端指令在服务器执行

**症状**：客户端指令产生了服务器往返延迟

**解决方案**：
- 检查前端是否正确获取了指令元数据
- 验证 `execution_target` 是否为 `"client"`
- 清空前端缓存并重新加载

### 指令执行失败

**症状**：返回错误状态或抛出异常

**排查步骤**：
1. 检查后端日志中的错误堆栈
2. 验证 `context` 中所需服务是否可用
3. 确认数据库连接正常
4. 检查权限和配置

---

## 📚 参考资料

### 现有指令示例

- `ping.py` - 简单的服务器端指令
- `help.py` - 访问 context 中的 command_definitions
- `clear.py` - 客户端指令的声明性定义

### 相关文档

- `nexus/services/command.py` - CommandService 实现
- `docs/tasks/command.md` - 指令系统设计文档
- `aura/src/features/chat/store/chatStore.ts` - 前端执行逻辑

---

## 💡 常见问题

**Q: 可以创建带参数的指令吗？**
A: 当前版本暂不支持参数解析，但可以在 `COMMAND_DEFINITION` 中预留 `parameters` 字段，为未来扩展做准备。

**Q: 客户端指令必须在后端定义吗？**
A: 是的。这确保了架构的形式完备性和"后端是唯一事实来源"原则。

**Q: 如何访问当前用户的 session_id？**
A: 通过 `context` 中的相关服务获取，具体实现取决于你的需求。

**Q: 指令可以调用其他指令吗？**
A: 理论上可以，但不推荐。每个指令应保持独立性和单一职责。

---

## 📞 支持

如有问题或建议，请：
- 查看现有指令源码作为参考
- 查阅系统架构文档
- 联系开发团队

---

**最后更新**: 2025-09-30
**版本**: 1.0
**维护者**: NEXUS Team
