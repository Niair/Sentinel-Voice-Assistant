import { cookies } from 'next/headers';
import { getChatsByUserId } from '@/lib/db/queries';

export async function GET(request: Request) {
      const { searchParams } = new URL(request.url);
      const limit = parseInt(searchParams.get('limit') || '20');
      const startingAfter = searchParams.get('startingAfter');

      // Use the guest user ID for now
      const userId = '00000000-0000-0000-0000-000000000000';

      try {
            const history = await getChatsByUserId({
                  id: userId,
                  limit,
                  startingAfter,
                  endingBefore: null
            });

            return Response.json(history);
      } catch (error) {
            return new Response('Failed to fetch history', { status: 500 });
      }
}
