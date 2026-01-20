import { getChatsByUserId } from '@/lib/db/queries';

export async function GET(request: Request) {
      const { searchParams } = new URL(request.url);
      const limit = parseInt(searchParams.get('limit') || '20');
      const startingAfter = searchParams.get('startingAfter');
      const endingBefore = searchParams.get('ending_before') ?? searchParams.get('endingBefore');

      // Use the guest user ID for now
      const userId = '00000000-0000-0000-0000-000000000000';

      try {
            const history = await getChatsByUserId({
                  id: userId,
                  limit,
                  startingAfter,
                  endingBefore
            });

            return Response.json(history);
      } catch (error) {
            return new Response('Failed to fetch history', { status: 500 });
      }
}
