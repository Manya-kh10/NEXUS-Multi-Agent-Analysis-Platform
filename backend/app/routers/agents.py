from fastapi import APIRouter, UploadFile, File
from app.services.agents import run_eda_agent, run_stats_agent, run_insight_agent
import pandas as pd
import io

router = APIRouter()

@router.post("/analyze")
async def analyze_dataset(file: UploadFile = File(...)):
    contents = await file.read()
    df = pd.read_csv(io.BytesIO(contents))

    eda_result = run_eda_agent(df)
    stats_result = run_stats_agent(df)
    insight_result = run_insight_agent(eda_result, stats_result)

    return {
        "eda": eda_result,
        "stats": stats_result,
        "insights": insight_result
    }

@router.get("/status")
async def agents_status():
    return {"status": "ready", "agents": ["EDA Agent", "Stats Agent", "Insight Agent"]}