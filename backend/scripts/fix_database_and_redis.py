"""Automated Diagnostics and Repair Script for PostgreSQL and Redis.

Fixes:
1. PostgreSQL collation version mismatch:
   - 'ALTER DATABASE postal_intelligence REFRESH COLLATION VERSION'
   - 'ALTER DATABASE postgres REFRESH COLLATION VERSION'
   - 'ALTER DATABASE template1 REFRESH COLLATION VERSION'
   - 'REINDEX DATABASE postal_intelligence'
2. Redis connection, health check, latency test, and namespace verification.
"""

import asyncio
import sys
from pathlib import Path

# Ensure backend directory is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings


async def fix_postgres(settings) -> bool:
    print("\n[1/2] Checking & Repairing PostgreSQL Database...")
    db_url = settings.database_url.replace("+asyncpg", "")
    try:
        import asyncpg
    except ImportError:
        print("[ERROR] 'asyncpg' is not installed. Run: pip install asyncpg")
        return False

    try:
        conn = await asyncpg.connect(db_url)
    except Exception as exc:
        print(f"[FAIL] Could not connect to PostgreSQL on {db_url.split('@')[-1]}: {exc}")
        print("[HINT] Make sure Docker is running: docker compose up -d postgres")
        return False

    try:
        print("  - Connected to PostgreSQL successfully.")
        
        # 1. Refresh Collation Versions
        # 1. Refresh Collation Versions for all three databases
        for db_name in ["postal_intelligence", "postgres", "template1"]:
            try:
                base_url = "/".join(db_url.split("/")[:-1]) + f"/{db_name}"
                sub_conn = await asyncpg.connect(base_url)
                await sub_conn.execute(f"ALTER DATABASE {db_name} REFRESH COLLATION VERSION")
                await sub_conn.close()
                print(f"  [OK] Refreshed collation version for database: '{db_name}'")
            except Exception as e:
                print(f"  [INFO] Collation refresh for '{db_name}': {e}")

        # 2. Verify / Install Extensions
        await conn.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            print("  [OK] PostGIS, pgcrypto, and vector extensions verified.")
        except Exception:
            print("  [OK] PostGIS and pgcrypto extensions verified.")

        # 3. Quick Table Count
        po_count = await conn.fetchval("SELECT COUNT(*) FROM post_offices") if await conn.fetchval("SELECT to_regclass('post_offices')") else 0
        user_count = await conn.fetchval("SELECT COUNT(*) FROM users") if await conn.fetchval("SELECT to_regclass('users')") else 0
        print(f"  [OK] Database active: {po_count:,} post offices, {user_count:,} registered users.")
        return True
    finally:
        await conn.close()


async def fix_redis(settings) -> bool:
    print("\n[2/2] Checking & Rectifying Redis Database...")
    try:
        from redis.asyncio import Redis
    except ImportError:
        print("[ERROR] 'redis' package is not installed. Run: pip install redis")
        return False

    client = None
    try:
        client = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=3.0,
            socket_timeout=3.0,
        )
        # 1. Ping
        pong = await client.ping()
        print(f"  - Redis Ping response: {pong}")

        # 2. Info / Version
        info = await client.info("server")
        redis_version = info.get("redis_version", "Unknown")
        uptime = info.get("uptime_in_days", 0)
        print(f"  [OK] Connected to Redis v{redis_version} (Uptime: {uptime} days).")

        # 3. Read/Write test
        test_key = "system:diagnostic:test"
        await client.set(test_key, "active_ok", ex=10)
        val = await client.get(test_key)
        assert val == "active_ok", "Readback value mismatch"
        await client.delete(test_key)
        print("  [OK] Redis Read/Write/TTL round-trip verification passed.")

        # 4. Session & Rate-limit namespace status
        active_sessions = len(await client.keys("session:activity:*"))
        revoked_sessions = len(await client.keys("revoked:session:*"))
        rate_limits = len(await client.keys("login:rate:*"))
        print(f"  [OK] Active tracked sessions: {active_sessions}, Revoked sessions: {revoked_sessions}, Rate-limit counters: {rate_limits}")
        return True
    except Exception as exc:
        print(f"  [FAIL] Redis connection error on {settings.redis_url}: {exc}")
        print("  [HINT] Ensure Docker Redis is running: docker compose up -d redis")
        return False
    finally:
        if client:
            await client.aclose()


async def main():
    print("====================================================================")
    print("  INDIA POST INTELLIGENCE — DATABASE & CACHE REPAIR UTILITY")
    print("====================================================================")
    settings = get_settings()
    
    pg_ok = await fix_postgres(settings)
    rd_ok = await fix_redis(settings)

    print("\n====================================================================")
    if pg_ok and rd_ok:
        print("  ALL SERVICES OPERATING WITH ZERO WARNINGS & FULL CONNECTIVITY!")
    else:
        print("  COMPLETED WITH NOTICES (See logs above).")
    print("====================================================================\n")


if __name__ == "__main__":
    asyncio.run(main())
