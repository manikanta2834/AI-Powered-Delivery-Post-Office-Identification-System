import argparse
import asyncio
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import asyncpg

from app.core.config import get_settings
from app.core.db import initialize_database


async def import_pincode_csv(csv_path: Path) -> tuple[int, int]:
    settings = get_settings()
    connection = await asyncpg.connect(settings.database_url.replace("+asyncpg", ""))
    try:
        await initialize_database()
        await connection.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
        await connection.execute(
            """
            CREATE TEMP TABLE pincode_import (
                city TEXT,
                area TEXT,
                pincode TEXT,
                district TEXT,
                state TEXT
            )
            """
        )
        with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            await connection.copy_records_to_table(
                "pincode_import",
                records=(
                    (
                        row["City"].strip(),
                        row["Area"].strip(),
                        row["Pincode"].strip(),
                        row["District"].strip(),
                        row["State"].strip(),
                    )
                    for row in csv.DictReader(csv_file)
                    if row["City"].strip() and row["Area"].strip() and row["Pincode"].strip()
                ),
                columns=["city", "area", "pincode", "district", "state"],
            )

        await connection.execute(
            """
            INSERT INTO post_offices (id, name, pin_code, district, state, metadata_json)
            SELECT gen_random_uuid(), city, pincode, district, state,
                   jsonb_build_object('source', 'India_pincode.csv', 'imported', true)
            FROM pincode_import
            WHERE pincode ~ '^[0-9]{6}$'
              AND NOT EXISTS (
                  SELECT 1
                  FROM post_offices AS existing
                  WHERE existing.name = pincode_import.city
                    AND existing.pin_code = pincode_import.pincode
                    AND existing.district = pincode_import.district
                    AND existing.state = pincode_import.state
              )
                        GROUP BY city, pincode, district, state
            """
        )
        await connection.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_localities_import_key
            ON localities (name, pin_code, district, state)
            """
        )
        await connection.execute(
            """
            INSERT INTO localities (id, name, district, state, pin_code, post_office_id, metadata_json)
            SELECT gen_random_uuid(), source.area, source.district, source.state, source.pincode,
                   office.id,
                   jsonb_build_object('source', 'India_pincode.csv', 'imported', true)
            FROM (
                SELECT DISTINCT area, city, pincode, district, state
                FROM pincode_import
                WHERE pincode ~ '^[0-9]{6}$'
            ) AS source
            JOIN post_offices AS office
              ON office.name = source.city
             AND office.pin_code = source.pincode
             AND office.district = source.district
             AND office.state = source.state
            WHERE NOT EXISTS (
                SELECT 1
                FROM localities AS existing
                WHERE existing.name = source.area
                  AND existing.pin_code = source.pincode
                  AND existing.district = source.district
                  AND existing.state = source.state
            )
            """
        )
        post_office_count = await connection.fetchval(
            "SELECT COUNT(*) FROM post_offices WHERE metadata_json->>'source' = 'India_pincode.csv'"
        )
        locality_count = await connection.fetchval(
            "SELECT COUNT(*) FROM localities WHERE metadata_json->>'source' = 'India_pincode.csv'"
        )
        await connection.execute("DROP TABLE pincode_import")
        return post_office_count, locality_count
    finally:
        await connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import India PIN/locality data into Postal Intelligence.")
    parser.add_argument("csv_path", type=Path)
    args = parser.parse_args()
    post_offices, localities = asyncio.run(import_pincode_csv(args.csv_path))
    print(f"Imported post offices: {post_offices}")
    print(f"Imported localities: {localities}")


if __name__ == "__main__":
    main()
