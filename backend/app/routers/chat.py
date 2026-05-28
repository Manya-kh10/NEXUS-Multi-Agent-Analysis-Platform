from fastapi import APIRouter, UploadFile, File, Form
from app.services.chat_agent import run_chat_agent
import pandas as pd
import io
import json

router = APIRouter()

@router.post("/message")
async def chat_with_agent(
    message: str = Form(...),
    history: str = Form(default="[]"),
    file: UploadFile = File(...)
):
    contents = await file.read()
    df = pd.read_csv(io.BytesIO(contents))

    try:
        chat_history = json.loads(history)
    except Exception:
        chat_history = []

    result = run_chat_agent(
        user_message=message,
        df=df,
        chat_history=chat_history
    )

    return {
        "role": "assistant",
        "content": result,
        "message": message
    }

@router.get("/status")
async def chat_status():
    return {"status": "ready", "model": "llama-3.3-70b-versatile"}