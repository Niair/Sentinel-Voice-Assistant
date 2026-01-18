import { create } from "zustand";
import type { UIArtifact } from "@/components/artifact";

export const initialArtifactData: UIArtifact = {
      title: "",
      documentId: "init",
      kind: "text",
      content: "",
      isVisible: false,
      status: "idle",
      boundingBox: {
            top: 0,
            left: 0,
            width: 0,
            height: 0,
      },
};

type ArtifactMetadata = Record<string, unknown>;

interface ArtifactStore {
      artifact: UIArtifact;
      metadata: ArtifactMetadata;
      setArtifact: (
            artifact: UIArtifact | ((prev: UIArtifact) => UIArtifact)
      ) => void;
      setMetadata: (
            metadata: ArtifactMetadata | ((prev: ArtifactMetadata) => ArtifactMetadata)
      ) => void;
}

const useArtifactStore = create<ArtifactStore>((set) => ({
      artifact: initialArtifactData,
      metadata: {},
      setArtifact: (artifact) =>
            set((state) => ({
                  artifact: typeof artifact === "function" ? artifact(state.artifact) : artifact,
            })),
      setMetadata: (metadata) =>
            set((state) => ({
                  metadata: typeof metadata === "function" ? metadata(state.metadata) : metadata,
            })),
}));

export function useArtifact() {
      const { artifact, metadata, setArtifact, setMetadata } = useArtifactStore();
      return { artifact, metadata, setArtifact, setMetadata };
}

export function useArtifactSelector<T>(
      selector: (state: UIArtifact) => T
): T {
      return useArtifactStore((state) => selector(state.artifact));
}
