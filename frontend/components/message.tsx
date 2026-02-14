"use client";
import type { UseChatHelpers } from "@ai-sdk/react";
import { useState, useRef } from "react";
import type { Vote } from "@/lib/db/schema";
import type { ChatMessage } from "@/lib/types";
import { cn, sanitizeText } from "@/lib/utils";
import { useDataStream } from "./data-stream-provider";
import { DocumentToolResult } from "./document";
import { DocumentPreview } from "./document-preview";
import { MessageContent } from "./elements/message";
import { Response } from "./elements/response";
import {
  Tool,
  ToolContent,
  ToolHeader,
  ToolInput,
  ToolOutput,
} from "./elements/tool";
import { SparklesIcon, CopyIcon } from "./icons";
import { Check } from "lucide-react";
import { MessageActions } from "./message-actions";
import { MessageEditor } from "./message-editor";
import { MessageReasoning } from "./message-reasoning";
import { PreviewAttachment } from "./preview-attachment";
import { Weather } from "./weather";

// Copy button component for ChatGPT-style UI
const CopyButton = ({ text }: { text: string }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  return (
    <button
      onClick={handleCopy}
      className="p-1.5 rounded-md hover:bg-black/5 dark:hover:bg-white/10 transition-colors text-muted-foreground hover:text-foreground"
      title="Copy message"
    >
      {copied ? (
        <Check size={16} className="text-green-500" />
      ) : (
        <CopyIcon size={16} />
      )}
    </button>
  );
};

