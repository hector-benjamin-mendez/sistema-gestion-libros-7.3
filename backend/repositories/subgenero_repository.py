"""Acceso a datos de la entidad Subgenero."""

from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload

from models import Subgenero
from utils.db_errors import RegistroNoEncontrado, traducir_errores


def crear(session: Session, *, nombre: str, id_genero: int) -> Subgenero:
    subgenero = Subgenero(nombre=nombre, id_genero=id_genero)
    with traducir_errores():
        session.add(subgenero)
        session.flush()
    return subgenero


def obtener_por_id(session: Session, subgenero_id: int) -> Subgenero | None:
    return session.get(Subgenero, subgenero_id)


def obtener_o_error(session: Session, subgenero_id: int) -> Subgenero:
    subgenero = session.get(Subgenero, subgenero_id)
    if subgenero is None:
        raise RegistroNoEncontrado(f"No existe el subgenero con id {subgenero_id}.")
    return subgenero


def obtener_con_genero(session: Session, subgenero_id: int) -> Subgenero | None:
    stmt = (
        select(Subgenero)
        .where(Subgenero.id == subgenero_id)
        .options(joinedload(Subgenero.genero))
    )
    return session.scalars(stmt).first()


def listar_por_genero(session: Session, id_genero: int,
                      limite: int = 50, desplazamiento: int = 0) -> list[Subgenero]:
    stmt = (
        select(Subgenero)
        .where(Subgenero.id_genero == id_genero)
        .order_by(Subgenero.nombre)
        .limit(limite)
        .offset(desplazamiento)
    )
    return list(session.scalars(stmt))


def listar(session: Session, *, limite: int = 50, desplazamiento: int = 0) -> list[Subgenero]:
    stmt = (
        select(Subgenero)
        .options(joinedload(Subgenero.genero))
        .order_by(Subgenero.nombre)
        .limit(limite)
        .offset(desplazamiento)
    )
    return list(session.scalars(stmt).unique())


def contar(session: Session, id_genero: int | None = None) -> int:
    stmt = select(func.count()).select_from(Subgenero)
    if id_genero:
        stmt = stmt.where(Subgenero.id_genero == id_genero)
    return session.scalar(stmt) or 0


def actualizar(session: Session, subgenero_id: int, **campos) -> Subgenero:
    subgenero = obtener_o_error(session, subgenero_id)
    for campo, valor in campos.items():
        if campo not in ("nombre", "id_genero"):
            raise ValueError(f"Campo no editable: {campo}")
        setattr(subgenero, campo, valor)
    with traducir_errores():
        session.flush()
    return subgenero


def eliminar(session: Session, subgenero_id: int) -> None:
    subgenero = obtener_o_error(session, subgenero_id)
    with traducir_errores():
        session.delete(subgenero)
        session.flush()
