"""Acceso a datos de la entidad Rango.

Define, por categoría de socio, cuántos préstamos puede tener a la vez y
por cuántos días. La capa de servicios lee estos dos números; acá no se
aplica ninguna regla.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from models import Rango
from utils.db_errors import RegistroNoEncontrado, traducir_errores
from utils.texto import normalizar_obligatorio

_CAMPOS_EDITABLES = {"nombre", "max_prestamos", "dias_prestamo"}


def crear(session: Session, *, nombre: str, max_prestamos: int,
          dias_prestamo: int) -> Rango:
    if max_prestamos < 1 or dias_prestamo < 1:
        raise ValueError("max_prestamos y dias_prestamo tienen que ser mayores a 0.")
    rango = Rango(
        nombre=normalizar_obligatorio(nombre, "rango"),
        max_prestamos=max_prestamos,
        dias_prestamo=dias_prestamo,
    )
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


def obtener_por_nombre(session: Session, nombre: str) -> Rango | None:
    limpio = normalizar_obligatorio(nombre, "rango")
    return session.scalars(select(Rango).where(Rango.nombre == limpio)).first()


def listar(session: Session, *, limite: int = 50,
           desplazamiento: int = 0) -> list[Rango]:
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
            raise ValueError(f"Campo no editable en Rango: {campo}")
        if campo == "nombre":
            valor = normalizar_obligatorio(valor, "rango")
        setattr(rango, campo, valor)
    with traducir_errores():
        session.flush()
    return rango


def eliminar(session: Session, rango_id: int) -> None:
    """Falla con ViolacionDeIntegridad si hay socios en ese rango."""
    rango = obtener_o_error(session, rango_id)
    with traducir_errores():
        session.delete(rango)
        session.flush()
