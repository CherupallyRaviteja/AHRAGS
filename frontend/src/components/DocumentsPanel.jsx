import { Trash2, FileText, Files, X } from "lucide-react";

function DocumentsPanel({ documents, onDelete, onClose }) {
  return (
    <div className="mt-3 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <div className="flex items-center gap-2">
          <Files size={16} className="text-blue-600" />
          <div>
            <p className="text-sm font-semibold text-slate-800">Documents</p>
            <p className="text-[11px] text-slate-400">
              {documents.length} {documents.length === 1 ? "document" : "documents"}
            </p>
          </div>
        </div>

        <button
          onClick={onClose}
          aria-label="Close documents"
          className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
        >
          <X size={16} />
        </button>
      </div>

      <div className="max-h-56 space-y-1.5 overflow-y-auto p-2">
        {documents.length === 0 && (
          <div className="px-3 py-6 text-center">
            <FileText size={22} className="mx-auto mb-2 text-slate-300" />
            <p className="text-xs text-slate-400">No documents uploaded</p>
          </div>
        )}

        {documents.map((doc) => (
          <div
            key={doc.name}
            className="group flex items-center justify-between gap-2 rounded-xl px-3 py-2.5 transition-colors hover:bg-slate-50"
          >
            <div className="flex min-w-0 items-center gap-2.5">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
                <FileText size={15} />
              </div>
              <span className="truncate text-xs font-medium text-slate-600" title={doc.name}>
                {doc.name}
              </span>
            </div>

            <button
              onClick={() => onDelete(doc.name)}
              aria-label={`Delete ${doc.name}`}
              className="shrink-0 rounded-lg p-1.5 text-slate-300 opacity-0 transition-all hover:bg-red-50 hover:text-red-500 group-hover:opacity-100"
            >
              <Trash2 size={15} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default DocumentsPanel;
