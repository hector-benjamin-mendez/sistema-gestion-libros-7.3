"""Acceso a datos de la entidad Genero.

El género se carga escribiéndolo (corrección 4): por eso además del CRUD
normal está `obtener_o_crear`, que es lo que usa el alta de material.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from models import Genero
from utils.db_errors import RegistroNoEncontrado, traducir_errores
from utils.texto import normalizar_obligatorio


def crear(session: Session, *, nombre: str) -> Genero:
    genero = Genero(nombre=normalizar_obligatorio(nombre, "género"))
    with traducir_errores():
        session.add(genero)
        session.flush()
    return genero


def obtener_por_id(session: Session, genero_id: int) -> Genero | None:
    return session.get(Genero, genero_id)


def obtener_o_error(session: Session, genero_id: int) -> Genero:
    genero = session.get(Genero, genero_id)
    if genero is None:
        raise RegistroNoEncontrado(f"No existe el género con id {genero_id}.")
    return genero


def obtener_por_nombre(session: Session, nombre: str) -> Genero | None:
    """Búsqueda exacta. La collation utf8mb4_unicode_ci hace que
    'terror', 'Terror' y 'TERROR' encuentren la misma fila."""
    limpio = normalizar_obligatorio(nombre, "género")
    return session.scalars(select(Genero).where(Genero.nombre == limpio)).first()


def obtener_o_crear(session: Session, nombre: str) -> Genero:
    """Devuelve el género con ese nombre; si no existe, lo crea.

    Es la función que hace posible que el HTML mande texto libre sin
    llenar la tabla de duplicados.
    """
    existente = obtener_por_nombre(session, nombre)
    return existente if existente is not None else crear(session, nombre=nombre)


def listar(session: Session, *, texto: str | None = None,
           limite: int = 50, desplazamiento: int = 0) -> list[Genero]:
    stmt = select(Genero).options(selectinload(Genero.titulos))
    if texto:
        stmt = stmt.where(Genero.nombre.like(f"%{texto.strip()}%"))
    stmt = stmt.order_by(Genero.nombre).limit(limite).offset(desplazamiento)
    return list(session.scalars(stmt).unique())


def contar(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Genero)) or 0


def actualizar(session: Session, genero_id: int, *, nombre: str) -> Genero:
    genero = obtener_o_error(session, genero_id)
    genero.nombre = normalizar_obligatorio(nombre, "género")
    with traducir_errores():
        session.flush()
    return genero


def eliminar(session: Session, genero_id: int) -> None:
    """Falla con ViolacionDeIntegridad si el género tiene títulos."""
    genero = obtener_o_error(session, genero_id)
    with traducir_errores():
        session.delete(genero)
        session.flush()