const PurePreviewMessage = ({
  addToolApprovalResponse,
  chatId,
  message,
  vote,
  isLoading,
  setMessages,
  regenerate,
  isReadonly,
  requiresScrollPadding: _requiresScrollPadding,
  isFirstMessage = false,
}: {
  addToolApprovalResponse: UseChatHelpers<ChatMessage>["addToolApprovalResponse"];
  chatId: string;
  message: ChatMessage;
  vote: Vote | undefined;
  isLoading: boolean;
  setMessages: UseChatHelpers<ChatMessage>["setMessages"];
  regenerate: UseChatHelpers<ChatMessage>["regenerate"];
  isReadonly: boolean;
  requiresScrollPadding: boolean;
  isFirstMessage?: boolean;
}) => {
  const [mode, setMode] = useState<"view" | "edit">("view");

  const attachmentsFromMessage = message.parts.filter(
    (part) => part.type === "file"
  );

  useDataStream();

  if (process.env.NODE_ENV === 'development') {
    console.log('Rendering Message:', message.id, 'Role:', message.role, 'Parts:', message.parts?.length);
  }

  // Extract all text content for copy functionality
  const getMessageText = () => {
    let text = "";
    if (message.content) {
      text += message.content;
    }
    message.parts?.forEach((part) => {
      if (part.type === "text" && (part as any).text) {
        text += (part as any).text;
      }
    });
    return text;
  };

  return (
    <div
      className={cn(
        "group/message w-full py-5",
        message.role === "user" ? "bg-white dark:bg-background" : "bg-white dark:bg-background"
      )}
      data-role={message.role}
      data-testid={`message-${message.role}`}
    >
      <div className="max-w-[48rem] mx-auto px-4 md:px-6">
        <div
          className={cn("flex items-start gap-4", {
            "flex-row-reverse": message.role === "user" && mode !== "edit",
          })}
        >
          {/* Avatar */}
          {message.role === "assistant" && (
            <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-sm font-semibold">
              S
            </div>
          )}

          {/* Message Content */}
          <div
            className={cn("flex flex-col min-w-0", {
              "items-end": message.role === "user" && mode !== "edit",
              "items-start": message.role === "assistant",
              "flex-1": mode === "edit",
            })}
          >
            {/* Assistant Header */}
            {message.role === "assistant" && isFirstMessage && (
              <div className="text-sm font-semibold text-foreground mb-1.5">
                Sentinel: Your Personal AI Assistant and Protector
              </div>
            )}

            {/* File Attachments - Only show for user messages */}
            {attachmentsFromMessage.length > 0 && message.role === "user" && (
              <div
                className="flex flex-wrap gap-2 mb-3"
                data-testid={"message-attachments"}
              >
                {attachmentsFromMessage.map((attachment) => (
                  <PreviewAttachment
                    attachment={{
                      name: attachment.filename ?? "file",
                      contentType: attachment.mediaType,
                      url: attachment.url,
                    }}
                    key={attachment.url}
                  />
                ))}
              </div>
            )}

            {/* Message Parts */}
            <div className={cn("flex flex-col gap-3", message.role === "assistant" && "w-full")}>
              {message.parts?.map((part, index) => {
                const { type } = part;
                const key = `message-${message.id}-part-${index}`;

                if (process.env.NODE_ENV === 'development') {
                  console.log(`Part ${index} for ${message.id}:`, { type, keys: Object.keys(part), text: (part as any).text?.slice(0, 20) });
                }

                // Skip file parts - they're rendered above
                if (type === "file") {
                  return null;
                }

                // Structural markers from ai 6 stream (start-step → step-start part); no user-visible content
                if (type === "step-start" || type === "step-end") {
                  return null;
                }

                // Handle generic tool-call parts (search_tool, rag_tool, MCP tools)
                if (type === "tool-call") {
                  const { toolCallId, toolName, args } = part as { toolCallId: string; toolName: string; args: unknown };
                  return (
                    <div className="w-full" key={toolCallId || key}>
                      <Tool className="w-full" defaultOpen={true}>
                        <ToolHeader state="input-available" type={`tool-${toolName}`} />
                        <ToolContent>
                          <div className="px-4 py-3">
                            <div className="text-sm font-medium text-muted-foreground mb-2">
                              Using {toolName}...
                            </div>
                            {args && (
                              <ToolInput input={args as Record<string, unknown>} />
                            )}
                          </div>
                        </ToolContent>
                      </Tool>
                    </div>
                  );
                }

                // Handle tool-result parts
                if (type === "tool-result") {
                  const { toolCallId, result } = part as { toolCallId: string; result: unknown };
                  const resultStr = typeof result === 'string' ? result : JSON.stringify(result, null, 2);
                  return (
                    <div className="w-full" key={`result-${toolCallId || key}`}>
                      <Tool className="w-full" defaultOpen={false}>
                        <ToolHeader state="output-available" type="tool-result" />
                        <ToolContent>
                          <div className="px-4 py-3 text-sm">
                            <pre className="whitespace-pre-wrap text-xs bg-muted p-2 rounded max-h-40 overflow-auto">
                              {resultStr.slice(0, 500)}{resultStr.length > 500 ? '...' : ''}
                            </pre>
                          </div>
                        </ToolContent>
                      </Tool>
                    </div>
                  );
                }

                if (type === "reasoning") {
                  const hasContent = part.text?.trim().length > 0;
                  const isStreaming = "state" in part && part.state === "streaming";
                  if (hasContent || isStreaming) {
                    return (
                      <MessageReasoning
                        isLoading={isLoading || isStreaming}
                        key={key}
                        reasoning={part.text || ""}
                      />
                    );
                  }
                }

                if (type === "text") {
                  const text = typeof (part as any).text === "string" ? (part as any).text : "";
                  if (mode === "view") {
                    if (message.role === "user") {
                      // ChatGPT-style user message bubble - stays right-aligned
                      return (
                        <div key={key} className="max-w-[80%] w-fit ml-auto">
                          <div className="bg-[#f7f7f8] dark:bg-[#2f2f2f] text-foreground px-5 py-2.5 rounded-3xl text-[15px] leading-relaxed">
                            <div className="whitespace-pre-wrap">{sanitizeText(text)}</div>
                          </div>
                        </div>
                      );
                    } else {
                      // ChatGPT-style assistant message (full width, clean)
                      return (
                        <div key={key} className="w-full">
                          <div className="text-[15px] leading-7 text-foreground">
                            <Response>{text}</Response>
                          </div>
                        </div>
                      );
                    }
                  }

                  if (mode === "edit") {
                    return (
                      <div
                        className="flex w-full flex-row items-start gap-3"
                        key={key}
                      >
                        <div className="min-w-0 flex-1">
                          <MessageEditor
                            key={message.id}
                            message={message}
                            regenerate={regenerate}
                            setMessages={setMessages}
                            setMode={setMode}
                          />
                        </div>
                      </div>
                    );
                  }
                }

                if (type === "tool-getWeather") {
                  const { toolCallId, state } = part;
                  const approvalId = (part as { approval?: { id: string } })
                    .approval?.id;
                  const isDenied =
                    state === "output-denied" ||
                    (state === "approval-responded" &&
                      (part as { approval?: { approved?: boolean } }).approval
                        ?.approved === false);
                  const widthClass = "w-[min(100%,450px)]";

                  if (state === "output-available") {
                    return (
                      <div className={widthClass} key={toolCallId}>
                        <Weather weatherAtLocation={part.output} />
                      </div>
                    );
                  }

                  if (isDenied) {
                    return (
                      <div className={widthClass} key={toolCallId}>
                        <Tool className="w-full" defaultOpen={true}>
                          <ToolHeader
                            state="output-denied"
                            type="tool-getWeather"
                          />
                          <ToolContent>
                            <div className="px-4 py-3 text-muted-foreground text-sm">
                              Weather lookup was denied.
                            </div>
                          </ToolContent>
                        </Tool>
                      </div>
                    );
                  }

                  if (state === "approval-responded") {
                    return (
                      <div className={widthClass} key={toolCallId}>
                        <Tool className="w-full" defaultOpen={true}>
                          <ToolHeader state={state} type="tool-getWeather" />
                          <ToolContent>
                            <ToolInput input={part.input} />
                          </ToolContent>
                        </Tool>
                      </div>
                    );
                  }

                  return (
                    <div className={widthClass} key={toolCallId}>
                      <Tool className="w-full" defaultOpen={true}>
                        <ToolHeader state={state} type="tool-getWeather" />
                        <ToolContent>
                          {(state === "input-available" ||
                            state === "approval-requested") && (
                              <ToolInput input={part.input} />
                            )}
                          {state === "approval-requested" && approvalId && (
                            <div className="flex items-center justify-end gap-2 border-t px-4 py-3">
                              <button
                                className="rounded-md px-3 py-1.5 text-muted-foreground text-sm transition-colors hover:bg-muted hover:text-foreground"
                                onClick={() => {
                                  addToolApprovalResponse({
                                    id: approvalId,
                                    approved: false,
                                    reason: "User denied weather lookup",
                                  });
                                }}
                                type="button"
                              >
                                Deny
                              </button>
                              <button
                                className="rounded-md bg-primary px-3 py-1.5 text-primary-foreground text-sm transition-colors hover:bg-primary/90"
                                onClick={() => {
                                  addToolApprovalResponse({
                                    id: approvalId,
                                    approved: true,
                                  });
                                }}
                                type="button"
                              >
                                Allow
                              </button>
                            </div>
                          )}
                        </ToolContent>
                      </Tool>
                    </div>
                  );
                }

                if (type === "tool-createDocument") {
                  const { toolCallId } = part;

                  if (part.output && "error" in part.output) {
                    return (
                      <div
                        className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-500 dark:bg-red-950/50"
                        key={toolCallId}
                      >
                        Error creating document: {String(part.output.error)}
                      </div>
                    );
                  }

                  return (
                    <DocumentPreview
                      isReadonly={isReadonly}
                      key={toolCallId}
                      result={part.output}
                    />
                  );
                }

                if (type === "tool-updateDocument") {
                  const { toolCallId } = part;

                  if (part.output && "error" in part.output) {
                    return (
                      <div
                        className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-500 dark:bg-red-950/50"
                        key={toolCallId}
                      >
                        Error updating document: {String(part.output.error)}
                      </div>
                    );
                  }

                  return (
                    <div className="relative" key={toolCallId}>
                      <DocumentPreview
                        args={{ ...part.output, isUpdate: true }}
                        isReadonly={isReadonly}
                        result={part.output}
                      />
                    </div>
                  );
                }

                if (type === "tool-requestSuggestions") {
                  const { toolCallId, state } = part;

                  return (
                    <Tool defaultOpen={true} key={toolCallId}>
                      <ToolHeader state={state} type="tool-requestSuggestions" />
                      <ToolContent>
                        {state === "input-available" && (
                          <ToolInput input={part.input} />
                        )}
                        {state === "output-available" && (
                          <ToolOutput
                            errorText={undefined}
                            output={
                              "error" in part.output ? (
                                <div className="rounded border p-2 text-red-500">
                                  Error: {String(part.output.error)}
                                </div>
                              ) : (
                                <DocumentToolResult
                                  isReadonly={isReadonly}
                                  result={part.output}
                                  type="request-suggestions"
                                />
                              )
                            }
                          />
                        )}
                      </ToolContent>
                    </Tool>
                  );
                }

                if (process.env.NODE_ENV === 'development') {
                  return (
                    <div className="rounded border border-dashed border-red-500/30 p-2 text-[10px] text-muted-foreground" key={key}>
                      Unknown part type: {type}. Full keys: {Object.keys(part).join(', ')}
                      <pre>{JSON.stringify(part, null, 2)}</pre>
                    </div>
                  );
                }

                return null;
              })}

              {/* Fallback for messages without parts */}
              {((!message.parts || message.parts.length === 0) || (message.role === 'assistant' && message.parts.every(p => p.type === 'text' && !(p as any).text?.trim()))) && message.content && (
                <div key="content-fallback">
                  {message.role === "user" ? (
                    <div className="max-w-[80%] w-fit ml-auto">
                      <div className="bg-[#f7f7f8] dark:bg-[#2f2f2f] text-foreground px-5 py-2.5 rounded-3xl text-[15px] leading-relaxed">
                        <div className="whitespace-pre-wrap">{sanitizeText(message.content)}</div>
                      </div>
                    </div>
                  ) : (
                    <div className="w-full">
                      <div className="text-[15px] leading-7 text-foreground">
                        <Response>{message.content}</Response>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Assistant error messages */}
              {message.role === 'assistant' && !message.parts && message.content && (
                <div key="error-message" className="w-full">
                  <div className="text-[15px] leading-7 text-red-600">
                    {sanitizeText(message.content)}
                  </div>
                </div>
              )}

              {/* Copy button for assistant messages */}
              {message.role === "assistant" && !isLoading && (
                <div className="flex items-center gap-1 mt-2 opacity-0 group-hover/message:opacity-100 transition-opacity">
                  <CopyButton text={getMessageText()} />
                </div>
              )}
            </div>

            {/* Message Actions */}
            {!isReadonly && message.role === "user" && (
              <MessageActions
                chatId={chatId}
                isLoading={isLoading}
                key={`action-${message.id}`}
                message={message}
                setMode={setMode}
                vote={vote}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export const PreviewMessage = PurePreviewMessage;

export const ThinkingMessage = () => {
  return (
    <div
      className="group/message w-full py-6 bg-white dark:bg-background"
      data-role="assistant"
      data-testid="message-assistant-loading"
    >
      <div className="max-w-3xl mx-auto px-4 md:px-6">
        <div className="flex items-start gap-4">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-sm font-semibold">
            S
          </div>
          <div className="flex items-center gap-2 pt-2 text-muted-foreground text-sm">
            <span className="animate-pulse">Sentinel is processing</span>
            <span className="flex gap-0.5">
              <span className="animate-bounce [animation-delay:0ms]">.</span>
              <span className="animate-bounce [animation-delay:150ms]">.</span>
              <span className="animate-bounce [animation-delay:300ms]">.</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
