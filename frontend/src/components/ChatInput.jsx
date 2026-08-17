import { useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";
import useChatStore from "../store/chatStore";
import api from "../services/api";

function ChatInput() {
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const textareaRef = useRef(null);

  const addMessage = useChatStore((state) => state.addMessage);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = "auto";
    const nextHeight = Math.min(Math.max(textarea.scrollHeight, 52), 160);
    textarea.style.height = `${nextHeight}px`;
  }, [input]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();

    addMessage({
      role: "user",
      content: userMessage,
    });

    setInput("");
    setIsLoading(true);

    try {
      const response = await api.post("/chat", {
        message: userMessage,
      });

      addMessage({
        role: "assistant",
        content: response.data.response,
      });
    } catch (error) {
      addMessage({
        role: "assistant",
        content: "Backend connection failed.",
      });

      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="shrink-0 border-t border-slate-200 bg-white px-4 py-4 sm:px-6">
      <div className="mx-auto max-w-5xl">
        <div
          className={`flex items-end gap-3 rounded-2xl border bg-white p-2 shadow-sm transition-all duration-200 ${
            isLoading
              ? "border-slate-200"
              : "border-slate-300 focus-within:border-blue-500 focus-within:ring-4 focus-within:ring-blue-500/10"
          }`}
        >
          <textarea
            ref={textareaRef}
            rows={1}
            placeholder={
              isLoading
                ? "AHRAGS is thinking..."
                : "Ask anything about your documents..."
            }
            value={input}
            disabled={isLoading}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            className="min-h-[52px] max-h-40 flex-1 resize-none overflow-y-auto bg-transparent px-3 py-3 text-sm leading-6 text-slate-900 outline-none placeholder:text-slate-400 disabled:cursor-not-allowed disabled:opacity-60"
          />

          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            aria-label="Send message"
            className="mb-0.5 flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white shadow-sm transition-all duration-200 hover:bg-blue-700 hover:shadow-md disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400 disabled:shadow-none"
          >
            <Send size={18} />
          </button>
        </div>

        <p className="mt-2 text-center text-[11px] text-slate-400">
          Enter to send · Shift + Enter for a new line
        </p>
      </div>
    </div>
  );
}

export default ChatInput;
