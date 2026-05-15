import { Trash2, FileText } from "lucide-react";

function DocumentsPanel({
  documents,
  onDelete,
}) {

  return (
    <div className="mt-8">

      <p className="text-slate-400 text-sm mb-3">
        Uploaded Documents
      </p>

      <div className="space-y-2 max-h-60 overflow-y-auto">

        {documents.length === 0 && (
          <div className="text-slate-500 text-sm">
            No documents uploaded
          </div>
        )}

        {documents.map((doc) => (

          <div
            key={doc.name}
            className="bg-slate-800 p-3 rounded-xl flex items-center justify-between"
          >

            <div className="flex items-center gap-2 overflow-hidden">
              <FileText size={18} />

              <span className="truncate text-sm">
                {doc.name}
              </span>
            </div>

            <button
              onClick={() => onDelete(doc.name)}
              className="text-red-400 hover:text-red-500"
            >
              <Trash2 size={18} />
            </button>

          </div>

        ))}

      </div>

    </div>
  );
}

export default DocumentsPanel;