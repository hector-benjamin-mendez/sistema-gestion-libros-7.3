"""Acceso a datos de la entidad Idioma.

Tabla nueva: sale del "IdIdioma" de la corrección 2. Antes el idioma era
texto libre dentro de libro y convivían 'Espanol', 'español' y 'ES'.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import Idioma
from utils.db_errors import RegistroNoEncontrado, traducir_errores
from utils.texto import normalizar_obligatorio


def crear(session: Session, *, nombre: str) -> Idioma:
    idioma = Idioma(nombre=normalizar_obligatorio(nombre, "idioma"))
    with traducir_errores():
        session.add(idioma)
        session.flush()
    return idioma


def obtener_por_id(session: Session, idioma_id: int) -> Idioma | None:
    return session.get(Idioma, idioma_id)


def obtener_o_error(session: Session, idioma_id: int) -> Idioma:
    idioma = session.get(Idioma, idioma_id)
    if idioma is None:
        raise RegistroNoEncontrado(f"No existe el idioma con id {idioma_id}.")
    return idioma


def obtener_por_nombre(session: Session, nombre: str) -> Idioma | None:
    limpio = normalizar_obligatorio(nombre, "idioma")
    return session.scalars(select(Idioma).where(Idioma.nombre == limpio)).first()


def obtener_o_crear(session: Session, nombre: str) -> Idioma:
    existente = obtener_por_nombre(session, nombre)
    return existente if existente is not None else crear(session, nombre=nombre)


def listar(session: Session, *, limite: int = 50, desplazamiento: int = 0) -> list[Idioma]:
    stmt = select(Idioma).order_by(Idioma.nombre).limit(limite).offset(desplazamiento)
    return list(session.scalars(stmt))


def contar(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Idioma)) or 0


def actualizar(session: Session, idioma_id: int, *, nombre: str) -> Idioma:
    idioma = obtener_o_error(session, idioma_id)
    idioma.nombre = normalizar_obligatorio(nombre, "idioma")
    with traducir_errores():
        session.flush()
    return idioma


def eliminar(session: Session, idioma_id: int) -> None:
    idioma = obtener_o_error(session, idioma_id)
    with traducir_errores():
        session.delete(idioma)
        session.flush()
