"""Acceso a datos de la entidad Rango."""

from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload

from models import Rango
from utils.db_errors import RegistroNoEncontrado, traducir_errores

_CAMPOS_EDITABLES = {"nombre", "max_prestamos", "dias_prestamo"}


def crear(session: Session, *, nombre: str, max_prestamos: int,
          dias_prestamo: int) -> Rango:
    rango = Rango(nombre=nombre, max_prestamos=max_prestamos,
                  dias_prestamo=dias_prestamo)
    with traducir_errores():
        session.add(rango)
        session.flush()
    return rango


def obtener_por_id(session: Session, rango_id: int) -> Rango | None:
    return session.get(Rango, rango_id)


def obtener_o_error(session: Session, rango_id: int) -> Rango:
    rango = session.get(Rango, rango_id)
    if rango is None:
        raise RegistroNoEncontrado(f"No existe el rango con id {rango_id}.")
    return rango


def listar(session: Session, *, limite: int = 50, desplazamiento: int = 0) -> list[Rango]:
    stmt = (
        select(Rango)
        .options(selectinload(Rango.socios))
        .order_by(Rango.nombre)
        .limit(limite)
        .offset(desplazamiento)
    )
    return list(session.scalars(stmt).unique())


def contar(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Rango)) or 0


def actualizar(session: Session, rango_id: int, **campos) -> Rango:
    rango = obtener_o_error(session, rango_id)
    for campo, valor in campos.items():
        if campo not in _CAMPOS_EDITABLES:
            raise ValueError(f"Campo no editable: {campo}")
        setattr(rango, campo, valor)
    with traducir_errores():
        session.flush()
    return rango


def eliminar(session: Session, rango_id: int) -> None:
    rango = obtener_o_error(session, rango_id)
    with traducir_errores():
        session.delete(rango)
        session.flush()
