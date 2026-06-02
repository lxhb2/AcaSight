import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import i18next from 'i18next';

interface ErrorEntry {
  id: string;
  timestamp: number;
  type: 'render' | 'promise' | 'runtime' | 'custom';
  message: string;
  stack?: string;
  componentStack?: string;
  metadata?: Record<string, unknown>;
}

const errorStore: ErrorEntry[] = [];
const MAX_STORED = 100;
const listeners: Array<() => void> = [];

function pushError(entry: ErrorEntry) {
  errorStore.unshift(entry);
  if (errorStore.length > MAX_STORED) errorStore.length = MAX_STORED;
  listeners.forEach(fn => fn());
}

export const errorTracker = {
  capture(type: ErrorEntry['type'], message: string, stack?: string, metadata?: Record<string, unknown>) {
    const entry: ErrorEntry = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      timestamp: Date.now(),
      type,
      message,
      stack,
      metadata,
    };
    pushError(entry);
    return entry;
  },
  getAll(): ErrorEntry[] {
    return [...errorStore];
  },
  getRecent(count = 10): ErrorEntry[] {
    return errorStore.slice(0, count);
  },
  clear() {
    errorStore.length = 0;
    listeners.forEach(fn => fn());
  },
  subscribe(fn: () => void) {
    listeners.push(fn);
    return () => {
      const idx = listeners.indexOf(fn);
      if (idx >= 0) listeners.splice(idx, 1);
    };
  },
};

if (typeof window !== 'undefined') {
  window.addEventListener('error', (event: ErrorEvent) => {
    errorTracker.capture('runtime', event.message, event.error?.stack, {
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
    });
  });

  window.addEventListener('unhandledrejection', (event: PromiseRejectionEvent) => {
    const message = event.reason instanceof Error ? event.reason.message : String(event.reason);
    const stack = event.reason instanceof Error ? event.reason.stack : undefined;
    errorTracker.capture('promise', message, stack);
  });
}

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[ErrorBoundary] Caught:', error, errorInfo);
    errorTracker.capture('render', error.message, error.stack ?? undefined, {
      componentStack: errorInfo.componentStack,
    });
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 32,
          height: '100%',
          gap: 12,
          color: 'var(--text-primary)',
        }}>
          <AlertTriangle size={32} style={{ color: 'var(--text-error, #ef4444)' }} />
          <h3 style={{ margin: 0, fontSize: 16 }}>{i18next.t('errorBoundary.title')}</h3>
          <p style={{
            margin: 0,
            fontSize: 13,
            color: 'var(--text-secondary)',
            maxWidth: 360,
            textAlign: 'center',
            wordBreak: 'break-word',
          }}>
            {this.state.error?.message || i18next.t('errorBoundary.unknownError')}
          </p>
          <button
            onClick={this.handleRetry}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              marginTop: 8,
              padding: '6px 16px',
              borderRadius: 6,
              border: '1px solid var(--border-color)',
              background: 'var(--bg-secondary)',
              color: 'var(--text-primary)',
              cursor: 'pointer',
              fontSize: 13,
            }}
          >
            <RefreshCw size={14} />
            {i18next.t('errorBoundary.retry')}
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
