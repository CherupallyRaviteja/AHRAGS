import { Plus, Upload } from "lucide-react";
import useChatStore from "../store/chatStore";
import { useEffect, useState } from "react";
import DocumentsPanel from "./DocumentsPanel";
import api from "../services/api";

function Sidebar() {

  const chats = useChatStore(
    (state) => state.chats
  );

  const activeChatId = useChatStore(
    (state) => state.activeChatId
  );

  const createChat = useChatStore(
    (state) => state.createChat
  );

  const setActiveChat = useChatStore(
    (state) => state.setActiveChat
  );

  const clearChats = useChatStore(
    (state) => state.clearChats
  );

  const [documents, setDocuments] = useState([]);
const [uploading, setUploading] = useState(false);

const handleUpload = async (e) => {

  const file = e.target.files[0];

  if (!file) return;

  const formData = new FormData();

  formData.append("file", file);

  try {

    setUploading(true);

    const response = await api.post(
      "/upload",
      formData,
      {
        headers: {
          "Content-Type":
            "multipart/form-data",
        },
      }
    );

    alert(response.data.message);

    fetchDocuments();

  } catch (error) {

    console.error(error);

    alert("Upload failed");

  } finally {

    setUploading(false);
  }
};

const handleDelete = async (docName) => {

  const confirmDelete = window.confirm(
    `Delete ${docName} from memory?`
  );

  if (!confirmDelete) return;

  try {

    await api.delete(
      `/documents/${docName}`
    );

    fetchDocuments();

  } catch (error) {

    console.error(error);

    alert("Delete failed");
  }
};

const fetchDocuments = async () => {

  try {

    const response = await api.get(
      "/documents"
    );

    setDocuments(
      response.data.documents
    );

  } catch (error) {
    console.error(error);
  }
};

useEffect(() => {
  fetchDocuments();
}, []);

  return (
    <div className="w-72 bg-grey-500 border-r border-black p-4">

      <h1 className="text-2xl font-bold mb-6">
        AHRAGS
      </h1>

      <button
        onClick={createChat}
        className="w-full flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 p-3 rounded-xl mb-4"
      >
        <Plus size={18} />
        New Chat
      </button>

   <div>

  <label className="w-full flex items-center gap-2 bg-slate-800 hover:bg-slate-700 p-3 rounded-xl cursor-pointer">

    <Upload size={18} />

    {
      uploading
        ? "Uploading..."
        : "Upload Document"
    }

    <input
      type="file"
      className="hidden"
      onChange={handleUpload}
    />

  </label>

  {uploading && (

    <div className="w-full h-2 bg-slate-700 rounded-full mt-3 overflow-hidden">

      <div className="h-full bg-indigo-500 animate-pulse w-full" />

    </div>

  )}

</div>
      <button
        onClick={clearChats}
        className="w-full mt-3 bg-red-600 hover:bg-red-700 p-3 rounded-xl"
      >
        Clear Chats
      </button>

      <div className="mt-8">

        <p className="text-slate-400 text-sm mb-3">
          Recent Chats
        </p>

        <div className="space-y-2">

          {chats.map((chat) => (

            <div
              key={chat.id}
              onClick={() =>
                setActiveChat(chat.id)
              }
              className={`p-3 rounded-lg cursor-pointer ${
                activeChatId === chat.id
                  ? "bg-indigo-600"
                  : "bg-slate-800"
              }`}
            >
              {chat.title}
            </div>

          ))}

        </div>

      </div>
  <DocumentsPanel
  documents={documents}
  onDelete={handleDelete}
/>
    </div>

  );

}

export default Sidebar;