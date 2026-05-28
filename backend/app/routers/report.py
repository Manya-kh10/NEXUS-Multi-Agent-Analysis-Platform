from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import Response
from app.services.report_service import generate_analysis_report
from app.services.agents import run_eda_agent, run_stats_agent, run_insight_agent
from app.services.ml_agent import run_ml_agent
import pandas as pd
import io

router = APIRouter()

@router.post("/generate")
async def generate_report(
    file: UploadFile = File(...),
    include_ml: bool = Form(default=True)
):
    contents = await file.read()
    df = pd.read_csv(io.BytesIO(contents))

    eda_result = run_eda_agent(df)
    stats_result = run_stats_agent(df)
    insight_result = run_insight_agent(eda_result, stats_result)

    ml_result = None
    if include_ml:
        ml_result = run_ml_agent(df)

    pdf_bytes = generate_analysis_report(
        filename=file.filename,
        eda_result=eda_result,
        stats_result=stats_result,
        insight_result=insight_result,
        ml_result=ml_result
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=nexus_report_{file.filename}.pdf"
        }
    )

@router.get("/status")
async def report_status():
    return {"status": "ready", "formats": ["pdf"]}