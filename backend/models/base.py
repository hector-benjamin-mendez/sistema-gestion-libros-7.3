"""Clase base declarativa. Todos los modelos heredan de acá."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
