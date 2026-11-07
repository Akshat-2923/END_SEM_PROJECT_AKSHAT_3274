"""Database engine and session management."""

from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.database.config import get_database_url

_engines: dict[str, Engine] = {}
_session_factories: dict[str, sessionmaker[Session]] = {}


def get_engine(url: Optional[str] = None, echo: bool = False) -> Engine:
    """Retrieve or initialize a cached SQLAlchemy engine for the given URL.

    Args:
        url: Database connection URL (defaults to get_database_url()).
        echo: If True, logs SQL statements to stdout.

    Returns:
        SQLAlchemy Engine instance.
    """
    db_url = url or get_database_url()
    cache_key = f"{db_url}_{echo}"

    if cache_key not in _engines:
        connect_args = {}
        if db_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False

        engine = create_engine(
            db_url,
            echo=echo,
            connect_args=connect_args,
            pool_pre_ping=True,
        )
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
def get_db(url: Optional[str] = None) -> Generator[Session, None, None]:
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
