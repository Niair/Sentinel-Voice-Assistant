import { getVotesByChatId, voteMessage } from '@/lib/db/queries';

export async function GET(request: Request) {
      const { searchParams } = new URL(request.url);
      const chatId = searchParams.get('chatId');

      if (!chatId) {
            return Response.json({ error: 'chatId required' }, { status: 400 });
      }

      try {
            const votes = await getVotesByChatId({ id: chatId });
            return Response.json(votes);
      } catch {
            return Response.json({ error: 'Failed to get votes' }, { status: 500 });
      }
}

export async function PATCH(request: Request) {
      const body = await request.json();
      const { chatId, messageId, type } = body;

      if (!chatId || !messageId || !type) {
            return Response.json(
                  { error: 'chatId, messageId, and type are required' },
                  { status: 400 }
            );
      }

      if (type !== 'up' && type !== 'down') {
            return Response.json(
                  { error: "type must be 'up' or 'down'" },
                  { status: 400 }
            );
      }

      try {
            await voteMessage({ chatId, messageId, type });
            return Response.json({ success: true });
      } catch {
            return Response.json({ error: 'Failed to vote on message' }, { status: 500 });
      }
}