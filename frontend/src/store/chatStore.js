import { create } from "zustand";

const storedChats = JSON.parse(
  localStorage.getItem("chats")
);

const savedChats =
  storedChats && storedChats.length > 0
    ? storedChats
    : [
        {
          id: Date.now(),
          title: "New Chat",
          messages: [],
        },
      ];

const useChatStore = create((set) => ({
  chats: savedChats,

  activeChatId: savedChats[0].id,

  createChat: () =>
    set((state) => {
      const newChat = {
        id: Date.now(),
        title: "New Chat",
        messages: [],
      };

      const updatedChats = [
        newChat,
        ...state.chats,
      ];

      localStorage.setItem(
        "chats",
        JSON.stringify(updatedChats)
      );

      return {
        chats: updatedChats,
        activeChatId: newChat.id,
      };
    }),

  setActiveChat: (id) =>
    set({
      activeChatId: id,
    }),

  addMessage: (message) =>
    set((state) => {
      const updatedChats = state.chats.map(
        (chat) => {
          if (
            chat.id === state.activeChatId
          ) {
            const updatedMessages = [
              ...chat.messages,
              message,
            ];

            return {
              ...chat,
              title:
                chat.messages.length === 0
                  ? message.content.slice(0, 20)
                  : chat.title,
              messages: updatedMessages,
            };
          }

          return chat;
        }
      );

      localStorage.setItem(
        "chats",
        JSON.stringify(updatedChats)
      );

      return {
        chats: updatedChats,
      };
    }),

  deleteChat: (id) =>
    set((state) => {
      const updatedChats = state.chats.filter(
        (chat) => chat.id !== id
      );

      localStorage.setItem(
        "chats",
        JSON.stringify(updatedChats)
      );

      if (id !== state.activeChatId) {
        return {
          chats: updatedChats,
        };
      }

      return {
        chats: updatedChats,
        activeChatId: updatedChats[0]?.id || null,
      };
    }),

  clearChats: () => {
    localStorage.removeItem("chats");

    set({
      chats: [],
      activeChatId: null,
    });
  },

}));

export default useChatStore;
