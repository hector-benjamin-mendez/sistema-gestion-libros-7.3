"""Acceso a datos de la entidad Editorial."""

from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload

from models import Editorial
from utils.db_errors import RegistroNoEncontrado, traducir_errores

_CAMPOS_EDITABLES = {"nombre", "direccion", "fecha_fundacion", "id_grupo_editorial"}


def crear(session: Session, *, nombre: str, id_grupo_editorial: int,
          direccion: str | None = None, fecha_fundacion = None) -> Editorial:
    editorial = Editorial(
        nombre=nombre, id_grupo_editorial=id_grupo_editorial,
        direccion=direccion, fecha_fundacion=fecha_fundacion,
    )
    with traducir_errores():
        session.add(editorial)
        session.flush()
    return editorial


def obtener_por_id(session: Session, editorial_id: int) -> Editorial | None:
    return session.get(Editorial, editorial_id)


def obtener_o_error(session: Session, editorial_id: int) -> Editorial:
    editorial = session.get(Editorial, editorial_id)
    if editorial is None:
        raise RegistroNoEncontrado(f"No existe la editorial con id {editorial_id}.")
    return editorial


def obtener_con_grupo(session: Session, editorial_id: int) -> Editorial | None:
    stmt = (
        select(Editorial)
        .where(Editorial.id == editorial_id)
        .options(joinedload(Editorial.grupo_editorial))
    )
    return session.scalars(stmt).first()


def listar_por_grupo(session: Session, id_grupo: int,
                     limite: int = 50, desplazamiento: int = 0) -> list[Editorial]:
    stmt = (
        select(Editorial)
        .where(Editorial.id_grupo_editorial == id_grupo)
        .order_by(Editorial.nombre)
        .limit(limite)
        .offset(desplazamiento)
    )
    return list(session.scalars(stmt))


def listar(session: Session, *, limite: int = 50, desplazamiento: int = 0) -> list[Editorial]:
    stmt = (
        select(Editorial)
        .options(joinedload(Editorial.grupo_editorial))
        .order_by(Editorial.nombre)
        .limit(limite)
        .offset(desplazamiento)
    )
    return list(session.scalars(stmt).unique())


def contar(session: Session, id_grupo: int | None = None) -> int:
    stmt = select(func.count()).select_from(Editorial)
    if id_grupo:
        stmt = stmt.where(Editorial.id_grupo_editorial == id_grupo)
    return session.scalar(stmt) or 0


def actualizar(session: Session, editorial_id: int, **campos) -> Editorial:
    editorial = obtener_o_error(session, editorial_id)
    for campo, valor in campos.items():
        if campo not in _CAMPOS_EDITABLES:
            raise ValueError(f"Campo no editable: {campo}")
        setattr(editorial, campo, valor)
    with traducir_errores():
        session.flush()
    return editorial


def eliminar(session: Session, editorial_id: int) -> None:
    editorial = obtener_o_error(session, editorial_id)
    with traducir_errores():
        session.delete(editorial)
        session.flush()
