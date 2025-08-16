// src/features/chat/hooks/useChat.ts
// 聊天Hook - 支持真实连接和模拟模式的双模式工作流
import { useEffect, useRef } from 'react';
import { useChatStore } from '../store/chatStore';
import wsManager from '@/services/websocket/manager';
import type { Message } from '../types';
import type { XiSystemEvent } from '@/services/websocket/protocol';
import { isStreamStartEvent, isToolCallEvent, isToolExecutionStartEvent, isToolExecutionResultEvent, isTextChunkEvent, isStreamEndEvent, isErrorEvent } from '@/services/websocket/protocol';
import { v4 as uuidv4 } from 'uuid';
import { mockFlows, createDefaultMockFlow, type MockFlow } from '../data/mockResponses';

// 模拟事件发射器类
class MockEventEmitter {
  private callback: ((event: XiSystemEvent) => void) | null = null;

  onMessage(callback: (event: XiSystemEvent) => void) {
    this.callback = callback;
  }

  emit(event: XiSystemEvent) {
    if (this.callback) {
      this.callback(event);
    }
  }

  disconnect() {
    this.callback = null;
  }
}

export const useChat = () => {
  const { messages, addMessage, appendStreamChunk, setStreamFinished, setThinking, isThinking, hasStarted, setHasStarted } = useChatStore();
  const currentStreamId = useRef<string | null>(null);
  const mockEmitter = useRef<MockEventEmitter>(new MockEventEmitter());

  // 检查是否使用模拟数据模式
  const useMockData = import.meta.env.VITE_USE_MOCK_DATA === 'true';

  useEffect(() => {
    // 统一的事件处理函数 - 真实和模拟模式通用
    const handleEvent = (event: XiSystemEvent) => {
      console.log('Received event:', event.type, event);

      if (isStreamStartEvent(event)) {
        // 流开始事件 - 创建新的流式消息
        console.log('Stream started:', event.metadata.message_id);

        const newXiMessage: Message = {
          id: event.metadata.message_id,
          role: 'xi',
          content: '',
          timestamp: new Date().toISOString(),
          metadata: { isStreaming: true }
        };
        addMessage(newXiMessage);
        currentStreamId.current = event.metadata.message_id;
        return;
      }

      if (isToolCallEvent(event)) {
        // 工具调用事件 - 添加工具调用提示到当前流
        console.log('Tool call:', event.payload.tool_name);

        if (currentStreamId.current) {
          appendStreamChunk(currentStreamId.current, `[正在调用${event.payload.tool_name}...🛠️]`);
        }
        return;
      }

      if (isToolExecutionStartEvent(event)) {
        // 工具执行开始事件 - 显示工具执行状态
        console.log('Tool execution started:', event.payload.tool_name);

        if (currentStreamId.current) {
          appendStreamChunk(currentStreamId.current, `[正在执行${event.payload.tool_name}...⚡]`);
        }
        return;
      }

      if (isToolExecutionResultEvent(event)) {
        // 工具执行结果事件 - 显示执行结果状态
        console.log('Tool execution result:', event.payload.tool_name, event.payload.status);

        if (currentStreamId.current) {
          const status = event.payload.status === 'success' ? '✅' : '❌';
          const time = event.payload.execution_time.toFixed(2);
          appendStreamChunk(currentStreamId.current, `[${event.payload.tool_name}执行${event.payload.status === 'success' ? '成功' : '失败'} ${status} (${time}s)]`);
        }
        return;
      }

      if (isTextChunkEvent(event)) {
        // 文本块事件 - 立即追加到当前流式消息
        const chunk = event.payload.chunk;

        if (currentStreamId.current) {
          appendStreamChunk(currentStreamId.current, chunk);
        }
        return;
      }

      if (isStreamEndEvent(event)) {
        // 流结束事件 - 标记流式消息完成
        console.log('Stream ended');

        if (currentStreamId.current) {
          setStreamFinished(currentStreamId.current);
        }
        currentStreamId.current = null;
        setThinking(false);
        return;
      }

      if (isErrorEvent(event)) {
        // 错误事件 - 显示错误信息
        console.error('WebSocket error event:', event.payload.message);

        const errorMessage: Message = {
          id: uuidv4(),
          role: 'xi',
          content: `❌ 错误：${event.payload.message}`,
          timestamp: new Date().toISOString(),
        };
        addMessage(errorMessage);

        if (currentStreamId.current) {
          currentStreamId.current = null;
        }
        setThinking(false);
        return;
      }

      // 处理其他事件类型（如后台任务事件）
      console.log('Unhandled event type:', event.type);
    };

    if (useMockData) {
      // 模拟数据模式：使用模拟事件发射器
      console.log('模拟数据模式');
      mockEmitter.current.onMessage(handleEvent);
    } else {
      // 真实连接模式：连接WebSocket
      console.log('真实连接模式');
      wsManager.connect();
      wsManager.onMessage(handleEvent);
    }

    return () => {
      if (useMockData) {
        mockEmitter.current.disconnect();
      } else {
        wsManager.disconnect();
      }
    };
  }, [addMessage, appendStreamChunk, setThinking, useMockData]);

  const sendMessage = (text: string) => {
    // 如果这是第一次发送消息，设置 hasStarted 为 true
    if (!hasStarted) {
      setHasStarted(true);
    }

    const userMessage: Message = {
      id: uuidv4(),
      role: 'yu',
      content: text,
      timestamp: new Date().toISOString(),
    };
    addMessage(userMessage);
    setThinking(true);

    if (useMockData) {
      // 模拟数据模式：生成模拟响应
      simulateMockResponse(text);
    } else {
      // 正常模式：发送WebSocket消息
      wsManager.sendMessage({ yu_input: text });
    }
  };

  // 模拟协议事件流响应函数
  const simulateMockResponse = (userInput: string) => {
    const input = userInput.trim();

    // 获取对应的模拟事件流
    const mockFlow: MockFlow = mockFlows[input] || createDefaultMockFlow(input);

    // 按时间顺序发射事件
    let totalDelay = 0;
    const messageId = uuidv4();

    mockFlow.forEach((mockEvent) => {
      totalDelay += mockEvent.delay;

      setTimeout(() => {
        // 添加metadata到事件中
        const eventWithMetadata: XiSystemEvent = {
          ...mockEvent.event,
          metadata: {
            message_id: messageId,
            timestamp: new Date().toISOString(),
          }
        } as XiSystemEvent;

        mockEmitter.current.emit(eventWithMetadata);
      }, totalDelay);
    });
  };

  return { messages, sendMessage, isThinking, hasStarted };
};
