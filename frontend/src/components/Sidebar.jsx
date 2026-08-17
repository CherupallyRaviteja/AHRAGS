import {
  Plus,
  Upload,
  FileText,
  Trash2,
  ChevronRight,
  X,
} from "lucide-react";
import useChatStore from "../store/chatStore";
import { useEffect, useState } from "react";
import DocumentsPanel from "./DocumentsPanel";
import api from "../services/api";

function Sidebar() {
  const chats = useChatStore((state) => state.chats);
  const activeChatId = useChatStore((state) => state.activeChatId);
  const createChat = useChatStore((state) => state.createChat);
  const setActiveChat = useChatStore((state) => state.setActiveChat);
  const deleteChat = useChatStore((state) => state.deleteChat);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [showDocuments, setShowDocuments] = useState(false);

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      setUploading(true);

      const response = await api.post("/upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      alert(response.data.message);
      fetchDocuments();
    } catch (error) {
      console.error(error);
      alert("Upload failed");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleDelete = (docName) => {
  setDeleteTarget({
    type: "document",
    id: docName,
    name: docName,
  });
};
const handleDeleteChat = (chatId) => {
  const chat = chats.find((item) => item.id === chatId);
  if (!chat) return;

  setDeleteTarget({
    type: "chat",
    id: chatId,
    name: chat.title,
  });
};
  const confirmDelete = async () => {
  if (!deleteTarget) return;

  if (deleteTarget.type === "chat") {
    deleteChat(deleteTarget.id);
    setDeleteTarget(null);
    return;
  }

  if (deleteTarget.type === "document") {
    try {
      await api.delete(`/documents/${deleteTarget.id}`);
      fetchDocuments();
    } catch (error) {
      console.error(error);
      alert("Delete failed");
    } finally {
      setDeleteTarget(null);
    }
  }
};
  const fetchDocuments = async () => {
    try {
      const response = await api.get("/documents");
      setDocuments(response.data.documents);
    } catch (error) {
      console.error(error);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col border-r border-slate-200 bg-white p-4 text-slate-900">
      <div className="mb-6 flex items-center gap-3 px-2">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-600 text-lg font-bold text-white shadow-sm">
          A
        </div>
        <div className="min-w-0">
          <h1 className="text-lg font-bold tracking-tight">AHRAGS</h1>
          <p className="text-xs text-slate-500">Agentic Hybrid RAG</p>
        </div>
      </div>

      <button
        onClick={createChat}
        className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 p-3 text-sm font-semibold text-white shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:bg-blue-700 hover:shadow-md active:translate-y-0"
      >
        <Plus size={18} />
        New Chat
      </button>

      <div className="mt-7 flex min-h-0 flex-1 flex-col">
        <div className="mb-3 flex items-center justify-between px-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Recent Chats
          </p>
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-500">
            {chats.length}
          </span>
        </div>

        <div className="min-h-0 flex-1 space-y-1 overflow-y-auto pr-1">
          {chats.length === 0 && (
            <p className="px-2 py-4 text-xs text-slate-400">No chats yet</p>
          )}

          {chats.map((chat) => (
            <div
              key={chat.id}
              onClick={() => setActiveChat(chat.id)}
              className={`group flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2.5 transition-all duration-200 ${
                activeChatId === chat.id
                  ? "border-blue-100 bg-blue-50 text-slate-900 shadow-sm"
                  : "border-transparent text-slate-600 hover:border-slate-200 hover:bg-slate-50 hover:text-slate-900"
              }`}
            >
              <span
                className={`h-2 w-2 shrink-0 rounded-full ${
                  activeChatId === chat.id ? "bg-blue-600" : "bg-slate-300"
                }`}
              />

              <span className="min-w-0 flex-1 truncate text-sm font-medium">
                {chat.title}
              </span>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteChat(chat.id);
                }}
                aria-label={`Delete ${chat.title}`}
                className="shrink-0 rounded-lg p-1.5 text-slate-400 opacity-0 transition-all hover:bg-red-50 hover:text-red-500 group-hover:opacity-100"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-4 border-t border-slate-200 pt-4">
          {!showDocuments ? (
            <button
              type="button"
              onClick={() => setShowDocuments(true)}
              className="w-full flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-left text-slate-700 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-600"
            >
              <FileText size={18} />
              
              <span className="flex-1 font-medium">
                Documents
              </span>

              {documents.length > 0 && (
                <span className="text-sm text-slate-400">
                  {documents.length}
                </span>
              )}

              <ChevronRight size={17} />
            </button>
          ) : (
            <DocumentsPanel
              documents={documents}
              onDelete={handleDelete}
              onClose={() => setShowDocuments(false)}
            />
          )}


        <label className="mt-2 flex w-full cursor-pointer items-center justify-center gap-2 rounded-xl border border-dashed border-blue-200 bg-blue-50/50 p-3 text-sm font-medium text-blue-600 transition-all duration-200 hover:border-blue-400 hover:bg-blue-50 hover:text-blue-700">
          <Upload size={17} />
          {uploading ? "Uploading..." : "Upload Document"}
          <input
            type="file"
            className="hidden"
            onChange={handleUpload}
            disabled={uploading}
          />
        </label>

        {uploading && (
          <div className="mt-3 h-1 overflow-hidden rounded-full bg-blue-100">
            <div className="h-full w-full animate-pulse bg-blue-500" />
          </div>
        )}
      </div>

      {deleteTarget && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/30 px-4 backdrop-blur-sm"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) {
              setDeleteTarget(null);
            }
          }}
        >
          <div
            className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-dialog-title"
          >
            <div className="flex items-start gap-4">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-red-50 text-red-500">
                <Trash2 size={20} />
              </div>

              <div className="min-w-0 flex-1">
                <h2
                  id="delete-dialog-title"
                  className="text-base font-semibold text-slate-900"
                >
                  {deleteTarget.type === "chat"
                    ? "Delete this chat?"
                    : "Delete this document?"}
                </h2>

                <p className="mt-1 text-sm leading-5 text-slate-500">
                  {deleteTarget.type === "chat"
                    ? "This chat and its messages will be permanently removed."
                    : "This document will be removed from your knowledge base."}
                </p>
              </div>

              <button
                type="button"
                onClick={() => setDeleteTarget(null)}
                aria-label="Close"
                className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
              >
                <X size={18} />
              </button>
            </div>

            <div className="mt-5 rounded-xl bg-slate-50 px-3 py-2.5">
              <p className="truncate text-sm font-medium text-slate-700">
                {deleteTarget.name}
              </p>
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setDeleteTarget(null)}
                className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-900"
              >
                Cancel
              </button>

              <button
                type="button"
                onClick={confirmDelete}
                className="flex items-center gap-2 rounded-xl bg-red-500 px-4 py-2.5 text-sm font-semibold text-white transition-all hover:bg-red-600 hover:shadow-md active:scale-[0.98]"
              >
                <Trash2 size={15} />
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}

export default Sidebar;
