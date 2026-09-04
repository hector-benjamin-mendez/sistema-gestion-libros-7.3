"""Acceso a datos de la entidad Autor.

Corrección 5: los autores se escriben, no se eligen de una lista.

`obtener_o_crear_por_texto` recibe lo que el bibliotecario tipeó
("Stephen King", "King, Stephen", "Ursula K. Le Guin") y devuelve la
fila correspondiente, creándola si hace falta. La clave única
(apellido, nombre) es la que impide que el mismo autor entre dos veces.
"""

from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from models import Autor
from utils.db_errors import RegistroNoEncontrado, traducir_errores
from utils.texto import (
    normalizar,
    normalizar_obligatorio,
    separar_lista,
    separar_nombre_autor,
)

_CAMPOS_EDITABLES = {
    "nombre", "apellido", "fecha_nacimiento",
    "fecha_fallecimiento", "nacionalidad",
}


def crear(session: Session, *, apellido: str, nombre: str = "",
          fecha_nacimiento: date | None = None,
          fecha_fallecimiento: date | None = None,
          nacionalidad: str | None = None) -> Autor:
    autor = Autor(
        apellido=normalizar_obligatorio(apellido, "apellido del autor"),
        nombre=normalizar(nombre) or "",
        fecha_nacimiento=fecha_nacimiento,
        fecha_fallecimiento=fecha_fallecimiento,
        nacionalidad=normalizar(nacionalidad),
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


def obtener_por_nombre_completo(session: Session, texto: str) -> Autor | None:
    nombre, apellido = separar_nombre_autor(texto)
    stmt = select(Autor).where(Autor.apellido == apellido, Autor.nombre == nombre)
    return session.scalars(stmt).first()


def obtener_o_crear_por_texto(session: Session, texto: str) -> Autor:
    """Recibe el texto tal cual salió del input y devuelve el autor."""
    existente = obtener_por_nombre_completo(session, texto)
    if existente is not None:
        return existente
    nombre, apellido = separar_nombre_autor(texto)
    return crear(session, apellido=apellido, nombre=nombre)


def obtener_o_crear_varios(session: Session, texto: str | None) -> list[Autor]:
    """Igual que la anterior pero para el campo entero del formulario.

    El input trae varios autores separados por punto y coma:
        "Sagan, Carl; Druyan, Ann"
    Se corta por ';' y no por ',' para no romper la forma
    "Apellido, Nombre", que es como se anota en las fichas.
    """
    return [obtener_o_crear_por_texto(session, parte)
            for parte in separar_lista(texto)]


def obtener_con_titulos(session: Session, autor_id: int) -> Autor | None:
    stmt = (
        select(Autor)
        .where(Autor.id == autor_id)
        .options(selectinload(Autor.titulos))
    )
    return session.scalars(stmt).unique().first()


def sugerir(session: Session, texto: str, limite: int = 10) -> list[Autor]:
    """Autocompletado del input de autores."""
    limpio = normalizar(texto)
    if limpio is None:
        return []
    patron = f"%{limpio}%"
    stmt = (
        select(Autor)
        .where(or_(Autor.apellido.like(patron), Autor.nombre.like(patron)))
        .order_by(Autor.apellido, Autor.nombre)
        .limit(limite)
    )
    return list(session.scalars(stmt))


def listar(session: Session, *, texto: str | None = None, solo_vivos: bool = False,
           limite: int = 50, desplazamiento: int = 0) -> list[Autor]:
    stmt = select(Autor)
    if texto:
        patron = f"%{texto.strip()}%"
        stmt = stmt.where(or_(Autor.apellido.like(patron), Autor.nombre.like(patron)))
    if solo_vivos:
        stmt = stmt.where(Autor.fecha_fallecimiento.is_(None))
    stmt = stmt.order_by(Autor.apellido, Autor.nombre).limit(limite).offset(desplazamiento)
    return list(session.scalars(stmt))


def contar(session: Session, texto: str | None = None) -> int:
    stmt = select(func.count()).select_from(Autor)
    if texto:
        patron = f"%{texto.strip()}%"
        stmt = stmt.where(or_(Autor.apellido.like(patron), Autor.nombre.like(patron)))
    return session.scalar(stmt) or 0


def actualizar(session: Session, autor_id: int, **campos) -> Autor:
    autor = obtener_o_error(session, autor_id)
    for campo, valor in campos.items():
        if campo not in _CAMPOS_EDITABLES:
            raise ValueError(f"Campo no editable en Autor: {campo}")
        if campo == "apellido":
            valor = normalizar_obligatorio(valor, "apellido del autor")
        if campo == "nombre":
            valor = normalizar(valor) or ""
        if campo == "nacionalidad":
            valor = normalizar(valor)
        setattr(autor, campo, valor)
    with traducir_errores():
        session.flush()
    return autor


def eliminar(session: Session, autor_id: int) -> None:
    """Borra el autor y sus filas de titulo_autor (ON DELETE CASCADE).
    Los títulos quedan, sin ese autor."""
    autor = obtener_o_error(session, autor_id)
    with traducir_errores():
        session.delete(autor)
        session.flush()
