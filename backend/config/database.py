"""Engine y sesiones de SQLAlchemy."""

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.settings import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    echo=False,          # True para ver el SQL generado (útil al depurar)
    pool_pre_ping=True,  # descarta conexiones muertas antes de usarlas
    pool_recycle=3600,   # renueva conexiones cada hora
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def get_session():
    """Para que Héctor la use con Depends() en FastAPI."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope():
    """Para scripts y pruebas. Commit automático, rollback si algo falla."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
