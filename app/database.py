"""Database setup providing engine, session maker, and DB dependency."""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from app.config import DATABASE_URL

# Enable check_same_thread=False for SQLite to support background task access
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base declarative class for SQLAlchemy models."""
    pass


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for request lifecycle and close on completion."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
