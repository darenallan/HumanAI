from fastapi import FastAPI
from pydantic import BaseModel

from main import ai_hr_assistant
# pyrefly: ignore [missing-import]
from module.document_generator import generate_document
# pyrefly: ignore [missing-import]
from module.supervision import get_all_logs, get_security_alerts


app = FastAPI(
    title="API Assistant IA RH",
    description="API du module IA pour la plateforme RH intelligente",
    version="1.0.0"
)


class ChatRequest(BaseModel):
    user_id: int
    role: str
    question: str


class DocumentRequest(BaseModel):
    user_id: int
    role: str
    document_type: str


@app.get("/")
def home():
    return {
        "message": "API Assistant IA RH opérationnelle",
        "status": "running"
    }


@app.post("/chat")
def chat(request: ChatRequest):
    response = ai_hr_assistant(
        user_id=request.user_id,
        role=request.role,
        question=request.question
    )

    return response


@app.post("/generate-document")
def generate_hr_document(request: DocumentRequest):
    response = generate_document(
        user_id=request.user_id,
        role=request.role,
        document_type=request.document_type
    )

    return response


@app.get("/supervision/logs")
def supervision_logs():
    return get_all_logs()


@app.get("/supervision/alerts")
def supervision_alerts():
    return get_security_alerts()