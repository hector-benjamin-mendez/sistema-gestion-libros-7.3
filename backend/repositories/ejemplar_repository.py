"""Acceso a datos de la entidad Ejemplar."""

from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload

from models import Ejemplar
from utils.db_errors import RegistroNoEncontrado, traducir_errores

# Lista cerrada de estados. El PDF no la define: es la convencion del equipo.
ESTADOS_VALIDOS = ("disponible", "prestado", "en_reparacion", "baja")

_CAMPOS_EDITABLES = {"id_libro", "codigo_inventario", "estado", "fecha_alta"}


def crear(session: Session, *, id_libro, codigo_inventario,
          fecha_alta, estado="disponible") -> Ejemplar:
    _validar_estado(estado)
    ejemplar = Ejemplar(
        id_libro=id_libro,
        codigo_inventario=codigo_inventario,
        estado=estado,
        fecha_alta=fecha_alta,
    )
    with traducir_errores():
        session.add(ejemplar)
        session.flush()
    return ejemplar


def obtener_por_id(session: Session, ejemplar_id: int) -> Ejemplar | None:
    return session.get(Ejemplar, ejemplar_id)


def obtener_o_error(session: Session, ejemplar_id: int) -> Ejemplar:
    ejemplar = session.get(Ejemplar, ejemplar_id)
    if ejemplar is None:
        raise RegistroNoEncontrado(f"No existe el ejemplar con id {ejemplar_id}.")
    return ejemplar


def obtener_por_codigo(session: Session, codigo: str) -> Ejemplar | None:
    stmt = select(Ejemplar).where(Ejemplar.codigo_inventario == codigo)
    return session.scalars(stmt).first()


def listar(session: Session, *, id_libro=None, estado=None,
           limite: int = 50, desplazamiento: int = 0) -> list[Ejemplar]:
    stmt = select(Ejemplar).options(joinedload(Ejemplar.libro))
    if id_libro:
        stmt = stmt.where(Ejemplar.id_libro == id_libro)
    if estado:
        _validar_estado(estado)
        stmt = stmt.where(Ejemplar.estado == estado)
    stmt = stmt.order_by(Ejemplar.codigo_inventario).limit(limite).offset(desplazamiento)
    return list(session.scalars(stmt))


def disponibles_de_libro(session: Session, id_libro: int) -> list[Ejemplar]:
    stmt = (
        select(Ejemplar)
        .where(Ejemplar.id_libro == id_libro, Ejemplar.estado == "disponible")
        .order_by(Ejemplar.codigo_inventario)
    )
    return list(session.scalars(stmt))


def contar_por_estado(session: Session, id_libro: int) -> dict[str, int]:
    stmt = (
        select(Ejemplar.estado, func.count())
        .where(Ejemplar.id_libro == id_libro)
        .group_by(Ejemplar.estado)
    )
    return {estado: cantidad for estado, cantidad in session.execute(stmt)}


def actualizar_estado(session: Session, ejemplar_id: int, estado: str) -> Ejemplar:
    _validar_estado(estado)
    ejemplar = obtener_o_error(session, ejemplar_id)
    ejemplar.estado = estado
    with traducir_errores():
        session.flush()
    return ejemplar


def actualizar(session: Session, ejemplar_id: int, **campos) -> Ejemplar:
    ejemplar = obtener_o_error(session, ejemplar_id)
    for campo, valor in campos.items():
        if campo not in _CAMPOS_EDITABLES:
            raise ValueError(f"Campo no editable en Ejemplar: {campo}")
        if campo == "estado":
            _validar_estado(valor)
        setattr(ejemplar, campo, valor)
    with traducir_errores():
        session.flush()
    return ejemplar


def eliminar(session: Session, ejemplar_id: int) -> None:
    ejemplar = obtener_o_error(session, ejemplar_id)
    with traducir_errores():
        session.delete(ejemplar)
        session.flush()


def _validar_estado(estado: str) -> None:
    if estado not in ESTADOS_VALIDOS:
        raise ValueError(
            f"Estado invalido: {estado!r}. Validos: {', '.join(ESTADOS_VALIDOS)}"
        )
