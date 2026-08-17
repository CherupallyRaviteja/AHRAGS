import { Copy, Check, Bot, User } from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";

function MessageBubble({ message }) {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
          <Bot size={16} />
        </div>
      )}

      <div className={`group max-w-[85%] sm:max-w-3xl ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm ${
            isUser
              ? "rounded-br-md bg-blue-600 text-white"
              : "rounded-bl-md border border-slate-200 bg-white text-slate-700"
          }`}
        >
          <ReactMarkdown
            components={{
              h1: ({ children }) => (
                <h1 className="mb-3 text-lg font-semibold text-current">{children}</h1>
              ),
              h2: ({ children }) => (
                <h2 className="mb-2 mt-4 text-base font-semibold text-current">{children}</h2>
              ),
              h3: ({ children }) => (
                <h3 className="mb-2 mt-3 font-semibold text-current">{children}</h3>
              ),
              p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
              ul: ({ children }) => (
                <ul className="mb-3 list-disc space-y-1 pl-5">{children}</ul>
              ),
              ol: ({ children }) => (
                <ol className="mb-3 list-decimal space-y-1 pl-5">{children}</ol>
              ),
              code: ({ children }) => (
                <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[0.9em] text-slate-800">
                  {children}
                </code>
              ),
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>

        <button
          onClick={handleCopy}
          aria-label="Copy message"
          className={`mt-1.5 flex items-center gap-1.5 px-1 text-[11px] text-slate-400 opacity-0 transition-all hover:text-blue-600 group-hover:opacity-100 ${
            isUser ? "ml-auto" : ""
          }`}
        >
          {copied ? <Check size={13} /> : <Copy size={13} />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>

      {isUser && (
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-100 text-blue-700">
          <User size={16} />
        </div>
      )}
    </div>
  );
}

export default MessageBubble;
