"""Database configuration and driver-neutral helpers for V4Career."""
import os
import logging
from threading import Lock
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
_mysql_pool = None
_mysql_pool_lock = Lock()
_postgres_pool = None
_postgres_pool_lock = Lock()

load_dotenv()

DB_ENGINE = os.getenv("DB_ENGINE", "postgres").strip().lower()
if DB_ENGINE in {"postgresql", "neon"}:
    DB_ENGINE = "postgres"
if DB_ENGINE not in {"mysql", "postgres"}:
    raise RuntimeError("DB_ENGINE must be 'mysql' or 'postgres'.")

# The tuple is used by Flask routes to catch driver-specific database errors.
_errors = []
try:
    from psycopg import Error as PsycopgError
    _errors.append(PsycopgError)
except ImportError:
    pass
try:
    from mysql.connector import Error as MySQLError
    _errors.append(MySQLError)
except ImportError:
    pass
DATABASE_ERRORS = tuple(_errors) or (Exception,)


def is_mysql():
    return DB_ENGINE == "mysql"


def get_connection():
    """Open a connection using the selected engine's environment settings."""
    if is_mysql():
        required = ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD")
        missing = [key for key in required if not os.getenv(key)]
        if missing:
            raise RuntimeError("Missing MySQL configuration: " + ", ".join(missing))
        try:
            from mysql.connector.pooling import MySQLConnectionPool
        except ImportError as exc:
            raise RuntimeError("MySQL selected but mysql-connector-python is not installed.") from exc

        # Aiven MySQL is remote: reusing authenticated TLS connections avoids
        # paying the TCP/TLS/authentication cost on every small API query.
        global _mysql_pool
        if _mysql_pool is None:
            with _mysql_pool_lock:
                if _mysql_pool is None:
                    kwargs = {
                        "host": os.getenv("DB_HOST"),
                        "port": int(os.getenv("DB_PORT", "3306")),
                        "database": os.getenv("DB_NAME"),
                        "user": os.getenv("DB_USER"),
                        "password": os.getenv("DB_PASSWORD"),
                        "connection_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "10")),
                        "autocommit": False,
                        "pool_name": "v4career_pool",
                        "pool_size": max(1, min(20, int(os.getenv("DB_POOL_SIZE", "10")))),
                        "pool_reset_session": True,
                    }
                    if os.getenv("DB_SSL_DISABLED", "false").lower() == "true":
                        kwargs["ssl_disabled"] = True
                    else:
                        kwargs["ssl_disabled"] = False
                    _mysql_pool = MySQLConnectionPool(**kwargs)
                    logger.info("Database connection pool initialized (engine=mysql, size=%s)", kwargs["pool_size"])
        return _mysql_pool.get_connection()

    required = ("NEON_HOST", "NEON_DB", "NEON_USER", "NEON_PASSWORD")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError("Missing PostgreSQL configuration: " + ", ".join(missing))
    # Reuse PostgreSQL connections instead of paying TCP/TLS/authentication
    # latency for every small API request. The lease preserves the existing
    # get_connection()/connection.close() interface used throughout the app.
    try:
        from psycopg_pool import ConnectionPool
    except ImportError as exc:
        raise RuntimeError(
            "PostgreSQL selected but psycopg_pool is not installed. "
            "Install dependencies from requirements.txt."
        ) from exc

    global _postgres_pool
    if _postgres_pool is None:
        with _postgres_pool_lock:
            if _postgres_pool is None:
                kwargs = {
                    "host": os.getenv("NEON_HOST"),
                    "port": int(os.getenv("NEON_PORT", "5432")),
                    "dbname": os.getenv("NEON_DB"),
                    "user": os.getenv("NEON_USER"),
                    "password": os.getenv("NEON_PASSWORD"),
                    "sslmode": os.getenv("NEON_SSLMODE", "require"),
                    "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "10")),
                }
                _postgres_pool = ConnectionPool(
                    conninfo="",
                    kwargs=kwargs,
                    min_size=max(1, int(os.getenv("PG_POOL_MIN_SIZE", "1"))),
                    max_size=max(2, int(os.getenv("PG_POOL_MAX_SIZE", "5"))),
                    timeout=float(os.getenv("PG_POOL_TIMEOUT", "8")),
                    max_lifetime=int(os.getenv("PG_POOL_MAX_LIFETIME", "1800")),
                    open=True,
                )
                logger.info(
                    "Database connection pool initialized (engine=postgres, min_size=%s, max_size=%s)",
                    _postgres_pool.min_size, _postgres_pool.max_size,
                )
    try:
        connection = _postgres_pool.getconn(timeout=float(os.getenv("PG_POOL_TIMEOUT", "8")))
    except Exception:
        logger.exception("Unable to acquire PostgreSQL connection from pool")
        raise
    return _PostgresConnectionLease(_postgres_pool, connection)


class _PostgresConnectionLease:
    """Connection proxy that returns its connection to the pool on close()."""
    __slots__ = ("_pool", "_connection", "_returned")

    def __init__(self, pool, connection):
        self._pool = pool
        self._connection = connection
        self._returned = False

    def __getattr__(self, name):
        return getattr(self._connection, name)

    def close(self):
        if not self._returned:
            self._returned = True
            self._pool.putconn(self._connection)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            try:
                self._connection.rollback()
            except Exception:
                logger.debug("Rollback failed while returning PostgreSQL connection", exc_info=True)
        self.close()
        return False


def column_names(cursor):
    """Return column names across psycopg and mysql-connector cursor metadata."""
    return [(column.name if hasattr(column, "name") else column[0]) for column in (cursor.description or [])]
