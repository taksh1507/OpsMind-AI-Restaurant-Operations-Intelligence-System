"""Run APScheduler in one dedicated process, separate from API workers."""
import asyncio
import signal

from app.core import settings
from app.core.logging_config import setup_logging
from app.database import close_db, init_db


async def main():
    if not settings.run_scheduler:
        raise RuntimeError("Set RUN_SCHEDULER=true for the scheduler service.")
    setup_logging()
    await init_db(settings.database_url)
    from app.core.scheduler import start_scheduler, shutdown_scheduler

    start_scheduler()
    stopped = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stopped.set)
    try:
        await stopped.wait()
    finally:
        await shutdown_scheduler()
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
