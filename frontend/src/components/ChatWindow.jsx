import { useEffect, useRef } from "react";
import {
  Bot,
  FileSearch,
  MessageCircleQuestion,
  Lightbulb,
  Search,
  Sparkles,
} from "lucide-react";
import MessageBubble from "./MessageBubble";
import ChatInput from "./ChatInput";
import useChatStore from "../store/chatStore";

function ChatWindow() {
  const chats = useChatStore((state) => state.chats);
  const activeChatId = useChatStore((state) => state.activeChatId);

  const activeChat = chats.find((chat) => chat.id === activeChatId);
  const bottomRef = useRef(null);
  const hasMessages = activeChat?.messages?.length > 0;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeChat?.messages]);

  return (
    <main className="flex min-w-0 flex-1 flex-col bg-slate-50 text-slate-900">
      <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-5 sm:px-7">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
            <Bot size={18} />
          </div>
          <div className="min-w-0">
            <h2 className="truncate text-sm font-semibold text-slate-900">
              {activeChat?.title || "AHRAGS"}
            </h2>
            <p className="text-xs text-slate-500">Agentic Hybrid RAG Assistant</p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
          <span className="h-2 w-2 rounded-full bg-emerald-500" />
          Ready
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {!activeChat && (
          <div className="flex min-h-full items-center justify-center px-6 py-16">
            <div className="max-w-lg text-center">
              <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
                <Sparkles size={27} />
              </div>
              <h1 className="text-3xl font-bold tracking-tight text-slate-900">
                Start a new conversation
              </h1>
              <p className="mt-3 text-sm leading-6 text-slate-500">
                Create a chat and ask questions about the documents available to AHRAGS.
              </p>
            </div>
          </div>
        )}

        {activeChat && !hasMessages && (
          <div className="mx-auto flex min-h-full w-full max-w-6xl items-center justify-center px-5 py-10 sm:px-8">
            <div className="w-full pb-10">
              <div className="mx-auto max-w-2xl text-center">
                <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
                  <Sparkles size={24} />
                </div>
                <h1 className="text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
                  Welcome to <span className="text-blue-600">AHRAGS</span>
                </h1>
                <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-500 sm:text-base">
                  Ask questions about your documents and get answers grounded in your knowledge base.
                </p>
              </div>

             <div className="mx-auto mt-7 grid max-w-3xl grid-cols-1 gap-3 sm:grid-cols-3">
                {/* Find Information */}
                <button
                  type="button"
                  className="group rounded-xl border border-slate-200 bg-white p-4 text-left shadow-sm transition-all duration-200 hover:-translate-y-1 hover:border-blue-200 hover:bg-blue-50/40 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                >
                  <div className="flex items-start gap-3">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600 transition-colors group-hover:bg-blue-100">
                      <FileSearch size={18} />
                    </span>

                    <div className="min-w-0">
                      <p className="font-semibold text-sm text-slate-900">
                        Find information
                      </p>

                      <p className="mt-1 text-xs leading-4 text-slate-500">
                        Locate specific information in your documents.
                      </p>
                    </div>
                  </div>
                </button>

                {/* Search Knowledge */}
                <button
                  type="button"
                  className="group rounded-xl border border-slate-200 bg-white p-4 text-left shadow-sm transition-all duration-200 hover:-translate-y-1 hover:border-blue-200 hover:bg-blue-50/40 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                >
                  <div className="flex items-start gap-3">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600 transition-colors group-hover:bg-blue-100">
                      <Search size={18} />
                    </span>

                    <div className="min-w-0">
                      <p className="font-semibold text-sm text-slate-900">
                        Search your knowledge
                      </p>

                      <p className="mt-1 text-xs leading-4 text-slate-500">
                        Retrieve relevant facts, topics, or keywords.
                      </p>
                    </div>
                  </div>
                </button>

                {/* Explain Concept */}
                <button
                  type="button"
                  className="group rounded-xl border border-slate-200 bg-white p-4 text-left shadow-sm transition-all duration-200 hover:-translate-y-1 hover:border-blue-200 hover:bg-blue-50/40 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                >
                  <div className="flex items-start gap-3">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600 transition-colors group-hover:bg-blue-100">
                      <Lightbulb size={18} />
                    </span>

                    <div className="min-w-0">
                      <p className="font-semibold text-sm text-slate-900">
                        Explain a concept
                      </p>

                      <p className="mt-1 text-xs leading-4 text-slate-500">
                        Get explanations grounded in your documents.
                      </p>
                    </div>
                  </div>
                </button>
              </div>
            </div>
          </div>
        )}

        {hasMessages && (
          <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-7 sm:px-6 sm:py-9">
            {activeChat.messages.map((msg, index) => (
              <MessageBubble key={index} message={msg} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}

        {!hasMessages && <div ref={bottomRef} />}
      </div>

      <ChatInput />
    </main>
  );
}

export default ChatWindow;
