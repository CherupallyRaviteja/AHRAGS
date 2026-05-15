import { useState } from "react";
import { Send } from "lucide-react";
import useChatStore from "../store/chatStore";
import api from "../services/api";

function ChatInput() {

  const [input, setInput] = useState("");

  const addMessage = useChatStore(
    (state) => state.addMessage
  );

const handleSend = async () => {

  if (!input.trim()) return;

  const userMessage = input;

  addMessage({
    role: "user",
    content: userMessage,
  });

  setInput("");

  try {

    const response = await api.post(
      "/chat",
      {
        message: userMessage,
      }
    );

    addMessage({
      role: "assistant",
      content:
        response.data.response,
    });

  } catch (error) {

    addMessage({
      role: "assistant",
      content:
        "Backend connection failed.",
    });

    console.error(error);
  }
};
  return (
    <div className="border-t border-slate-800 p-4">

      <div className="flex gap-3">

        <input
          type="text"
          placeholder="Ask something..."
          value={input}
          onChange={(e) =>
            setInput(e.target.value)
          }
          onKeyDown={(e) =>
            e.key === "Enter" && handleSend()
          }
          className="flex-1 bg-slate-800 p-4 rounded-xl outline-none"
        />

        <button
          onClick={handleSend}
          className="bg-indigo-600 hover:bg-indigo-700 px-5 rounded-xl"
        >
          <Send size={20} />
        </button>

      </div>

    </div>
  );
}

export default ChatInput;