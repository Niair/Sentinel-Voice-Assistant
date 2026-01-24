import { appendFileSync } from 'fs';
import { getChatById, getMessageById, saveChat, saveMessages, ensureGuestUserExists, updateChatTitleById } from '@/lib/db/queries';
import { generateUUID, getTextFromMessage } from '@/lib/utils';
import { Message } from 'ai';

const DEBUG_LOG_PATH = 'e:\\_Projects\\Sentinal-Voice-Assistant\\.cursor\\debug.log';
function debugLog(obj: Record<string, unknown>) {
  try {
    appendFileSync(DEBUG_LOG_PATH, JSON.stringify({ ...obj, timestamp: Date.now(), sessionId: 'debug-session' }) + '\n');
  } catch {}
}

function getMessageText(message: Message) {
  return String(getTextFromMessage(message as any) || message.content || '');
}

async function saveMessageIfMissing(message: Message, chatId: string) {
  const messageId = message.id || generateUUID();
  if (message.id) {
    const existing = await getMessageById({ id: message.id });
    if (existing.length > 0) {
      return;
    }
  }

  const text = getMessageText(message);
  await saveMessages({
    messages: [{
      id: messageId,
      chatId,
      role: message.role,
      parts: (message as any).parts || [{ type: 'text', text }],
      attachments: (message as any).attachments || [],
      createdAt: new Date(),
    }]
  });
}

/**
 * Transform backend stream from Vercel AI SDK v1 (0:"chunk"\n) to SSE (data: {...}\n\n).
 * parseJsonEventStream uses EventSourceParserStream, which only parses SSE, not raw NDJSON.
 */
function transformVercelDataStreamToAi6(stream: ReadableStream<Uint8Array>): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  const format = (obj: object) => `data: ${JSON.stringify(obj)}\n\n`;
  let buffer = '';
  let textId: string | null = null;
  let emittedStart = false;
  let emittedStartStep = false;
  let textDeltaCount = 0;

  return stream.pipeThrough(new TransformStream<Uint8Array, Uint8Array>({
    transform(chunk, controller) {
      buffer += new TextDecoder().decode(chunk, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';
      for (const line of lines) {
        if (line.length === 0) continue;
        const m = line.match(/^0:(.*)$/);
        if (m) {
          try {
            const value = JSON.parse(m[1]);
            const delta = typeof value === 'string' ? value : String((value as { content?: string })?.content ?? '');
            if (!textId) textId = generateUUID();
            if (!emittedStartStep) {
              controller.enqueue(encoder.encode(format({ type: 'start-step' })));
              emittedStartStep = true;
              debugLog({ location: 'route:transform', message: 'start-step', hypothesisId: 'H6' });
            }
            if (!emittedStart) {
              controller.enqueue(encoder.encode(format({ type: 'text-start', id: textId })));
              emittedStart = true;
              debugLog({ location: 'route:transform', message: 'text-start', data: { id: textId }, hypothesisId: 'H6' });
            }
            if (delta.length > 0) {
              controller.enqueue(encoder.encode(format({ type: 'text-delta', id: textId, delta })));
              textDeltaCount++;
              if (textDeltaCount === 1) {
                debugLog({ location: 'route:transform', message: 'text-delta', data: { deltaLen: delta.length }, hypothesisId: 'H6' });
              }
            }
          } catch {
            // ignore malformed 0: lines
          }
        }
      }
    },
    flush(controller) {
      if (textId != null && emittedStart) {
        controller.enqueue(encoder.encode(format({ type: 'text-end', id: textId })));
        debugLog({ location: 'route:transform', message: 'text-end', data: { textDeltaCount }, hypothesisId: 'H6' });
      }
      if (emittedStartStep) {
        controller.enqueue(encoder.encode(format({ type: 'finish-step' })));
        controller.enqueue(encoder.encode(format({ type: 'finish', finishReason: 'stop' })));
        debugLog({ location: 'route:transform', message: 'finish-step+finish', hypothesisId: 'H6' });
      }
    },
  }));
}

