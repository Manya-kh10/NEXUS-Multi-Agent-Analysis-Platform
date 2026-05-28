from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from app.services.cleaning_pipeline import CleaningPipeline
import pandas as pd
import io
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

router = APIRouter()

# Dedicated thread pool for CPU-heavy cleaning work so the async event loop
# stays responsive for other requests (health checks, downloads, etc.).
_cleaning_pool = ThreadPoolExecutor(max_workers=2)

CLEANED_DIR = "/app/data/cleaned"


def _run_pipeline(contents: bytes, filename: str):
    """Synchronous helper executed inside the thread pool."""
    # low_memory=True uses chunked internal parsing inside pandas which
    # reduces peak memory for very wide / large CSVs.
    df = pd.read_csv(io.BytesIO(contents), low_memory=True)

    original_rows = len(df)
    original_cols = len(df.columns)

    pipeline = CleaningPipeline(df)
    pipeline.run_all()

    os.makedirs(CLEANED_DIR, exist_ok=True)
    output_path = os.path.join(CLEANED_DIR, filename)
    result = pipeline.save(output_path)

    return {
        "filename": filename,
        "original_shape": {"rows": original_rows, "cols": original_cols},
        "cleaned_shape": {"rows": result["rows"], "cols": result["columns"]},
        "cleaning_report": result["report"],
        "download_path": f"/api/pipeline/download/{filename}"
    }


@router.post("/clean")
async def clean_dataset(file: UploadFile = File(...)):
    contents = await file.read()
    loop = asyncio.get_running_loop()

    try:
        result = await loop.run_in_executor(
            _cleaning_pool,
            _run_pipeline,
            contents,
            file.filename,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(exc)}")

    return result


@router.get("/download/{filename}")
async def download_cleaned(filename: str):
    path = os.path.join(CLEANED_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=path,
        media_type="text/csv",
        filename=f"cleaned_{filename}"
    )


@router.get("/status")
async def pipeline_status():
    return {"status": "ready"}