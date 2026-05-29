from app.core.celery_app import celery_app
from app.services.agents import run_eda_agent, run_stats_agent, run_insight_agent
from app.services.cache import get_cached_result, set_cached_result
import pandas as pd
import io
import asyncio
import logging

logger = logging.getLogger("nexus.tasks")

async def _fetch_dataset_data(dataset_id: str) -> str:
    """Helper to fetch dataset metadata and download CSV bytes asynchronously."""
    from app.database import AsyncSessionLocal
    from app.services import dataset_service, storage_service

    async with AsyncSessionLocal() as db:
        dataset = await dataset_service.get_dataset_by_id(db, dataset_id)
        if not dataset:
            raise ValueError(f"Dataset not found for ID: {dataset_id}")
            
        storage_url = dataset.cleaned_storage_url or dataset.storage_url
        if not storage_url:
            raise ValueError(f"No storage URL recorded for dataset: {dataset_id}")
            
        file_bytes = await storage_service.download_file(storage_url)
        return file_bytes.decode("utf-8")

@celery_app.task(bind=True, max_retries=3)
def run_analysis_task(self, csv_data_or_id: str, filename: str):
    try:
        csv_data = ""
        is_by_id = False
        
        # Determine if parameter is a dataset ID or raw CSV
        # Dataset ID will be a short UUID-like string with no newlines
        if "\n" not in csv_data_or_id and len(csv_data_or_id) < 100:
            is_by_id = True
            self.update_state(state="PROGRESS", meta={"status": "Fetching dataset from cloud storage...", "progress": 2})
            try:
                # Run the async download in a synchronous thread context
                csv_data = asyncio.run(_fetch_dataset_data(csv_data_or_id))
            except Exception as e:
                logger.error(f"Failed to download dataset {csv_data_or_id}: {e}")
                # If lookup fails, try treating it as raw data or raise exception
                raise e
        else:
            csv_data = csv_data_or_id

        # Check cache first
        cached = get_cached_result(csv_data)
        if cached:
            return {
                "status": "complete",
                "filename": filename,
                "cached": True,
                **cached
            }

        self.update_state(state="PROGRESS", meta={"status": "Loading dataset...", "progress": 5})
        df = pd.read_csv(io.StringIO(csv_data))

        self.update_state(state="PROGRESS", meta={"status": "EDA Agent running...", "progress": 10})
        eda_result = run_eda_agent(df)

        self.update_state(state="PROGRESS", meta={
            "status": "Stats Agent running...",
            "progress": 50,
            "eda": eda_result
        })
        stats_result = run_stats_agent(df)

        self.update_state(state="PROGRESS", meta={
            "status": "Insight Agent running...",
            "progress": 80,
            "eda": eda_result,
            "stats": stats_result
        })
        insight_result = run_insight_agent(eda_result, stats_result)

        self.update_state(state="PROGRESS", meta={
            "status": "Saving to cache...",
            "progress": 95,
            "eda": eda_result,
            "stats": stats_result,
            "insights": insight_result
        })

        result = {
            "eda": eda_result,
            "stats": stats_result,
            "insights": insight_result
        }

        set_cached_result(csv_data, result)

        return {
            "status": "complete",
            "filename": filename,
            "cached": False,
            **result
        }

    except Exception as exc:
        logger.exception(f"Task execution failure for file {filename}: {exc}")
        self.update_state(
            state="FAILURE",
            meta={"status": f"Swarm analysis task failed: {str(exc)}", "progress": 0}
        )
        raise exc