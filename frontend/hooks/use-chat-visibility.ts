import { create } from "zustand";

export type VisibilityType = "public" | "private";

interface ChatVisibilityStore {
  chatVisibility: VisibilityType;
  setChatVisibility: (visibility: VisibilityType) => void;
}

export const useChatVisibility = create<ChatVisibilityStore>((set) => ({
  chatVisibility: "private",
  setChatVisibility: (visibility) => set({ chatVisibility: visibility }),
}));