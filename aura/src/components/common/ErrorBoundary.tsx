// src/components/common/ErrorBoundary.tsx 
// React错误边界，优雅处理组件错误
import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="flex flex-col items-center justify-center min-h-[200px] text-center p-6">
          <div className="w-12 h-12 rounded-full bg-secondary/50 flex items-center justify-center mb-4">
            <div className="text-secondary-foreground text-lg">⚠</div>
          </div>
          <div className="text-base text-foreground mb-2">
            出现了一些问题
          </div>
          <div className="text-sm text-secondary-foreground leading-relaxed max-w-md">
            {this.state.error?.message || '请刷新页面重试'}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
