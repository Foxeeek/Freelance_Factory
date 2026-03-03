from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from freelance_ai.app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


@contextmanager
def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    # Import models for metadata registration.
    from freelance_ai.core.models import OrderDB  # noqa: F401

    Base.metadata.create_all(bind=engine)
