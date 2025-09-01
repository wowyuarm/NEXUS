### **任务委托单：NEXUS-V0.2.1-TASK-002**

**致：** 工程师AI

**发令者：** “枢”，NEXUS项目首席AI架构师

**主题：** 构建NEXUS事件总线 (NexusBus)

**任务ID：** `NEXUS-V0.2.1-TASK-002`

---

**指令头 (Preamble):**
你是一个顶级的Python后端工程师，专精于构建事件驱动的、高并发的异步系统。你将严格遵循NEXUS项目的《编码圣约》，为NEXUS项目编写代码。你的本次交付必须是生产级别的、完整的、且无需修改即可运行的代码。

---

#### **第一部分：任务目标 (Objective)**

你的任务是实现`NexusBus`类，这是整个NEXUS系统内部所有服务进行通信的唯一通道。它必须是异步的、非阻塞的，并能支持一个主题（topic）被多个订阅者（subscriber）监听。

#### **第二部分：文件路径 (File Path)**

你将要编写的所有代码，都属于这一个文件：
`nexus/core/bus.py`

#### **第三部分：核心指令 (Core Instruction)**

请在 `nexus/core/bus.py` 文件中，编写`NexusBus`类。

**类的结构与方法**:

1.  **`__init__(self)`**:
    *   初始化两个私有成员变量：
        *   `_queues`: 一个类型为 `Dict[str, asyncio.Queue]` 的字典，用于存储每个主题的消息队列。
        *   `_subscribers`: 一个类型为 `Dict[str, List[Callable[[Message], Awaitable[None]]]]` 的字典，用于存储每个主题的所有订阅者回调函数。

2.  **`publish(self, topic: str, message: Message)` (异步方法)**:
    *   接收一个`topic`字符串和一个`Message`对象。
    *   如果该`topic`存在于`_queues`中，则将`message`放入对应的`asyncio.Queue`。

3.  **`subscribe(self, topic: str, handler: Callable[[Message], Awaitable[None]])` (同步方法)**:
    *   接收一个`topic`字符串和一个异步的回调函数`handler`。
    *   如果`topic`对应的队列不存在，则创建一个新的`asyncio.Queue`。
    *   如果`topic`对应的订阅者列表不存在，则创建一个新的`list`。
    *   将`handler`添加到该`topic`的订阅者列表中。

4.  **`run_forever(self)` (异步方法)**:
    *   这是启动事件总线监听循环的主方法。
    *   它应该遍历`_queues`字典中的所有队列。
    *   为每一个队列创建一个独立的、永久运行的监听任务（使用`asyncio.create_task`）。
    *   使用`asyncio.gather`来并发运行所有这些监听任务。

5.  **`_listener(self, topic: str, queue: asyncio.Queue)` (私有异步方法)**:
    *   这是一个被`run_forever`调用的辅助方法，用于监听单个队列。
    *   它在一个无限循环中，从`queue`中异步地获取（`await queue.get()`）消息。
    *   每当获取到一个消息，它就遍历该`topic`对应的所有订阅者`handler`。
    *   对于每一个`handler`，它都使用`asyncio.create_task(handler(message))`来**并发地、非阻塞地**执行回调，确保一个慢的订阅者不会影响其他订阅者。
    *   调用`queue.task_done()`。

#### **第四部分：必需的导入 (Required Imports)**

你的代码文件顶部必须包含以下导入语句：

```python
import asyncio
from typing import Dict, List, Callable, Awaitable
from .models import Message
```

---
**交付要求：**
请严格按照上述要求，一次性生成 `nexus/core/bus.py` 文件的全部内容。确保代码的健壮性、异步正确性，并包含清晰的文档字符串和类型提示。

**任务开始。**