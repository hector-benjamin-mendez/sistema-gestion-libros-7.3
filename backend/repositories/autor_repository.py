"""Acceso a datos de la entidad Autor."""

from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session, selectinload

from models import Autor
from utils.db_errors import RegistroNoEncontrado, traducir_errores

_CAMPOS_EDITABLES = {
    "nombre", "apellido", "fecha_nacimiento",
    "fecha_fallecimiento", "nacionalidad",
}


def crear(session: Session, *, nombre: str, apellido: str,
          fecha_nacimiento, nacionalidad: str,
          fecha_fallecimiento=None) -> Autor:
    autor = Autor(
        nombre=nombre, apellido=apellido,
        fecha_nacimiento=fecha_nacimiento, nacionalidad=nacionalidad,
        fecha_fallecimiento=fecha_fallecimiento,
    )
    with traducir_errores():
        session.add(autor)
        session.flush()
    return autor


def obtener_por_id(session: Session, autor_id: int) -> Autor | None:
    return session.get(Autor, autor_id)


def obtener_o_error(session: Session, autor_id: int) -> Autor:
    autor = session.get(Autor, autor_id)
    if autor is None:
        raise RegistroNoEncontrado(f"No existe el autor con id {autor_id}.")
    return autor


def obtener_con_libros(session: Session, autor_id: int) -> Autor | None:
    stmt = (
        select(Autor)
        .where(Autor.id == autor_id)
        .options(selectinload(Autor.libros))
    )
    return session.scalars(stmt).unique().first()


def buscar(session: Session, *, texto: str | None = None,
           solo_vivos: bool = False,
           limite: int = 50, desplazamiento: int = 0) -> list[Autor]:
    stmt = select(Autor)
    if texto:
        patron = f"%{texto}%"
        stmt = stmt.where(
            or_(Autor.apellido.like(patron), Autor.nombre.like(patron))
        )
    if solo_vivos:
        stmt = stmt.where(Autor.fecha_fallecimiento.is_(None))
    stmt = stmt.order_by(Autor.apellido, Autor.nombre).limit(limite).offset(desplazamiento)
    return list(session.scalars(stmt))


def listar(session: Session, *, limite: int = 50, desplazamiento: int = 0) -> list[Autor]:
    stmt = (
        select(Autor)
        .order_by(Autor.apellido, Autor.nombre)
        .limit(limite)
        .offset(desplazamiento)
    )
    return list(session.scalars(stmt))


def contar(session: Session, texto: str | None = None) -> int:
    stmt = select(func.count()).select_from(Autor)
    if texto:
        patron = f"%{texto}%"
        stmt = stmt.where(
            or_(Autor.apellido.like(patron), Autor.nombre.like(patron))
        )
    return session.scalar(stmt) or 0


def actualizar(session: Session, autor_id: int, **campos) -> Autor:
    autor = obtener_o_error(session, autor_id)
    for campo, valor in campos.items():
        if campo not in _CAMPOS_EDITABLES:
            raise ValueError(f"Campo no editable: {campo}")
        setattr(autor, campo, valor)
    with traducir_errores():
        session.flush()
    return autor


def eliminar(session: Session, autor_id: int) -> None:
    autor = obtener_o_error(session, autor_id)
    with traducir_errores():
        session.delete(autor)
        session.flush()
