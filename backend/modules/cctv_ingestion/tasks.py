"""
Distributed Task Queue Worker for CCTV Ingestion.
Maintains a single persistent event loop across tasks to prevent connection pool fragmentation.
"""
import asyncio
import logging
from celery import Celery
from modules.cctv_ingestion.service import process_cctv_payload

logger = logging.getLogger(__name__)

celery_app = Celery(
    "cctv_tasks", 
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

# Global tracker for the worker loop lifecycle
_WORKER_LOOP = None

def get_worker_event_loop():
    """
    Retrieves or establishes a single persistent event loop for the worker.
    Fixes the 'Event loop is closed' errors with global async resources like asyncpg.
    """
    global _WORKER_LOOP
    if _WORKER_LOOP is None or _WORKER_LOOP.is_closed():
        try:
            _WORKER_LOOP = asyncio.get_event_loop()
        except RuntimeError:
            _WORKER_LOOP = asyncio.new_event_loop()
            asyncio.set_event_loop(_WORKER_LOOP)
    return _WORKER_LOOP

@celery_app.task(rate_limit="15/m", max_retries=3, default_retry_delay=10)
def process_cctv_task(raw_payload: dict):
    """Executes ingestion using run_until_complete to keep connection states alive."""
    try:
        logger.info(f"[Worker] Processing enqueued task payload.")
        
        # Get the persistent worker loop structure
        loop = get_worker_event_loop()
        
        # FIXES THE CRASH: run_until_complete executes tasks without killing the underlying loop
        loop.run_until_complete(process_cctv_payload(raw_payload))
        
    except Exception as exc:
        logger.warning(f"[Worker] Task execution failed: {exc}. Retrying...")
        raise process_cctv_task.retry(exc=exc)