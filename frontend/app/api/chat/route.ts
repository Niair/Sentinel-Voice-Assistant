import { getChatById, getMessageById, saveChat, saveMessages, ensureGuestUserExists, updateChatTitleById } from '@/lib/db/queries';
import { generateUUID, getTextFromMessage } from '@/lib/utils';
import { Message } from 'ai';

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
      let newlineIndex = buffer.indexOf('\n');

      while (newlineIndex !== -1) {
        const line = buffer.slice(0, newlineIndex);
        buffer = buffer.slice(newlineIndex + 1);

        // Parse Vercel AI SDK streaming format
        if (line.startsWith('0:')) {
          const payload = line.slice(2).trim();
          try {
            const parsed = JSON.parse(payload);
            // Handle both string and object formats
            if (typeof parsed === 'string') {
              text += parsed;
            } else if (parsed?.content) {
              text += parsed.content;
            }
          } catch {
            // Fallback for unescaped strings
            text += payload.replace(/^"|"$/g, '');
          }
        }

        newlineIndex = buffer.indexOf('\n');
      }
    }

    // Handle any remaining buffer
    if (buffer.trim()) {
      if (buffer.startsWith('0:')) {
        const payload = buffer.slice(2).trim();
        text += payload.replace(/^"|"$/g, '');
      }
    }
  } catch (error) {
    console.error('Stream reading error:', error);
    text = "I encountered an error while reading the response. Please try again.";
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
  const [clientStream, storageStream] = response.body.tee();

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

  return new Response(clientStream, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'Cache-Control': 'no-cache, no-transform',
      'Connection': 'keep-alive',
      'X-Content-Type-Options': 'nosniff',
      'X-Vercel-AI-Data-Stream': 'v1',
    },
  });
}