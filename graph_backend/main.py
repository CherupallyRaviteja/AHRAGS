from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from rag_index import RAGIndex
from pathlib import Path
from fastapi import HTTPException
from controller import main

app = FastAPI()
rag = RAGIndex()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {
        "message": "Backend Running"
    }

@app.post("/chat")
async def chat(data: dict):
    try:
        user_message = data.get("message", "").strip()

        if not user_message:
            raise HTTPException(status_code=400, detail="Message is required")

        answer, sources, score, provenance = main(user_message)

        return {
            "response": answer,
            "sources": sources,
            "score": score,
            "provenance": provenance,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    UPLOAD_DIR = Path("uploads")
    UPLOAD_DIR.mkdir(exist_ok=True)

    file_path = UPLOAD_DIR / file.filename
    # Save uploaded file
 
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    
    rag.add_pdf(str(file_path))
    rag.save_to_db()

    return {"message": "Uploaded successfully"}

@app.get("/documents")
def get_documents():
    try:
        return {
            "documents": rag.get_documents()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{doc_name}")
def delete_document(doc_name: str):
    try:
        deleted = rag.delete_document(doc_name)

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Document '{doc_name}' not found"
            )

        return {
            "message": "Document deleted successfully",
            "document": doc_name
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))