"""Conexão com o banco (PostgreSQL em produção, SQLite em desenvolvimento) e a sessão por requisição."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base de todos os modelos SQLAlchemy."""

    pass


def get_db():
    """Abre uma sessão do banco por requisição e a fecha no fim, mesmo com erro."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
