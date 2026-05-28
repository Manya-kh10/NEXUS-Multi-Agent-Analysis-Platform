from app.celery_app import celery_app
from app.services.agents import run_eda_agent, run_stats_agent, run_insight_agent
from app.services.cache import get_cached_result, set_cached_result
import pandas as pd
import io

@celery_app.task(bind=True, max_retries=3)
def run_analysis_task(self, csv_data: str, filename: str):
    try:
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
        self.update_state(
            state="FAILURE",
            meta={"status": f"Error: {str(exc)}", "progress": 0}
        )
        raise self.retry(exc=exc, countdown=5)