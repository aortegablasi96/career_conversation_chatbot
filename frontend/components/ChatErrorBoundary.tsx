"use client";

import { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

export default class ChatErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ChatWindow error:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-dvh items-center justify-center bg-black text-white">
          <div className="text-center space-y-3 px-6">
            <p className="text-lg font-medium text-white/80">
              Something went wrong displaying the chat.
            </p>
            <button
              onClick={() => this.setState({ hasError: false })}
              className="px-5 py-2 rounded-xl bg-white/10 hover:bg-white/20 border border-white/10 text-sm text-white transition"
            >
              Try again
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
