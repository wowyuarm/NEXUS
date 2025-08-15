// src/features/chat/data/mockData.ts
import type { Message } from '../types';
import { v4 as uuidv4 } from 'uuid';

/**
 * 模拟对话数据
 * 用于前端开发和测试界面效果
 */
export const mockMessages: Message[] = [
  {
    id: uuidv4(),
    role: 'yu',
    content: '你好，曦。今天想和你聊聊AI的未来发展。',
    timestamp: new Date(Date.now() - 300000).toISOString(), // 5分钟前
  },
  {
    id: uuidv4(),
    role: 'xi',
    content: '你好，禹。很高兴与你探讨这个话题。✨\n\nAI的未来发展确实是一个令人兴奋的领域。我认为有几个关键方向值得关注：\n\n## 主要发展趋势\n\n1. **多模态融合**：未来的AI将能够同时处理文本、图像、音频、视频等多种模态的信息\n2. **推理能力提升**：从简单的模式匹配向真正的逻辑推理和创造性思维发展\n3. **个性化适应**：AI将更好地理解和适应每个用户的独特需求和偏好\n\n你对哪个方向最感兴趣呢？',
    timestamp: new Date(Date.now() - 280000).toISOString(),
  },
  {
    id: uuidv4(),
    role: 'yu',
    content: '我特别关注AI的推理能力。能给我展示一些代码示例吗？',
    timestamp: new Date(Date.now() - 240000).toISOString(),
  },
  {
    id: uuidv4(),
    role: 'xi',
    content: '当然！让我为你展示一个AI推理的简单示例：\n\n```python\nclass ReasoningEngine:\n    def __init__(self):\n        self.knowledge_base = {}\n        self.rules = []\n    \n    def add_fact(self, fact: str, confidence: float = 1.0):\n        """添加事实到知识库"""\n        self.knowledge_base[fact] = confidence\n    \n    def add_rule(self, premise: str, conclusion: str, weight: float = 1.0):\n        """添加推理规则"""\n        self.rules.append({\n            \'premise\': premise,\n            \'conclusion\': conclusion,\n            \'weight\': weight\n        })\n    \n    def infer(self, query: str) -> float:\n        """基于知识库和规则进行推理"""\n        if query in self.knowledge_base:\n            return self.knowledge_base[query]\n        \n        # 应用推理规则\n        for rule in self.rules:\n            if rule[\'premise\'] in self.knowledge_base:\n                confidence = self.knowledge_base[rule[\'premise\']] * rule[\'weight\']\n                if rule[\'conclusion\'] == query:\n                    return confidence\n        \n        return 0.0\n\n# 使用示例\nengine = ReasoningEngine()\nengine.add_fact("天空是蓝色的", 0.9)\nengine.add_rule("天空是蓝色的", "今天天气不错", 0.7)\n\nresult = engine.infer("今天天气不错")\nprint(f"推理结果置信度: {result}")  # 输出: 0.63\n```\n\n这个例子展示了基础的符号推理。现代AI还会结合神经网络进行更复杂的推理。',
    timestamp: new Date(Date.now() - 180000).toISOString(),
  },
  {
    id: uuidv4(),
    role: 'yu',
    content: '很有趣！那么在实际应用中，AI推理面临哪些挑战？',
    timestamp: new Date(Date.now() - 120000).toISOString(),
  },
  {
    id: uuidv4(),
    role: 'xi',
    content: '[正在使用我的能力...🛠️]\n\n根据我的分析，AI推理在实际应用中面临以下主要挑战：\n\n### 技术挑战\n\n- **不确定性处理**：现实世界充满不确定性，如何在不完整信息下做出合理推理\n- **常识推理**：人类的常识对AI来说往往是最难掌握的\n- **因果关系理解**：区分相关性和因果性，理解事件之间的真正关系\n\n### 实践挑战\n\n- **可解释性**：AI的推理过程需要对人类透明和可理解\n- **鲁棒性**：面对对抗性输入或边缘情况时保持稳定性能\n- **伦理考量**：确保推理结果符合人类价值观和道德标准\n\n### 未来方向\n\n我认为**神经符号结合**是一个很有前景的方向，它结合了神经网络的学习能力和符号推理的逻辑性。\n\n你在工作中遇到过类似的推理挑战吗？',
    timestamp: new Date(Date.now() - 60000).toISOString(),
  }
];

/**
 * 获取模拟消息的函数
 * 可以根据需要返回不同数量的消息
 */
export const getMockMessages = (count?: number): Message[] => {
  if (count && count < mockMessages.length) {
    return mockMessages.slice(0, count);
  }
  return mockMessages;
};

/**
 * 创建新的模拟消息
 */
export const createMockMessage = (role: 'yu' | 'xi' | 'system', content: string): Message => {
  return {
    id: uuidv4(),
    role,
    content,
    timestamp: new Date().toISOString(),
  };
};
