
import json
import os
import sys

import mysql.connector
import psycopg
from psycopg.types.json import Jsonb
from dotenv import load_dotenv

load_dotenv()

TABLES = {
    "sources": [
        "id", "name", "base_url", "source_type", "is_enabled",
        "created_at", "updated_at",
    ],
    "jobs": [
        "id", "source_id", "external_id", "url_hash", "title",
        "company", "location", "experience", "salary_min",
        "salary_max", "salary_currency", "salary_period", "skills",
        "description", "job_url", "posted_at", "first_seen_at",
        "last_seen_at", "status", "created_at", "updated_at",
    ],
    "collection_runs": [
        "id", "source_id", "started_at", "finished_at", "status",
        "records_found", "records_inserted", "records_updated",
        "error_message",
    ],
}


def mysql_connection():
    required = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(
            "Missing MySQL environment variables: " + ", ".join(missing)
        )

    return mysql.connector.connect(
        host=os.environ["DB_HOST"],
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        connection_timeout=10,
    )


def postgres_connection():
    required = [
        "NEON_HOST", "NEON_DB", "NEON_USER", "NEON_PASSWORD"
    ]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(
            "Missing Neon environment variables: " + ", ".join(missing)
        )

    return psycopg.connect(
        host=os.environ["NEON_HOST"],
        port=int(os.getenv("NEON_PORT", "5432")),
        dbname=os.environ["NEON_DB"],
        user=os.environ["NEON_USER"],
        password=os.environ["NEON_PASSWORD"],
        sslmode=os.getenv("NEON_SSLMODE", "require"),
        connect_timeout=15,
    )


def normalize_value(table, column, value):
    if table == "sources" and column == "is_enabled":
        return bool(value)

    if table == "jobs" and column == "skills":
        if value is None:
            return None
        if isinstance(value, str):
            value = json.loads(value)
        return Jsonb(value)

    return value


def fetch_mysql_rows(connection, table, columns):
    column_sql = ", ".join(f"`{column}`" for column in columns)
    cursor = connection.cursor()
    try:
        cursor.execute(f"SELECT {column_sql} FROM `{table}` ORDER BY `id`")
        return cursor.fetchall()
    finally:
        cursor.close()


def copy_table(mysql_conn, pg_conn, table, columns):
    rows = fetch_mysql_rows(mysql_conn, table, columns)

    if not rows:
        print(f"{table}: source table is empty; nothing to copy.")
        return 0

    column_sql = ", ".join(f'"{column}"' for column in columns)
    placeholders = ", ".join(["%s"] * len(columns))
    insert_sql = (
        f'INSERT INTO "{table}" ({column_sql}) '
        f"VALUES ({placeholders})"
    )

    with pg_conn.cursor() as cursor:
        for row in rows:
            values = [
                normalize_value(table, column, value)
                for column, value in zip(columns, row)
            ]
            cursor.execute(insert_sql, values)

    print(f"{table}: copied {len(rows)} rows.")
    return len(rows)



def set_identity_sequence(pg_conn, table):
    with pg_conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT setval(
                pg_get_serial_sequence(%s, 'id'),
                COALESCE((SELECT MAX(id) FROM "{table}"), 1),
                EXISTS (SELECT 1 FROM "{table}")
            )
            """,
            (f"public.{table}",),
        )


def table_count(connection, table):
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
        return cursor.fetchone()[0]


def main():
    mysql_conn = None
    pg_conn = None

    try:
        mysql_conn = mysql_connection()
        pg_conn = postgres_connection()

        # This first version is deliberately a one-time copy into EMPTY
        # destination tables. It never deletes data from MySQL.
        with pg_conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) FROM (
                    SELECT 1 FROM sources
                    UNION ALL SELECT 1 FROM jobs
                    UNION ALL SELECT 1 FROM collection_runs
                ) AS existing_rows
                """
            )
            if cursor.fetchone()[0] != 0:
                raise RuntimeError(
                    "Neon destination tables are not empty. "
                    "No data was copied. Stop and review the destination."
                )

        expected = {}
        for table, columns in TABLES.items():
            expected[table] = len(
                fetch_mysql_rows(mysql_conn, table, columns)
            )

        # Foreign-key dependencies: sources first, then dependent tables.
        with pg_conn.transaction():
            for table in ("sources", "jobs", "collection_runs"):
                copy_table(mysql_conn, pg_conn, table, TABLES[table])

            for table in ("sources", "jobs", "collection_runs"):
                set_identity_sequence(pg_conn, table)

        print("\nMigration committed. Verifying row counts:")
        failed = False

        for table in ("sources", "jobs", "collection_runs"):
            actual = table_count(pg_conn, table)
            print(f"{table}: MySQL={expected[table]}, Neon={actual}")
            if actual != expected[table]:
                failed = True

        if failed:
            raise RuntimeError("Row-count verification failed.")

        print("\nAll table counts match. Keep MySQL as your backup.")

    except Exception as exc:
        print(f"\nMigration failed: {type(exc).__name__}: {exc}")
        sys.exit(1)

    finally:
        if mysql_conn is not None:
            mysql_conn.close()
        if pg_conn is not None:
            pg_conn.close()


if __name__ == "__main__":
    main()
