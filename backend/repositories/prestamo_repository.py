"""Acceso a datos de la entidad Prestamo.

Un prestamo esta ACTIVO cuando fecha_devolucion IS NULL.
Esa es la definicion en todo el sistema.
"""

from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload

from models import Ejemplar, Prestamo
from utils.db_errors import RegistroNoEncontrado, traducir_errores


def crear(session: Session, *, id_socio, id_ejemplar,
          fecha_prestamo, fecha_vencimiento) -> Prestamo:
    """Registra el prestamo. NO valida reglas de negocio: eso es de Hector."""
    prestamo = Prestamo(
        id_socio=id_socio,
        id_ejemplar=id_ejemplar,
        fecha_prestamo=fecha_prestamo,
        fecha_vencimiento=fecha_vencimiento,
    )
    with traducir_errores():
        session.add(prestamo)
        session.flush()
    return prestamo


def obtener_por_id(session: Session, prestamo_id: int) -> Prestamo | None:
    return session.get(Prestamo, prestamo_id)


def obtener_detallado(session: Session, prestamo_id: int) -> Prestamo | None:
    """Igual que obtener_por_id pero con socio, ejemplar y libro ya cargados."""
    stmt = (
        select(Prestamo)
        .where(Prestamo.id == prestamo_id)
        .options(
            joinedload(Prestamo.socio),
            joinedload(Prestamo.ejemplar).joinedload(Ejemplar.libro),
        )
    )
    return session.scalars(stmt).unique().first()


def obtener_o_error(session: Session, prestamo_id: int) -> Prestamo:
    prestamo = session.get(Prestamo, prestamo_id)
    if prestamo is None:
        raise RegistroNoEncontrado(f"No existe el prestamo con id {prestamo_id}.")
    return prestamo


def listar(session: Session, *, id_socio=None, id_ejemplar=None,
           solo_activos=False, vencidos_al=None,
           limite: int = 50, desplazamiento: int = 0) -> list[Prestamo]:
    # Se agrega el salto ejemplar -> libro para que la respuesta pueda incluir
    # el titulo sin disparar una consulta por cada prestamo listado.
    stmt = select(Prestamo).options(
        joinedload(Prestamo.socio),
        joinedload(Prestamo.ejemplar).joinedload(Ejemplar.libro),
    )
    if id_socio:
        stmt = stmt.where(Prestamo.id_socio == id_socio)
    if id_ejemplar:
        stmt = stmt.where(Prestamo.id_ejemplar == id_ejemplar)
    if solo_activos:
        stmt = stmt.where(Prestamo.fecha_devolucion.is_(None))
    if vencidos_al is not None:
        stmt = stmt.where(
            Prestamo.fecha_devolucion.is_(None),
            Prestamo.fecha_vencimiento < vencidos_al,
        )
    stmt = stmt.order_by(Prestamo.fecha_prestamo.desc()).limit(limite).offset(desplazamiento)
    return list(session.scalars(stmt).unique())


def activos_de_socio(session: Session, id_socio: int) -> list[Prestamo]:
    stmt = (
        select(Prestamo)
        .where(Prestamo.id_socio == id_socio, Prestamo.fecha_devolucion.is_(None))
        .options(joinedload(Prestamo.ejemplar).joinedload(Ejemplar.libro))
        .order_by(Prestamo.fecha_vencimiento)
    )
    return list(session.scalars(stmt).unique())


def contar_activos_de_socio(session: Session, id_socio: int) -> int:
    """Hector compara este numero contra socio.rango.max_prestamos."""
    stmt = (
        select(func.count())
        .select_from(Prestamo)
        .where(Prestamo.id_socio == id_socio, Prestamo.fecha_devolucion.is_(None))
    )
    return session.scalar(stmt) or 0


def ejemplar_esta_prestado(session: Session, id_ejemplar: int) -> bool:
    """MySQL no puede garantizar esto por constraint. Se consulta."""
    stmt = (
        select(Prestamo.id)
        .where(Prestamo.id_ejemplar == id_ejemplar,
               Prestamo.fecha_devolucion.is_(None))
        .limit(1)
    )
    return session.scalars(stmt).first() is not None


def registrar_devolucion(session: Session, prestamo_id: int, fecha_devolucion) -> Prestamo:
    prestamo = obtener_o_error(session, prestamo_id)
    if prestamo.fecha_devolucion is not None:
        raise ValueError(f"El prestamo {prestamo_id} ya fue devuelto.")
    prestamo.fecha_devolucion = fecha_devolucion
    with traducir_errores():
        session.flush()
    return prestamo


def eliminar(session: Session, prestamo_id: int) -> None:
    prestamo = obtener_o_error(session, prestamo_id)
    with traducir_errores():
        session.delete(prestamo)
        session.flush()
