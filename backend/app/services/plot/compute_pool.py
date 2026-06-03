"""Process pool compute gateway for CPU-intensive plotting tasks."""
import asyncio
from concurrent.futures import ProcessPoolExecutor
import structlog

logger = structlog.get_logger()

# Shared process pool, max 2 workers to prevent OOM
_executor = ProcessPoolExecutor(max_workers=2)

async def run_in_process(func, *args, **kwargs):
    """Run a CPU-intensive function in the process pool."""
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(_executor, func, *args, **kwargs)
    return result

def shutdown():
    """Shutdown the process pool."""
    _executor.shutdown(wait=False)
