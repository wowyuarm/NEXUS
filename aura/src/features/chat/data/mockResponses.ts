// src/features/chat/data/mockResponses.ts
// 模拟响应数据 - 升级为协议事件流模拟

import type { XiSystemEvent } from '@/services/websocket/protocol';
import { v4 as uuidv4 } from 'uuid';

// 定义模拟事件流的类型
export interface MockEvent {
  delay: number;
  event: Omit<XiSystemEvent, 'metadata'>;
}

export type MockFlow = MockEvent[];

// 生成模拟事件的辅助函数
const createMockEvent = (type: string, payload: any, delay: number = 100): MockEvent => ({
  delay,
  event: { type, payload } as Omit<XiSystemEvent, 'metadata'>
});



// 模拟事件流定义
export const mockFlows: Record<string, MockFlow> = {
  '1': [ // 基础文本响应测试
    createMockEvent('stream_start', { session_id: uuidv4(), input_message_id: uuidv4() }, 100),
    createMockEvent('text_chunk', { chunk: '**基础文本响应测试** ✨\n\n这是一个基础的文本响应，用于测试：\n\n- 基本的Markdown渲染\n- 文本换行和段落\n- **粗体**和*斜体*效果\n- 列表项目显示\n\n界面渲染效果看起来不错！' }, 50),
    createMockEvent('stream_end', {}, 200),
  ],

  '2': [ // 工具调用模拟测试
    createMockEvent('stream_start', { session_id: uuidv4(), input_message_id: uuidv4() }, 100),
    createMockEvent('tool_call', { tool_name: 'web_search', arguments: { query: '工具调用测试' } }, 500),
    createMockEvent('text_chunk', { chunk: '**工具调用模拟测试**\n\n' }, 1500),
    createMockEvent('text_chunk', { chunk: '我正在使用搜索工具查找相关信息...\n\n' }, 400),
    createMockEvent('text_chunk', { chunk: '根据搜索结果，找到了以下内容：\n' }, 300),
    createMockEvent('text_chunk', { chunk: '- 🔍 搜索功能正常\n' }, 200),
    createMockEvent('text_chunk', { chunk: '- 📊 数据分析完成\n' }, 200),
    createMockEvent('text_chunk', { chunk: '- ✅ 工具调用动画效果测试成功\n\n' }, 200),
    createMockEvent('text_chunk', { chunk: '这个测试验证了工具调用提示的显示效果。' }, 300),
    createMockEvent('stream_end', {}, 200),
  ],

  '3': [ // 代码块渲染测试
    createMockEvent('stream_start', { session_id: uuidv4(), input_message_id: uuidv4() }, 100),
    createMockEvent('text_chunk', { chunk: '**代码块渲染测试** 💻\n\n' }, 500),
    createMockEvent('text_chunk', { chunk: '让我展示一些代码示例来测试语法高亮：\n\n' }, 400),
    createMockEvent('text_chunk', { chunk: '```python\n# Python 代码示例\nclass TestComponent:\n    def __init__(self, name):\n        self.name = name\n        self.status = \'active\'\n    \n    def render(self):\n        return f"Component {self.name} is {self.status}"\n\n# 创建实例\ncomponent = TestComponent("YX Nexus")\nprint(component.render())\n```\n\n' }, 800),
    createMockEvent('text_chunk', { chunk: '```javascript\n// JavaScript 代码示例\nconst testFunction = (data) => {\n  return data.map(item => ({\n    ...item,\n    processed: true\n  }));\n};\n```\n\n' }, 600),
    createMockEvent('text_chunk', { chunk: '代码高亮和格式化效果测试完成！' }, 300),
    createMockEvent('stream_end', {}, 200),
  ],

  '4': [ // 长文本滚动测试
    createMockEvent('stream_start', { session_id: uuidv4(), input_message_id: uuidv4() }, 100),
    createMockEvent('text_chunk', { chunk: '**长文本滚动测试** 📜\n\n' }, 500),
    createMockEvent('text_chunk', { chunk: '这是一个用于测试长文本滚动和渲染性能的响应。\n\n' }, 400),
    createMockEvent('text_chunk', { chunk: '## 第一部分：系统架构\n\n' }, 300),
    createMockEvent('text_chunk', { chunk: 'YX Nexus 采用了现代化的前端架构，包括：\n\n' }, 300),
    createMockEvent('text_chunk', { chunk: '### 技术栈\n- **前端框架**: React + TypeScript\n- **状态管理**: Zustand\n- **样式系统**: Tailwind CSS + shadcn/ui\n- **动画库**: Framer Motion\n- **构建工具**: Vite\n\n' }, 600),
    createMockEvent('text_chunk', { chunk: '### 设计理念\n1. **空间叙事**: 从虚无到流淌的界面转换\n2. **生命感交互**: 呼吸光晕和微妙动画\n3. **信息分层**: 默认简洁，交互揭示深度\n4. **架构即认知**: 结构反映思维模式\n\n' }, 600),
    createMockEvent('text_chunk', { chunk: '## 第二部分：核心功能\n\n' }, 300),
    createMockEvent('text_chunk', { chunk: '### 悬浮指令核心\n- 毛玻璃材质效果\n- 动态辉光边框\n- 聚焦状态增强\n- 响应式尺寸调整\n\n' }, 500),
    createMockEvent('text_chunk', { chunk: '### 宇宙漂流背景\n- 多层次动画系统\n- 智能状态控制\n- 性能优化实现\n- 沉浸式体验营造\n\n' }, 500),
    createMockEvent('text_chunk', { chunk: '### 生命光晕系统\n- 角色身份标识\n- 思考状态动画\n- 精确的光晕控制\n- 流式输出指示\n\n' }, 500),
    createMockEvent('text_chunk', { chunk: '## 第三部分：用户体验\n\n' }, 300),
    createMockEvent('text_chunk', { chunk: '这个长文本测试验证了：\n- 📱 响应式布局适配\n- 🎨 Markdown 渲染质量\n- ⚡ 滚动性能表现\n- 🎯 内容层次结构\n- ✨ 视觉效果一致性\n\n' }, 600),
    createMockEvent('text_chunk', { chunk: '测试完成！界面滚动和渲染效果良好。' }, 300),
    createMockEvent('stream_end', {}, 200),
  ],

  '5': [ // 表格和引用测试
    createMockEvent('stream_start', { session_id: uuidv4(), input_message_id: uuidv4() }, 100),
    createMockEvent('text_chunk', { chunk: '**表格和引用测试** 📊\n\n' }, 500),
    createMockEvent('text_chunk', { chunk: '> 这是一个引用块测试，用于验证引用样式的渲染效果。引用块应该有特殊的左边框和斜体样式。\n\n' }, 600),
    createMockEvent('text_chunk', { chunk: '下面是一个表格测试：\n\n' }, 300),
    createMockEvent('text_chunk', { chunk: '| 功能模块 | 状态 | 测试结果 | 备注 |\n|---------|------|----------|------|\n| 基础文本 | ✅ | 通过 | 渲染正常 |\n| 代码高亮 | ✅ | 通过 | 语法正确 |\n| 表格显示 | 🧪 | 测试中 | 当前项目 |\n| 引用块 | ✅ | 通过 | 样式正确 |\n| 列表项 | ✅ | 通过 | 缩进正常 |\n\n' }, 800),
    createMockEvent('text_chunk', { chunk: '### 链接测试\n这里有一个[测试链接](https://example.com)，用于验证链接样式。\n\n' }, 400),
    createMockEvent('text_chunk', { chunk: '### 分割线测试\n\n---\n\n' }, 300),
    createMockEvent('text_chunk', { chunk: '分割线上方和下方的内容应该有明显的视觉分隔。\n\n' }, 400),
    createMockEvent('text_chunk', { chunk: '**测试总结**: 表格、引用、链接等元素渲染效果良好！' }, 300),
    createMockEvent('stream_end', {}, 200),
  ],
};

// 默认响应生成函数
export const createDefaultMockFlow = (input: string): MockFlow => [
  createMockEvent('stream_start', { session_id: uuidv4(), input_message_id: uuidv4() }, 100),
  createMockEvent('text_chunk', { chunk: '**默认响应** 🤖\n\n' }, 500),
  createMockEvent('text_chunk', { chunk: `你输入了："${input}"\n\n` }, 300),
  createMockEvent('text_chunk', { chunk: '💡 **测试提示**：\n- 输入 **1** - 基础文本响应测试\n- 输入 **2** - 工具调用模拟测试\n- 输入 **3** - 代码块渲染测试\n- 输入 **4** - 长文本滚动测试\n- 输入 **5** - 表格和引用测试\n\n' }, 600),
  createMockEvent('text_chunk', { chunk: '每种测试都会展示不同的UI组件和动画效果，帮助验证界面的各项功能。\n\n' }, 400),
  createMockEvent('text_chunk', { chunk: '✨ 试试输入数字来体验不同的测试场景吧！' }, 300),
  createMockEvent('stream_end', {}, 200),
];
