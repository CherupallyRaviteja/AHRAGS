from fastapi import FastAPI,UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import os
from rag_index import RAGIndex

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag = RAGIndex()

class ChatRequest(BaseModel):
    message: str

@app.get("/")
def home():
    return {
        "message": "AHAGS Backend Running"
    }

from controller import main

@app.post("/chat")
async def chat(req: ChatRequest):

    answer = main(req.message)
  
    return {
        "response": answer,
    }

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...)
):

    os.makedirs(
        "temp",
        exist_ok=True
    )

    file_path = f"temp/{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(
            file.file,
            buffer
        )

    try:

        rag.add_pdf(file_path)

        rag.save_to_db()
        
        os.remove(file_path)

        return {
            "message":
            f"{file.filename} added successfully"
        }

    except Exception as e:

        return {
            "message":
            f"Upload failed: {str(e)}"
        }
    
@app.get("/documents")
def get_documents():

    docs = rag.get_documents()

    return {
        "documents": docs
    }

@app.delete("/documents/{doc_name}")
def delete_document(doc_name: str):

    try:

        rag.delete_document(doc_name)

        rag.save_to_db()

        return {
            "message": f"{doc_name} deleted"
        }

    except Exception as e:

        return {
            "message": str(e)
        }
