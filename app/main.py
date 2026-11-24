import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.ingest import run_ingest, ingest_pdf, DATA_DIR
from app.rag import ask_rag, clear_cache

app = FastAPI(title="ReguRAG API", description="PDF Tabanli Mevzuat ve Risk Asistani")


@app.on_event("startup")
def startup_event():
    run_ingest()


class QuestionRequest(BaseModel):
    question: str


@app.get("/")
def home():
    return FileResponse("app/index.html")


@app.get("/files")
def list_files():
    files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith(".pdf")]
    return {"files": files}


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        name = os.path.basename(file.filename)
        file_path = os.path.join(DATA_DIR, name)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        chunks = ingest_pdf(file_path, name)
        clear_cache()
        return {"filename": name, "chunks_added": chunks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Yükleme hatası: {e}")


@app.post("/ask")
def ask(req: QuestionRequest):
    try:
        return ask_rag(req.question)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Model hatası: {e}")