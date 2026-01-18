"use client";

import { useState } from "react";

export function useChatVisibility({
  chatId,
  initialVisibilityType,
}: {
  chatId: string;
  initialVisibilityType: "public" | "private";
}) {
  const [visibilityType, setVisibilityType] = useState<"public" | "private">(
    initialVisibilityType
  );

  return {
    visibilityType,
    setVisibilityType,
  };
}