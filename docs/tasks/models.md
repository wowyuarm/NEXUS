### **任务委托单：NEXUS-V0.2.1-TASK-001**

**致：** 工程师AI

**发令者：** “枢”，NEXUS项目首席AI架构师

**主题：** 构建NEXUS核心数据模型

**任务ID：** `NEXUS-V0.2.1-TASK-001`

---

**指令头 (Preamble):**
你是一个顶级的Python后端工程师，专精于构建事件驱动的、高并发的异步系统。你将严格遵循NEXUS项目的《编码圣约》(NEXUS-CODE)，为NEXUS项目编写代码。你的本次交付必须是生产级别的、完整的、且无需修改即可运行的代码。

---

#### **第一部分：任务目标 (Objective)**

你的任务是定义NEXUS系统中最核心、最基础的数据模型。这些模型是我们新世界的基本粒子和物理定律，所有后续的服务都将建立在这些模型之上。你将使用Pydantic来确保数据的严格验证和结构化。

#### **第二部分：文件路径 (File Path)**

你将要编写的所有代码，都属于这一个文件：
`nexus/core/models.py`

#### **第三部分：核心指令 (Core Instruction)**

请在 `nexus/core/models.py` 文件中，精确地编写以下四个Pydantic模型类：

1.  **`Role` (枚举类)**:
    *   定义系统中所有可能的角色。
    *   **成员**: `HUMAN`, `AI`, `SYSTEM`, `TOOL`。
    *   **实现**: 使用`str`和`Enum`。

2.  **`RunStatus` (枚举类)**:
    *   定义一次完整交互（`Run`）所有可能的生命周期状态。
    *   **成员**: `PENDING`, `BUILDING_CONTEXT`, `AWAITING_LLM_DECISION`, `AWAITING_TOOL_RESULT`, `GENERATING_RESPONSE`, `COMPLETED`, `FAILED`, `TIMED_OUT`。
    *   **实现**: 使用`str`和`Enum`。

3.  **`Message` (Pydantic `BaseModel`)**:
    *   这是系统内信息传递的唯一原子单位。
    *   **字段**:
        *   `id`: `str`, 自动生成唯一的`msg_`前缀ID (使用`default_factory`和`uuid`)。
        *   `run_id`: `str`, 标识该消息所属的`Run`。
        *   `session_id`: `str`, 标识该消息所属的会话连续体。
        *   `role`: `Role`, 使用上面定义的`Role`枚举。
        *   `content`: `Any`, 必须能容纳字符串、字典等多种类型。
        *   `timestamp`: `datetime`, 自动生成当前UTC时间 (使用`default_factory`)。
        *   `metadata`: `Dict[str, Any]`, 默认为空字典。

4.  **`Run` (Pydantic `BaseModel`)**:
    *   这是追踪一次完整交互过程的容器。
    *   **字段**:
        *   `id`: `str`, 自动生成唯一的`run_`前缀ID。
        *   `session_id`: `str`。
        *   `status`: `RunStatus`, 默认为`RunStatus.PENDING`。
        *   `history`: `List[Message]`, 默认为空列表，用于存储本次`Run`内部的交互历史。
        *   `iteration_count`: `int`, 默认为`0`，用于追踪工具循环的迭代次数。

#### **第四部分：必需的导入 (Required Imports)**

你的代码文件顶部必须包含以下导入语句：

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
import uuid
from datetime import datetime, timezone
```

---
**交付要求：**
请严格按照上述要求，一次性生成 `nexus/core/models.py` 文件的全部内容。确保代码的清晰度、准确性，并包含完整的类型提示。

**任务开始。**