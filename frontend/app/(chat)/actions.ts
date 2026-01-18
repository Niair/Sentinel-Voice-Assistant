"use server";

import {
      deleteMessagesByChatIdAfterTimestamp,
      getMessageById,
} from "@/lib/db/queries";

export async function deleteTrailingMessages({ id }: { id: string }) {
      const [message] = await getMessageById({ id });

      if (message) {
            await deleteMessagesByChatIdAfterTimestamp({
                  chatId: message.chatId,
                  timestamp: message.createdAt,
            });
      }
}
