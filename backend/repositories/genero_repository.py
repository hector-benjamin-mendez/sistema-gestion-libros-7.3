"""Acceso a datos de la entidad Genero."""

from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload

from models import Genero
from utils.db_errors import RegistroNoEncontrado, traducir_errores


def crear(session: Session, *, nombre: str) -> Genero:
    genero = Genero(nombre=nombre)
    with traducir_errores():
        session.add(genero)
        session.flush()
    return genero


def obtener_por_id(session: Session, genero_id: int) -> Genero | None:
    return session.get(Genero, genero_id)


def obtener_o_error(session: Session, genero_id: int) -> Genero:
    genero = session.get(Genero, genero_id)
    if genero is None:
        raise RegistroNoEncontrado(f"No existe el genero con id {genero_id}.")
    return genero


def listar(session: Session, *, limite: int = 50, desplazamiento: int = 0) -> list[Genero]:
    stmt = (
        select(Genero)
        .options(selectinload(Genero.subgeneros))
        .order_by(Genero.nombre)
        .limit(limite)
        .offset(desplazamiento)
    )
    return list(session.scalars(stmt).unique())


def contar(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Genero)) or 0


def actualizar(session: Session, genero_id: int, *, nombre: str) -> Genero:
    genero = obtener_o_error(session, genero_id)
    genero.nombre = nombre
    with traducir_errores():
        session.flush()
    return genero


def eliminar(session: Session, genero_id: int) -> None:
    genero = obtener_o_error(session, genero_id)
    with traducir_errores():
        session.delete(genero)
        session.flush()
