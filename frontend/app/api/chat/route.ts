import { getChatById, saveChat, saveMessages } from '@/lib/db/queries';
import { generateUUID, getTextFromMessage } from '@/lib/utils';
import { Message } from 'ai';

export async function POST(req: Request) {
  const { messages, id }: { messages: Array<Message>, id: string } = await req.json();
  const userId = '00000000-0000-0000-0000-000000000000'; // Our Guest User

  // 1. If this is a new chat, save it to the DB so it doesn't 404 on reload
  // 1. If this is a new chat, save it to the DB so it doesn't 404 on reload
  try {
    const chatExists = await getChatById({ id });
    if (!chatExists && messages.length > 0) {
      const firstMessage = messages[0];
      const title = getTextFromMessage(firstMessage as any) || firstMessage.content.slice(0, 50) || 'New Chat';

      console.log('Saving new chat metadata for ID:', id);
      await saveChat({
        id,
        userId,
        title,
        visibility: 'private'
      });

      // Also save the user's initial message
      await saveMessages({
        messages: [{
          id: firstMessage.id || generateUUID(),
          chatId: id,
          role: 'user',
          parts: (firstMessage as any).parts || [{ type: 'text', text: firstMessage.content }],
          attachments: (firstMessage as any).attachments || [],
          createdAt: new Date(),
        }]
      });
      console.log('Chat and first message saved successfully');
    }
  } catch (error) {
    console.error('DATABASE ERROR in /api/chat:', error);
  }

  // This calls your FastAPI backend running on port 8000
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
      user_id: '00000000-0000-0000-0000-000000000000'
    }),
  });

  if (!response.body) {
    console.error('AI Backend returned no body');
    return new Response('No response body from AI backend', { status: 500 });
  }

  console.log('AI Backend connection successful, starting to pipe stream for ID:', id);

  const reader = response.body.getReader();
  const encoder = new TextEncoder();
  const decoder = new TextDecoder();

  const stream = new ReadableStream({
    async start(controller) {
      console.log('Stream controller started');
      let chunkCount = 0;
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            console.log('AI Backend stream finished. Total chunks:', chunkCount);
            break;
          }
          chunkCount++;
          const text = decoder.decode(value);
          // Optional: log first few chunks
          if (chunkCount <= 5) {
            console.log(`Chunk ${chunkCount}:`, text.slice(0, 50));
          }
          controller.enqueue(value);
        }
      } catch (error) {
        console.error('Error reading from AI backend stream:', error);
        controller.error(error);
      } finally {
        controller.close();
        console.log('Stream controller closed');
      }
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'Cache-Control': 'no-cache, no-transform',
      'Connection': 'keep-alive',
      'X-Content-Type-Options': 'nosniff',
      'X-Vercel-AI-Data-Stream': 'v1',
    },
  });
}
