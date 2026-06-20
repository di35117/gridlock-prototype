"""
Distributed Task Queue Worker for CCTV Ingestion.
Uses Redis as a broker to handle high-throughput camera feeds gracefully.
"""
import asyncio
import logging
from celery import Celery
from modules.cctv_ingestion.service import process_cctv_payload

logger = logging.getLogger(__name__)

# Connect to the Redis container running on port 6379 from your docker-compose
celery_app = Celery(
    "cctv_tasks", 
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

# FIXES BOTTLENECK A & B: Throttling & Auto-Retry
# 'rate_limit="15/m"' means Celery will never execute more than 15 tasks per minute, 
# keeping you safely under Gemini's 429 error thresholds!
@celery_app.task(rate_limit="15/m", max_retries=3, default_retry_delay=10)
def process_cctv_task(raw_payload: dict):
    """Synchronous Celery wrapper that handles the payload execution in a safe async loop."""
    try:
        logger.info(f"[Worker] Processing enqueued task payload.")
        # Execute your existing service logic within a dedicated worker event loop
        asyncio.run(process_cctv_payload(raw_payload))
    except Exception as exc:
        logger.warning(f"[Worker] Task failed due to network/DB pressure. Retrying in 10s... Error: {exc}")
        # Automatically retry the task if the DB or external API blipped
        raise process_cctv_task.retry(exc=exc)