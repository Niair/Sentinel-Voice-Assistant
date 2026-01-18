"use client";

import { useEffect, useRef, useState } from "react";

export function useMessages({ status }: { status: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [hasSentMessage, setHasSentMessage] = useState(false);

  const scrollToBottom = (behavior: ScrollBehavior = "smooth") => {
    endRef.current?.scrollIntoView({ behavior });
  };

  useEffect(() => {
    if (status === "streaming") {
      setHasSentMessage(true);
      if (isAtBottom) {
        scrollToBottom();
      }
    }
  }, [status, isAtBottom]);

  const onViewportEnter = () => {
    setIsAtBottom(true);
  };

  const onViewportLeave = () => {
    setIsAtBottom(false);
  };

  return {
    containerRef,
    endRef,
    isAtBottom,
    scrollToBottom,
    hasSentMessage,
    onViewportEnter,
    onViewportLeave,
  };
}