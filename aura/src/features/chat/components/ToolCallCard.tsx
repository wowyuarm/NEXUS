/**
 * ToolCallCard Component - Tool Call Status Visualization
 * 
 * A specialized component for displaying tool call states with liquid glass material design.
 * Features dynamic animations, status indicators, and optional expandable content.
 * 
 * Design Language: Liquid Glass
 * - Semi-transparent background with backdrop blur
 * - Subtle borders and diffused shadows
 * - Organic animations reflecting tool execution state
 * - Grayscale-only color palette
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Check, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ToolCall } from '../store/auraStore';

// Animation constants
const ANIMATION_DURATIONS = {
  SPIN: 1,
  GLOW: 2,
  SCALE: 0.3,
  EXPAND: 0.3,
  CHEVRON: 0.2,
  FADE_IN: 0.4
} as const;

// Status text mapping
const STATUS_TEXT = {
  running: 'Executing...',
  completed: 'Completed',
  error: 'Failed'
} as const;

interface ToolCallCardProps {
  toolCall: ToolCall;
}

export const ToolCallCard: React.FC<ToolCallCardProps> = ({ toolCall }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // Status icon rendering with unified structure
  const renderStatusIcon = () => {
    if (toolCall.status === 'running') {
      return (
        <motion.div
          className="w-4 h-4 border-2 border-border rounded-full relative"
          animate={{ rotate: 360 }}
          transition={{
            duration: ANIMATION_DURATIONS.SPIN,
            repeat: Infinity,
            ease: 'linear'
          }}
        >
          <div className="absolute inset-0 border-2 border-transparent border-t-foreground rounded-full" />
        </motion.div>
      );
    }

    // Unified structure for completed/error states
    const IconComponent = toolCall.status === 'completed' ? Check : X;

    return (
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ duration: ANIMATION_DURATIONS.SCALE, ease: 'easeOut' }}
        className="w-4 h-4 rounded-full border border-border flex items-center justify-center"
      >
        <IconComponent className="w-2.5 h-2.5 text-foreground" />
      </motion.div>
    );
  };

  // Liquid glow animation for running state
  const glowAnimation = toolCall.status === 'running' ? {
    boxShadow: [
      '0 0 0 0 rgba(255, 255, 255, 0.1)',
      '0 0 0 8px rgba(255, 255, 255, 0.05)',
      '0 0 0 0 rgba(255, 255, 255, 0.1)'
    ]
  } : {};

  const glowTransition = toolCall.status === 'running' ? {
    duration: ANIMATION_DURATIONS.GLOW,
    repeat: Infinity,
    ease: 'easeInOut' as const
  } : {};

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ 
        opacity: 1, 
        y: 0,
        ...glowAnimation
      }}
      transition={{
        opacity: { duration: ANIMATION_DURATIONS.FADE_IN, ease: 'easeOut' },
        y: { duration: ANIMATION_DURATIONS.FADE_IN, ease: 'easeOut' },
        boxShadow: glowTransition
      }}
      className={cn(
        // Liquid Glass Material
        'bg-card/75 backdrop-blur-xl',
        'border border-border',
        'shadow-lg shadow-black/20',
        'rounded-2xl p-4',
        
        // Layout
        'mb-3 last:mb-0',
        
        // Interactive
        'cursor-pointer transition-all duration-300',
        'hover:bg-card/85'
      )}
      onClick={() => setIsExpanded(!isExpanded)}
    >
      {/* Header: Tool name and status */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {renderStatusIcon()}
          <div>
            <div className="text-sm font-medium text-foreground">
              {toolCall.toolName}
            </div>
            <div className="text-xs text-secondary-foreground">
              {STATUS_TEXT[toolCall.status]}
            </div>
          </div>
        </div>
        
        {/* Expand/Collapse indicator */}
        <motion.div
          animate={{ rotate: isExpanded ? 180 : 0 }}
          transition={{ duration: ANIMATION_DURATIONS.CHEVRON }}
          className="text-secondary-foreground"
        >
          <ChevronDown className="w-4 h-4" />
        </motion.div>
      </div>

      {/* Expandable content: Arguments and Results */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: ANIMATION_DURATIONS.EXPAND, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="pt-4 space-y-3">
              {/* Arguments */}
              {Object.keys(toolCall.args).length > 0 && (
                <div>
                  <div className="text-xs font-medium text-secondary-foreground mb-2">
                    Arguments
                  </div>
                  <div className="bg-muted/40 rounded-lg p-3">
                    <pre className="text-xs text-foreground font-mono whitespace-pre-wrap break-words">
                      {JSON.stringify(toolCall.args, null, 2)}
                    </pre>
                  </div>
                </div>
              )}

              {/* Result */}
              {toolCall.result && (
                <div>
                  <div className="text-xs font-medium text-secondary-foreground mb-2">
                    Result
                  </div>
                  <div className="bg-muted/40 rounded-lg p-3">
                    <div className="text-xs text-foreground whitespace-pre-wrap break-words">
                      {toolCall.result}
                    </div>
                  </div>
                </div>
              )}

              {/* Timing info */}
              <div className="flex justify-between text-xs text-secondary-foreground pt-2 border-t border-border/50">
                <span>Started: {toolCall.startTime.toLocaleTimeString()}</span>
                {toolCall.endTime && (
                  <span>
                    Duration: {Math.round((toolCall.endTime.getTime() - toolCall.startTime.getTime()) / 1000)}s
                  </span>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};
