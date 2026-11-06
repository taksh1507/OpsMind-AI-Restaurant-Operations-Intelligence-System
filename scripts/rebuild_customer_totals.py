"""Rebuild one tenant's historical customer totals during maintenance."""

import argparse
import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.services.customer_totals import rebuild_customer_totals


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant-id", type=int, required=True)
    args = parser.parse_args()
    if args.tenant_id < 1:
        parser.error("--tenant-id must be positive")
    engine = create_async_engine(settings.database_url)
    try:
        async with async_sessionmaker(engine)() as db:
            async with db.begin():
                count = await rebuild_customer_totals(db, args.tenant_id)
        print(f"Rebuilt totals for {count} customers in tenant {args.tenant_id}.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
