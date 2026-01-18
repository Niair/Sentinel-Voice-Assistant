import { create } from "zustand";

export type BlockKind = "text" | "code" | "sheet";
export type BlockStatus = "idle" | "streaming";

interface BlockState {
  kind: BlockKind;
  status: BlockStatus;
  content: string;
}

interface BlockStore {
  block: BlockState;
  setBlock: (block: BlockState | ((prev: BlockState) => BlockState)) => void;
}

export const useBlock = create<BlockStore>((set) => ({
  block: {
    kind: "text",
    status: "idle",
    content: "",
  },
  setBlock: (block) =>
    set((state) => ({
      block: typeof block === "function" ? block(state.block) : block,
    })),
}));