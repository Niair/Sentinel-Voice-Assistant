"use client";

import type { ComponentProps } from "react";
import { Streamdown } from "streamdown";
import { cn } from "@/lib/utils";

type ResponseProps = ComponentProps<typeof Streamdown>;

export function Response({ className, children, ...props }: ResponseProps) {
  return (
    <Streamdown
      className={cn(
        "size-full",
        // Typography
        "[&>*:first-child]:mt-0 [&>*:last-child]:mb-0",
        "[&_p]:mb-4 [&_p]:leading-7",
        // Headings
        "[&_h1]:text-2xl [&_h1]:font-semibold [&_h1]:mb-4 [&_h1]:mt-6",
        "[&_h2]:text-xl [&_h2]:font-semibold [&_h2]:mb-3 [&_h2]:mt-5",
        "[&_h3]:text-lg [&_h3]:font-semibold [&_h3]:mb-2 [&_h3]:mt-4",
        // Lists
        "[&_ul]:mb-4 [&_ul]:list-disc [&_ul]:pl-6",
        "[&_ol]:mb-4 [&_ol]:list-decimal [&_ol]:pl-6",
        "[&_li]:mb-1 [&_li]:leading-7",
        // Inline code
        "[&_code]:whitespace-pre-wrap [&_code]:break-words",
        "[&_code:not(pre_code)]:bg-black/5 [&_code:not(pre_code)]:dark:bg-white/10",
        "[&_code:not(pre_code)]:px-1.5 [&_code:not(pre_code)]:py-0.5",
        "[&_code:not(pre_code)]:rounded-md [&_code:not(pre_code)]:text-sm",
        "[&_code:not(pre_code)]:font-mono",
        // Code blocks
        "[&_pre]:max-w-full [&_pre]:overflow-x-auto",
        "[&_pre]:bg-[#1e1e1e] [&_pre]:dark:bg-[#0d0d0d]",
        "[&_pre]:rounded-xl [&_pre]:p-4 [&_pre]:my-4",
        "[&_pre]:text-white [&_pre]:text-sm",
        // Tables
        "[&_table]:w-full [&_table]:mb-4 [&_table]:border-collapse",
        "[&_th]:border [&_th]:border-border [&_th]:p-2 [&_th]:text-left [&_th]:font-semibold [&_th]:bg-muted",
        "[&_td]:border [&_td]:border-border [&_td]:p-2",
        "[&_tr:nth-child(even)]:bg-muted/50",
        // Blockquotes
        "[&_blockquote]:border-l-2 [&_blockquote]:border-border",
        "[&_blockquote]:pl-4 [&_blockquote]:italic [&_blockquote]:text-muted-foreground",
        // Links
        "[&_a]:text-primary [&_a]:underline [&_a]:underline-offset-4",
        "[&_a]:hover:text-primary/80",
        // Horizontal rule
        "[&_hr]:my-6 [&_hr]:border-border",
        className
      )}
      {...props}
    >
      {children}
    </Streamdown>
  );
}
