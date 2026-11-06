"""Run the documented customer ownership migration during maintenance."""

import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.migrations.customer_tenants import migrate_customer_tenants


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--orphan-owners", type=Path, help="JSON mapping customer IDs to verified tenant IDs")
    args = parser.parse_args()
    owners = {}
    if args.orphan_owners:
        raw = json.loads(args.orphan_owners.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or any(type(value) is not int for value in raw.values()):
            raise ValueError("Orphan owner file must map customer IDs to integer tenant IDs")
        owners = {int(key): value for key, value in raw.items()}
    engine = create_async_engine(settings.database_url)
    try:
        print(json.dumps(await migrate_customer_tenants(engine, owners)))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
