"""Acceso a datos de la entidad GrupoEditorial."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from models import GrupoEditorial
from utils.db_errors import RegistroNoEncontrado, traducir_errores
from utils.texto import normalizar_obligatorio


def crear(session: Session, *, nombre: str) -> GrupoEditorial:
    grupo = GrupoEditorial(nombre=normalizar_obligatorio(nombre, "grupo editorial"))
    with traducir_errores():
        session.add(grupo)
        session.flush()
    return grupo


def obtener_por_id(session: Session, grupo_id: int) -> GrupoEditorial | None:
    return session.get(GrupoEditorial, grupo_id)


def obtener_o_error(session: Session, grupo_id: int) -> GrupoEditorial:
    grupo = session.get(GrupoEditorial, grupo_id)
    if grupo is None:
        raise RegistroNoEncontrado(f"No existe el grupo editorial con id {grupo_id}.")
    return grupo


def obtener_por_nombre(session: Session, nombre: str) -> GrupoEditorial | None:
    limpio = normalizar_obligatorio(nombre, "grupo editorial")
    stmt = select(GrupoEditorial).where(GrupoEditorial.nombre == limpio)
    return session.scalars(stmt).first()


def obtener_o_crear(session: Session, nombre: str) -> GrupoEditorial:
    existente = obtener_por_nombre(session, nombre)
    return existente if existente is not None else crear(session, nombre=nombre)


def listar(session: Session, *, limite: int = 50,
           desplazamiento: int = 0) -> list[GrupoEditorial]:
    stmt = (
        select(GrupoEditorial)
        .options(selectinload(GrupoEditorial.editoriales))
        .order_by(GrupoEditorial.nombre)
        .limit(limite)
        .offset(desplazamiento)
    )
    return list(session.scalars(stmt).unique())


def contar(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(GrupoEditorial)) or 0


def actualizar(session: Session, grupo_id: int, *, nombre: str) -> GrupoEditorial:
    grupo = obtener_o_error(session, grupo_id)
    grupo.nombre = normalizar_obligatorio(nombre, "grupo editorial")
    with traducir_errores():
        session.flush()
    return grupo


def eliminar(session: Session, grupo_id: int) -> None:
    """Las editoriales del grupo NO se borran: quedan con grupo en NULL
    (ON DELETE SET NULL en el schema)."""
    grupo = obtener_o_error(session, grupo_id)
    with traducir_errores():
        session.delete(grupo)
        session.flush()