// FIXED: Simplified stream parser that correctly handles Vercel AI SDK format
async function collectAssistantData(stream: ReadableStream<Uint8Array>) {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let text = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      let lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('0:')) {
          try {
            const payload = JSON.parse(line.slice(2));
            text += typeof payload === 'string' ? payload : (payload?.content || '');
          } catch {
            text += line.slice(2).replace(/^"|"$/g, '');
          }
        }
      }
    }
  } catch (error) {
    console.error('Stream reading error:', error);
  }
  return { text };
}

export async function POST(req: Request) {
  const { messages, id, selectedChatModel }: { messages: Array<Message>, id: string, selectedChatModel?: string } = await req.json();
  const userId = '00000000-0000-0000-0000-000000000000';

  // Extract first USER message for title
  const firstUserMessage = messages.find(m => m.role === 'user');
  const titleFromUser = firstUserMessage ? getMessageText(firstUserMessage).slice(0, 50) : 'New Chat';

  // FIXED: Declare chatExists at function scope so it's accessible in the async callback
  let chatExists = false;

  try {
    await ensureGuestUserExists(userId);

    // Check if chat exists
    const existingChat = await getChatById({ id });
    chatExists = !!existingChat;

    if (!chatExists && messages.length > 0) {
      console.log('Saving new chat metadata for ID:', id);
      await saveChat({
        id,
        userId,
        title: titleFromUser,
        visibility: 'private'
      });

      await saveMessageIfMissing(firstUserMessage || messages[0], id);
      console.log('Chat and first message saved successfully');
    } else {
      const latestUserMessage = [...messages].reverse().find((message) => message.role === 'user');
      if (latestUserMessage) {
        await saveMessageIfMissing(latestUserMessage, id);
      }
    }
  } catch (error) {
    console.error('DATABASE ERROR in /api/chat (persistence check):', error);
  }

  // Send attachments to backend
  const messagesWithAttachments = messages.map(m => {
    const baseMessage = {
      role: m.role,
      content: String(getTextFromMessage(m as any) || m.content || ''),
      id: m.id
    };

    if ((m as any).parts) {
      const fileParts = (m as any).parts.filter((p: any) => p.type === 'file');
      if (fileParts.length > 0) {
        (baseMessage as any).attachments = fileParts;
      }
    }

    return baseMessage;
  });

  const response = await fetch('http://127.0.0.1:8000/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages: messagesWithAttachments,
      id: id,
      user_id: userId,
      model: selectedChatModel
    }),
  });

  if (!response.ok || !response.body) {
    const errorText = await response.text().catch(() => 'No error body');
    console.error('AI Backend error status:', response.status, errorText);
    return new Response(`AI backend error: ${response.status}`, { status: 500 });
  }

  console.log('Got successful response from AI backend, piping stream for ID:', id);

  // Split stream for client response and background processing
  const [finalStream, storageStream] = response.body.tee();

  // Process assistant response in background
  void (async () => {
    try {
      const { text } = await collectAssistantData(storageStream);

      // Only update title if it's a new chat (chatExists is now properly scoped)
      if (!chatExists && titleFromUser) {
        console.log('Updating chat title to:', titleFromUser);
        await updateChatTitleById({ chatId: id, title: titleFromUser });
      }

      if (text.trim()) {
        await saveMessages({
          messages: [{
            id: generateUUID(),
            chatId: id,
            role: 'assistant',
            parts: [{ type: 'text', text }],
            attachments: [],
            createdAt: new Date(),
          }]
        });
      }
    } catch (error) {
      console.error('DATABASE ERROR in /api/chat (assistant save):', error);
    }
  })();

  const clientStream = transformVercelDataStreamToAi6(finalStream);

  return new Response(clientStream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      'X-Vercel-AI-Data-Stream': 'v1',
    },
  });
}