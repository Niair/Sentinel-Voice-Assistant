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

async function collectAssistantData(stream: ReadableStream<Uint8Array>) {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let text = '';
  let title = '';

  const consumeLine = (line: string) => {
    const trimmed = line.trim();
    if (trimmed.startsWith('0:')) {
      const payload = trimmed.slice(2).trim();
      if (!payload) return;
      try {
        const parsed = JSON.parse(payload);
        if (typeof parsed === 'string') {
          text += parsed;
        } else if (parsed?.content && typeof parsed.content === 'string') {
          text += parsed.content;
        }
      } catch {
        text += payload.replace(/^"|"$/g, '');
      }
    } else if (trimmed.startsWith('c:')) {
      const payload = trimmed.slice(2).trim();
      if (!payload) return;
      try {
        const parsed = JSON.parse(payload);
        if (typeof parsed === 'string') {
          title = parsed;
        }
      } catch {
        title = payload.replace(/^"|"$/g, '');
      }
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let newlineIndex = buffer.indexOf('\n');
    while (newlineIndex !== -1) {
      const line = buffer.slice(0, newlineIndex);
      buffer = buffer.slice(newlineIndex + 1);
      consumeLine(line);
      newlineIndex = buffer.indexOf('\n');
    }
  }

  if (buffer.trim()) {
    consumeLine(buffer);
  }

  return { text, title };
}

export async function POST(req: Request) {
  const { messages, id }: { messages: Array<Message>, id: string } = await req.json();
  const userId = '00000000-0000-0000-0000-000000000000'; // Our Guest User

  // 1. Ensure the Guest User exists and save the chat
  try {
    // This is a self-healing check to make sure our hardcoded guest user exists
    await ensureGuestUserExists(userId);

    const chatExists = await getChatById({ id });
    if (!chatExists && messages.length > 0) {
      const firstMessage = messages.find((message) => message.role === 'user') ?? messages[0];
      const firstText = getMessageText(firstMessage);
      const initialTitle = firstText.slice(0, 50) || 'New Chat';

      console.log('Saving new chat metadata for ID:', id);
      await saveChat({
        id,
        userId,
        title: initialTitle,
        visibility: 'private'
      });

      await saveMessageIfMissing(firstMessage, id);
      console.log('Chat and first message saved successfully');
    }

    const latestUserMessage = [...messages].reverse().find((message) => message.role === 'user');
    if (latestUserMessage) {
      await saveMessageIfMissing(latestUserMessage, id);
    }
  } catch (error) {
    console.error('DATABASE ERROR in /api/chat (persistence check):', error);
  }

  // 2. This calls your FastAPI backend running on port 8000
  const response = await fetch('http://127.0.0.1:8000/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages: messages.map(m => ({
        role: m.role,
        content: String(getTextFromMessage(m as any) || m.content || ''),
        id: m.id
      })),
      id: id,
      user_id: userId
    }),
  });

  if (!response.body) {
    console.error('AI Backend returned no body');
    return new Response('No response body from AI backend', { status: 500 });
  }

  console.log('Got successful response from AI backend, piping stream for ID:', id);

  // 3. Tee the stream: one copy for client, one for database storage
  const [clientStream, storageStream] = response.body.tee();
  
  // 4. Background async task to collect and save assistant response
  void (async () => {
    try {
      const { text, title } = await collectAssistantData(storageStream);
      
      if (title) {
        console.log('Updating chat title to:', title);
        await updateChatTitleById({ chatId: id, title });
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
      console.error('DATABASE ERROR in /api/chat (assistant/title save):', error);
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