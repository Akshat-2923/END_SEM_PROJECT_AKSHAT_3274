"""Database engine and session management.

Provides connection pooling, SSL/TLS negotiation for Azure Database for PostgreSQL
Flexible Server, transactional session management, and connectivity diagnostics.
"""

from contextlib import contextmanager
from typing import Any, Generator, Optional, Union

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL
from sqlalchemy.orm import Session, sessionmaker

from src.database.config import (
    get_database_config,
    get_database_url,
    parse_database_url,
)

_engines: dict[str, Engine] = {}
_session_factories: dict[str, sessionmaker[Session]] = {}


def get_engine(
    url: Optional[Union[str, URL]] = None,
    echo: Optional[bool] = None,
    ssl_mode: Optional[str] = None,
    pool_size: Optional[int] = None,
    max_overflow: Optional[int] = None,
    pool_timeout: Optional[int] = None,
    pool_recycle: Optional[int] = None,
    ssl_root_cert: Optional[str] = None,
) -> Engine:
    """Retrieve or initialize a cached SQLAlchemy engine with SSL and connection pooling.

    Args:
        url: Database connection URL (defaults to get_database_url()).
        echo: If True, logs SQL statements to stdout (defaults to DB_ECHO or False).
        ssl_mode: PostgreSQL SSL mode (e.g. 'require', 'prefer', 'verify-ca').
        pool_size: Permanent connection pool capacity.
        max_overflow: Maximum temporary overflow connections.
        pool_timeout: Seconds to wait before timing out connection requests.
        pool_recycle: Seconds after which connections are recycled.
        ssl_root_cert: Optional path to Root CA certificate bundle.

    Returns:
        SQLAlchemy Engine instance.
    """
    db_config = get_database_config(url=url)
    db_url_str = str(url or db_config.url)
    parsed = parse_database_url(db_url_str)

    eff_echo = echo if echo is not None else db_config.echo
    eff_ssl_mode = ssl_mode if ssl_mode is not None else db_config.ssl_mode
    eff_ssl_root_cert = ssl_root_cert if ssl_root_cert is not None else db_config.ssl_root_cert
    eff_pool_size = pool_size if pool_size is not None else db_config.pool_size
    eff_max_overflow = max_overflow if max_overflow is not None else db_config.max_overflow
    eff_pool_timeout = pool_timeout if pool_timeout is not None else db_config.pool_timeout
    eff_pool_recycle = pool_recycle if pool_recycle is not None else db_config.pool_recycle

    cache_key = f"{db_url_str}_{eff_echo}_{eff_ssl_mode}_{eff_pool_size}_{eff_max_overflow}"

    if cache_key not in _engines:
        connect_args: dict[str, Any] = {}
        if parsed.drivername.startswith("sqlite"):
            connect_args["check_same_thread"] = False
            engine = create_engine(
                db_url_str,
                echo=eff_echo,
                connect_args=connect_args,
            )
        else:
            if parsed.drivername.startswith("postgresql"):
                if eff_ssl_mode:
                    connect_args["sslmode"] = eff_ssl_mode
                if eff_ssl_root_cert:
                    connect_args["sslrootcert"] = eff_ssl_root_cert

            engine = create_engine(
                db_url_str,
                echo=eff_echo,
                connect_args=connect_args,
                pool_size=eff_pool_size,
                max_overflow=eff_max_overflow,
                pool_timeout=eff_pool_timeout,
                pool_recycle=eff_pool_recycle,
                pool_pre_ping=True,
            )
        setattr(engine, "_connect_args", dict(connect_args))
        _engines[cache_key] = engine

    return _engines[cache_key]


