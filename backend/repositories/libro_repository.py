"""Acceso a datos de la entidad Libro."""

from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload, selectinload

from models import Libro, Autor
from utils.db_errors import RegistroNoEncontrado, traducir_errores

_CAMPOS_EDITABLES = {
    "titulo", "isbn", "id_subgenero", "id_editorial",
    "fecha_publicacion", "idioma", "numero_edicion",
}


def crear(session: Session, *, titulo, id_subgenero, id_editorial,
          fecha_publicacion, idioma, numero_edicion,
          isbn=None, autores_ids=None) -> Libro:
    libro = Libro(
        titulo=titulo,
        isbn=isbn,
        id_subgenero=id_subgenero,
        id_editorial=id_editorial,
        fecha_publicacion=fecha_publicacion,
        idioma=idioma,
        numero_edicion=numero_edicion,
    )
    if autores_ids:
        libro.autores = _autores_por_ids(session, autores_ids)
    with traducir_errores():
        session.add(libro)
        session.flush()
    return libro


def obtener_por_id(session: Session, libro_id: int) -> Libro | None:
    return session.get(Libro, libro_id)


def obtener_o_error(session: Session, libro_id: int) -> Libro:
    libro = session.get(Libro, libro_id)
    if libro is None:
        raise RegistroNoEncontrado(f"No existe el libro con id {libro_id}.")
    return libro


def obtener_completo(session: Session, libro_id: int) -> Libro | None:
    """Trae el libro con autores, subgenero, editorial y ejemplares ya cargados."""
    stmt = (
        select(Libro)
        .where(Libro.id == libro_id)
        .options(
            selectinload(Libro.autores),
            selectinload(Libro.ejemplares),
            joinedload(Libro.subgenero),
            joinedload(Libro.editorial),
        )
    )
    return session.scalars(stmt).unique().first()


def obtener_por_isbn(session: Session, isbn: str) -> Libro | None:
    return session.scalars(select(Libro).where(Libro.isbn == isbn)).first()


def listar(session: Session, *, titulo=None, id_subgenero=None,
           id_editorial=None, id_autor=None,
           limite: int = 50, desplazamiento: int = 0) -> list[Libro]:
    stmt = select(Libro).options(
        selectinload(Libro.autores),
        joinedload(Libro.subgenero),
        joinedload(Libro.editorial),
    )
    if titulo:
        stmt = stmt.where(Libro.titulo.like(f"%{titulo}%"))
    if id_subgenero:
        stmt = stmt.where(Libro.id_subgenero == id_subgenero)
    if id_editorial:
        stmt = stmt.where(Libro.id_editorial == id_editorial)
    if id_autor:
        stmt = stmt.join(Libro.autores).where(Autor.id == id_autor)
    stmt = stmt.order_by(Libro.titulo).limit(limite).offset(desplazamiento)
    return list(session.scalars(stmt).unique())


def contar(session: Session, *, titulo=None, id_subgenero=None) -> int:
    stmt = select(func.count()).select_from(Libro)
    if titulo:
        stmt = stmt.where(Libro.titulo.like(f"%{titulo}%"))
    if id_subgenero:
        stmt = stmt.where(Libro.id_subgenero == id_subgenero)
    return session.scalar(stmt) or 0


def actualizar(session: Session, libro_id: int, **campos) -> Libro:
    libro = obtener_o_error(session, libro_id)
    for campo, valor in campos.items():
        if campo not in _CAMPOS_EDITABLES:
            raise ValueError(f"Campo no editable en Libro: {campo}")
        setattr(libro, campo, valor)
    with traducir_errores():
        session.flush()
    return libro


def eliminar(session: Session, libro_id: int) -> None:
    libro = obtener_o_error(session, libro_id)
    with traducir_errores():
        session.delete(libro)
        session.flush()


def asignar_autores(session: Session, libro_id: int, autores_ids: list[int]) -> Libro:
    libro = obtener_o_error(session, libro_id)
    libro.autores = _autores_por_ids(session, autores_ids)
    with traducir_errores():
        session.flush()
    return libro


def _autores_por_ids(session: Session, autores_ids: list[int]) -> list[Autor]:
    autores = list(session.scalars(select(Autor).where(Autor.id.in_(autores_ids))))
    faltantes = set(autores_ids) - {a.id for a in autores}
    if faltantes:
        raise RegistroNoEncontrado(f"No existen los autores: {sorted(faltantes)}")
    return autores


# NOTA: aca habia un obtener_todos() duplicado que hacia lo mismo que listar()
# pero peor: sin eager loading (N+1: 24 consultas para 21 libros contra 2),
# sin limite (traia la tabla entera) y con la API vieja db.query() de
# SQLAlchemy 1.x mezclada con el estilo 2.0 del resto del archivo.
# Se elimino. Las rutas usan listar().