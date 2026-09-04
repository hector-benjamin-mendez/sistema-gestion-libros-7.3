"""Acceso a datos de la entidad Editorial.

Corrección 5: la editorial se escribe, no se elige de una lista. Eso
cambia tres cosas respecto de la versión anterior:

  · `obtener_o_crear`  : el alta la crea sola si no existe.
  · `id_grupo_editorial` pasa a ser opcional: nadie va a saber a qué
    grupo pertenece "Ediciones del Barrio" mientras carga un libro.
  · `sugerir`          : devuelve nombres parecidos a lo que se está
    tipeando, para que el input pueda tener autocompletado y no se
    generen "Minotauro" y "Minotauro SA" como dos editoriales.
"""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from models import Editorial
from utils.db_errors import RegistroNoEncontrado, traducir_errores
from utils.texto import normalizar, normalizar_obligatorio

_CAMPOS_EDITABLES = {"nombre", "direccion", "fecha_fundacion", "id_grupo_editorial"}


def crear(session: Session, *, nombre: str, id_grupo_editorial: int | None = None,
          direccion: str | None = None,
          fecha_fundacion: date | None = None) -> Editorial:
    editorial = Editorial(
        nombre=normalizar_obligatorio(nombre, "editorial"),
        id_grupo_editorial=id_grupo_editorial,
        direccion=normalizar(direccion),
        fecha_fundacion=fecha_fundacion,
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


def obtener_por_nombre(session: Session, nombre: str) -> Editorial | None:
    limpio = normalizar_obligatorio(nombre, "editorial")
    return session.scalars(select(Editorial).where(Editorial.nombre == limpio)).first()


def obtener_o_crear(session: Session, nombre: str) -> Editorial:
    """Lo que usa el alta de material cuando la editorial llega tipeada."""
    existente = obtener_por_nombre(session, nombre)
    return existente if existente is not None else crear(session, nombre=nombre)


def obtener_con_grupo(session: Session, editorial_id: int) -> Editorial | None:
    stmt = (
        select(Editorial)
        .where(Editorial.id == editorial_id)
        .options(joinedload(Editorial.grupo_editorial))
    )
    return session.scalars(stmt).first()


def sugerir(session: Session, texto: str, limite: int = 10) -> list[Editorial]:
    """Para el autocompletado del input de texto.

    Ordena por nombre y filtra por coincidencia parcial. Con 10
    resultados alcanza: es una ayuda de tipeo, no un listado.
    """
    limpio = normalizar(texto)
    if limpio is None:
        return []
    stmt = (
        select(Editorial)
        .where(Editorial.nombre.like(f"%{limpio}%"))
        .order_by(Editorial.nombre)
        .limit(limite)
    )
    return list(session.scalars(stmt))


def listar(session: Session, *, texto: str | None = None, id_grupo: int | None = None,
           limite: int = 50, desplazamiento: int = 0) -> list[Editorial]:
    stmt = select(Editorial).options(joinedload(Editorial.grupo_editorial))
    if texto:
        stmt = stmt.where(Editorial.nombre.like(f"%{texto.strip()}%"))
    if id_grupo:
        stmt = stmt.where(Editorial.id_grupo_editorial == id_grupo)
    stmt = stmt.order_by(Editorial.nombre).limit(limite).offset(desplazamiento)
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
            raise ValueError(f"Campo no editable en Editorial: {campo}")
        if campo == "nombre":
            valor = normalizar_obligatorio(valor, "editorial")
        if campo == "direccion":
            valor = normalizar(valor)
        setattr(editorial, campo, valor)
    with traducir_errores():
        session.flush()
    return editorial


def eliminar(session: Session, editorial_id: int) -> None:
    """Falla con ViolacionDeIntegridad si tiene copias cargadas."""
    editorial = obtener_o_error(session, editorial_id)
    with traducir_errores():
        session.delete(editorial)
        session.flush()
