from fastapi import APIRouter, UploadFile, File
from app.services.ml_agent import run_ml_agent
import pandas as pd
import io

router = APIRouter()

@router.post("/train")
async def train_models(file: UploadFile = File(...)):
    contents = await file.read()
    df = pd.read_csv(io.BytesIO(contents))

    result = run_ml_agent(df)

    return result

@router.get("/status")
async def ml_status():
    return {
        "status": "ready",
        "models": ["Random Forest", "Logistic Regression", "Linear Regression"],
        "tasks": ["classification", "regression"]
    }