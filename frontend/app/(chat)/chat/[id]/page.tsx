import { cookies } from "next/headers";
import { notFound } from "next/navigation";
import { Chat } from "@/components/chat";
import { DataStreamHandler } from "@/components/data-stream-handler";
import { DEFAULT_CHAT_MODEL } from "@/lib/ai/models";
import { getChatById, getMessagesByChatId, getVotesByChatId } from "@/lib/db/queries";
import { convertToUIMessages } from "@/lib/utils";

export default async function Page({ params }: { params: { id: string } }) {
      const { id } = params;
      let chat = await getChatById({ id });

      if (!chat) {
            // If the chat isn't in the DB yet, it might still be being created by the API route.
            // We'll provide a temporary skeleton so the client-side useChat can take over.
            chat = {
                  id,
                  title: 'New Chat',
                  userId: '00000000-0000-0000-0000-000000000000',
                  visibility: 'private',
                  createdAt: new Date(),
            } as any;
      }

      const messages = await getMessagesByChatId({ id });
      const votes = await getVotesByChatId({ id });
      const cookieStore = await cookies();
      const modelIdFromCookie = cookieStore.get("chat-model");
      const selectedModelId = modelIdFromCookie?.value || DEFAULT_CHAT_MODEL;

      return (
            <>
                  <Chat
                        id={chat.id}
                        initialMessages={convertToUIMessages(messages)}
                        initialChatModel={selectedModelId}
                        initialVisibilityType={chat.visibility}
                        isReadonly={false}
                        autoResume={true}
                  />
                  <DataStreamHandler />
            </>
      );
}
