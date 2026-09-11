"""Dataset Readiness & Verification Probe."""

import asyncio
import sys
from pathlib import Path

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings


async def check():
    settings = get_settings()
    try:
        import asyncpg
    except ImportError:
        print("  [WARN] asyncpg not available, skipping pre-check.")
        sys.exit(0)

    try:
        conn = await asyncpg.connect(settings.database_url.replace("+asyncpg", ""))
        reg = await conn.fetchval("SELECT to_regclass('post_offices')")
        cnt = await conn.fetchval("SELECT COUNT(*) FROM post_offices") if reg else 0
        loc_cnt = await conn.fetchval("SELECT COUNT(*) FROM localities") if await conn.fetchval("SELECT to_regclass('localities')") else 0
        await conn.close()
        
        if cnt > 100:
            print(f"  [OK] PostGIS loaded with {cnt:,} post offices and {loc_cnt:,} localities.")
            sys.exit(0)
        else:
            print(f"  [INFO] PostGIS contains {cnt} post offices (ingestion needed).")
            sys.exit(1)
    except Exception as exc:
        print(f"  [WARN] Could not verify database records: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(check())