def get_session_factory(engine: Optional[Engine] = None) -> sessionmaker[Session]:
    """Retrieve or initialize a sessionmaker for the given engine."""
    eng = engine or get_engine()
    eng_id = str(eng.url)

    if eng_id not in _session_factories:
        _session_factories[eng_id] = sessionmaker(
            bind=eng,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

    return _session_factories[eng_id]


@contextmanager
def get_db(url: Optional[Union[str, URL]] = None) -> Generator[Session, None, None]:
    """Context manager for transactional database sessions with automatic commit/rollback.

    Yields:
        Active SQLAlchemy Session.
    """
    engine = get_engine(url)
    session_factory = get_session_factory(engine)
    session: Session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _extract_pool_metric(pool: Any, attr_name: str) -> Optional[int]:
    """Safely extract connection pool metric handling both methods and attributes."""
    if hasattr(pool, attr_name):
        val = getattr(pool, attr_name)
        try:
            return val() if callable(val) else int(val)
        except Exception:
            return None
    return None


def check_database_connectivity(engine: Optional[Engine] = None) -> dict[str, Any]:
    """Inspect database connectivity, PostGIS availability, SSL status, and pool metrics.

    Ensures that all passwords and sensitive credentials are completely redacted.

    Args:
        engine: Optional Engine to test (defaults to default get_engine()).

    Returns:
        Dictionary containing sanitized diagnostic and operational metrics.
    """
    eng = engine or get_engine()
    parsed = eng.url
    sanitized_url = parsed.render_as_string(hide_password=True)
    dialect = parsed.get_backend_name()
    driver = parsed.get_driver_name()

    pool_metrics = None
    if hasattr(eng, "pool"):
        pool = eng.pool
        pool_metrics = {
            "type": type(pool).__name__,
            "size": _extract_pool_metric(pool, "size"),
            "checked_in": _extract_pool_metric(pool, "checkedin"),
            "checked_out": _extract_pool_metric(pool, "checkedout"),
            "overflow": _extract_pool_metric(pool, "overflow"),
        }

    configured_ssl_mode = getattr(eng, "_connect_args", {}).get("sslmode")
    if not configured_ssl_mode and parsed.query.get("sslmode"):
        configured_ssl_mode = str(parsed.query.get("sslmode"))

    result: dict[str, Any] = {
        "status": "disconnected",
        "connected": False,
        "dialect": dialect,
        "driver": driver,
        "host": parsed.host,
        "port": parsed.port,
        "database_name": parsed.database,
        "username": parsed.username,
        "sanitized_url": sanitized_url,
        "ssl_mode": configured_ssl_mode,
        "ssl_active": False,
        "server_version": None,
        "postgis_version": None,
        "pool": pool_metrics,
        "error": None,
    }

    try:
        with eng.connect() as conn:
            # 1. Connectivity ping
            conn.execute(text("SELECT 1;"))
            result["connected"] = True
            result["status"] = "connected"

            # 2. Database engine version
            try:
                version_str = conn.execute(text("SELECT version();")).scalar()
                result["server_version"] = str(version_str) if version_str else None
            except Exception:
                pass

            # 3. PostGIS extension version
            try:
                postgis_str = conn.execute(text("SELECT PostGIS_Full_Version();")).scalar()
                result["postgis_version"] = str(postgis_str) if postgis_str else None
            except Exception:
                try:
                    postgis_str = conn.execute(text("SELECT PostGIS_Version();")).scalar()
                    result["postgis_version"] = str(postgis_str) if postgis_str else None
                except Exception:
                    result["postgis_version"] = None

            # 4. SSL session verification
            try:
                ssl_active = conn.execute(
                    text("SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid();")
                ).scalar()
                result["ssl_active"] = bool(ssl_active)
            except Exception:
                try:
                    fairy = conn.connection
                    raw_conn = getattr(fairy, "driver_connection", None) or getattr(fairy, "connection", None)
                    if raw_conn and hasattr(raw_conn, "ssl_in_use"):
                        result["ssl_active"] = bool(raw_conn.ssl_in_use)
                except Exception:
                    pass

    except Exception as exc:
        result["status"] = "disconnected"
        result["connected"] = False
        raw_err = str(exc)
        if parsed.password:
            raw_err = raw_err.replace(parsed.password, "***")
        result["error"] = raw_err

    return result

