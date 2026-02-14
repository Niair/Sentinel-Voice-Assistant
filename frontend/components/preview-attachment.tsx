import Image from "next/image";
import type { Attachment } from "@/lib/types";
import { Loader } from "./elements/loader";
import { CrossSmallIcon } from "./icons";
import { Button } from "./ui/button";
import { FileText, FileImage, FileCode, File } from "lucide-react";

// Helper to get file icon based on content type
const getFileIcon = (contentType?: string) => {
  if (contentType?.startsWith("image")) {
    return <FileImage className="size-5 text-blue-600" />;
  }
  if (contentType?.includes("pdf")) {
    return <FileText className="size-5 text-red-500" />;
  }
  if (contentType?.includes("code") || contentType?.includes("text")) {
    return <FileCode className="size-5 text-green-600" />;
  }
  return <File className="size-5 text-blue-600" />;
};

// Helper to get file type label
const getFileTypeLabel = (contentType?: string, name?: string) => {
  if (contentType?.startsWith("image")) return "Image";
  if (contentType?.includes("pdf")) return "PDF";
  if (name?.toLowerCase().endsWith(".pdf")) return "PDF";
  if (contentType?.includes("word") || name?.toLowerCase().endsWith(".doc") || name?.toLowerCase().endsWith(".docx")) return "Document";
  if (contentType?.includes("code")) return "Code";
  if (contentType?.includes("text")) return "Text";
  return "File";
};

export const PreviewAttachment = ({
  attachment,
  isUploading = false,
  onRemove,
}: {
  attachment: Attachment;
  isUploading?: boolean;
  onRemove?: () => void;
}) => {
  const { name, url, contentType } = attachment;

  return (
    <div
      className="group relative flex items-center gap-3 p-3 pr-8 rounded-xl border bg-white dark:bg-card hover:bg-gray-50 dark:hover:bg-accent/50 transition-colors shadow-sm min-w-[220px] max-w-[280px]"
      data-testid="input-attachment-preview"
    >
      {/* File Icon */}
      <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center">
        {getFileIcon(contentType)}
      </div>

      {/* File Info */}
      <div className="flex-1 min-w-0">
        <div className="font-medium text-sm text-foreground truncate">
          {name}
        </div>
        <div className="text-xs text-muted-foreground">
          {getFileTypeLabel(contentType, name)}
        </div>
      </div>

      {/* Uploading Overlay */}
      {isUploading && (
        <div
          className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-xl"
          data-testid="input-attachment-loader"
        >
          <Loader size={20} />
        </div>
      )}

      {/* Remove Button */}
      {onRemove && !isUploading && (
        <Button
          className="absolute top-1.5 right-1.5 size-6 rounded-full p-0 opacity-0 transition-opacity group-hover:opacity-100 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700"
          onClick={onRemove}
          size="sm"
          variant="ghost"
        >
          <CrossSmallIcon size={12} />
        </Button>
      )}
    </div>
  );
};
