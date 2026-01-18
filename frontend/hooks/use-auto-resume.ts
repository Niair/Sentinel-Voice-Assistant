"use client";

import { useEffect, useRef } from "react";
import type { ChatMessage } from "@/lib/types";

interface UseAutoResumeProps {
      autoResume: boolean;
      initialMessages: ChatMessage[];
      resumeStream: () => void;
      setMessages: (messages: ChatMessage[]) => void;
}

export function useAutoResume({
      autoResume,
      initialMessages,
      resumeStream,
      setMessages,
}: UseAutoResumeProps) {
      const hasResumed = useRef(false);

      useEffect(() => {
            if (autoResume && !hasResumed.current && initialMessages.length > 0) {
                  const lastMessage = initialMessages[initialMessages.length - 1];
                  if (lastMessage.role === "assistant") {
                        resumeStream();
                        hasResumed.current = true;
                  }
            }
      }, [autoResume, initialMessages, resumeStream, setMessages]);
}
