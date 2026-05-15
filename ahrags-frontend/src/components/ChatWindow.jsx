import { useEffect, useRef } from "react";

import MessageBubble from "./MessageBubble";
import ChatInput from "./ChatInput";
import useChatStore from "../store/chatStore";

function ChatWindow() {

  const chats = useChatStore(
    (state) => state.chats
  );

  const activeChatId = useChatStore(
    (state) => state.activeChatId
  );

  const activeChat = chats.find(
    (chat) => chat.id === activeChatId
  );

  const bottomRef = useRef(null);

  useEffect(() => {

    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
    });

  }, [activeChat?.messages]);

  return (
    <div className="flex flex-col flex-1">

      <div className="flex-1 overflow-y-auto p-6 space-y-6">

        {!activeChat && (
          <div className="text-slate-500 text-center mt-20 text-xl">
            Create a new chat
          </div>
        )}

        {activeChat?.messages.map(
          (msg, index) => (
            <MessageBubble
              key={index}
              message={msg}
            />
          )
        )}

        <div ref={bottomRef} />

      </div>

      <ChatInput />

    </div>
  );
}

export default ChatWindow;