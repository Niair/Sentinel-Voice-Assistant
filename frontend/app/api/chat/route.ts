import { streamText } from 'ai';
// Note: In a real Vercel AI SDK setup, you might use 'fetch' directly 
// if your backend already handles the protocol, or use the SDK's 
// custom provider capabilities.

export async function POST(req: Request) {
  const { messages, id } = await req.json();

  // This calls your FastAPI backend running on port 8000
  const response = await fetch('http://localhost:8000/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      messages,
      thread_id: id // Use the Vercel chat ID as the LangGraph thread_id
    }),
  });

  if (!response.ok) {
    return new Response('Failed to connect to AI backend', { status: 500 });
  }

  // The FastAPI backend is already sending data in the Vercel AI SDK 
  // wire protocol format (0:..., 9:..., etc.), so we just pipe it.
  return new Response(response.body);
}
