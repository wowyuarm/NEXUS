// src/features/chat/index.tsx
// Chat functionality modules entry point
//
// Responsibilities:
// - Export main components of chat functionality
// - Provide unified external interface
// - Maintain backward compatibility (ChatView alias)
//
// Architecture description:
// - ChatContainer: Logic container, responsible for state management and business logic
// - ChatView: Pure display component, responsible for UI rendering and user interaction
// - Maintain API stability through alias exports

export { ChatContainer as ChatView } from './ChatContainer';
