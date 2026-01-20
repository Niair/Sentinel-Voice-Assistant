import { updateChatTitleById } from '@/lib/db/queries';

export async function POST(req: Request) {
  try {
    const { id, title } = await req.json();

    if (!id || !title) {
      return new Response('Missing id or title', { status: 400 });
    }

    await updateChatTitleById({ chatId: id, title });

    return new Response('Chat title updated successfully', { status: 200 });
  } catch (error) {
    console.error('Error updating chat title:', error);
    return new Response('Internal Server Error', { status: 500 });
  }
}
