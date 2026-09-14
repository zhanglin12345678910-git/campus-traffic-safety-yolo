from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import Settings


class Base(DeclarativeBase):
    pass


class Database:
    def __init__(self, settings: Settings):
        connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
        self.engine = create_engine(
            settings.database_url,
            echo=settings.sql_echo,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        self.session_factory = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)

    def create_all(self) -> None:
        from app import models  # noqa: F401

        Base.metadata.create_all(self.engine)

    def session(self) -> Session:
        return self.session_factory()

    def dependency(self) -> Generator[Session, None, None]:
        db = self.session()
        try:
            yield db
        finally:
            db.close()

