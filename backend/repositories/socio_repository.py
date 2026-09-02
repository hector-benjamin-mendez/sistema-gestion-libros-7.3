"""Acceso a datos de la entidad Socio."""

from sqlalchemy import select, or_
from sqlalchemy.orm import Session, joinedload, selectinload
# (datetime ya no se usa: la fecha de baja la decide la capa de rutas)
from models import Socio
from utils.db_errors import RegistroNoEncontrado, traducir_errores

_CAMPOS_EDITABLES = {
    "nombre", "apellido", "dni", "email", "telefono",
    "id_rango", "fecha_alta", "fecha_baja",
}


def crear(session: Session, *, nombre, apellido, dni, email,
          id_rango, fecha_alta, telefono=None) -> Socio:
    socio = Socio(
        nombre=nombre, apellido=apellido, dni=dni, email=email,
        telefono=telefono, id_rango=id_rango, fecha_alta=fecha_alta,
    )
    with traducir_errores():
        session.add(socio)
        session.flush()
    return socio


def obtener_por_id(session: Session, socio_id: int) -> Socio | None:
    return session.get(Socio, socio_id)


def obtener_o_error(session: Session, socio_id: int) -> Socio:
    socio = session.get(Socio, socio_id)
    if socio is None:
        raise RegistroNoEncontrado(f"No existe el socio con id {socio_id}.")
    return socio


def obtener_con_rango(session: Session, socio_id: int) -> Socio | None:
    stmt = (
        select(Socio)
        .where(Socio.id == socio_id)
        .options(joinedload(Socio.rango), selectinload(Socio.prestamos))
    )
    return session.scalars(stmt).unique().first()


def obtener_por_dni(session: Session, dni: str) -> Socio | None:
    return session.scalars(select(Socio).where(Socio.dni == dni)).first()


def obtener_por_email(session: Session, email: str) -> Socio | None:
    return session.scalars(select(Socio).where(Socio.email == email)).first()


def listar(session: Session, *, texto=None, id_rango=None, solo_activos=False,
           limite: int = 50, desplazamiento: int = 0) -> list[Socio]:
    stmt = select(Socio).options(joinedload(Socio.rango))
    if texto:
        patron = f"%{texto}%"
        stmt = stmt.where(
            or_(Socio.apellido.like(patron),
                Socio.nombre.like(patron),
                Socio.dni.like(patron))
        )
    if id_rango:
        stmt = stmt.where(Socio.id_rango == id_rango)
    if solo_activos:
        stmt = stmt.where(Socio.fecha_baja.is_(None))
    stmt = stmt.order_by(Socio.apellido, Socio.nombre).limit(limite).offset(desplazamiento)
    return list(session.scalars(stmt))


def actualizar(session: Session, socio_id: int, **campos) -> Socio:
    socio = obtener_o_error(session, socio_id)
    for campo, valor in campos.items():
        if campo not in _CAMPOS_EDITABLES:
            raise ValueError(f"Campo no editable en Socio: {campo}")
        setattr(socio, campo, valor)
    with traducir_errores():
        session.flush()
    return socio


def dar_de_baja(session: Session, socio_id: int, fecha_baja) -> Socio:
    """Baja logica: el socio queda en la base con fecha_baja cargada."""
    socio = obtener_o_error(session, socio_id)
    socio.fecha_baja = fecha_baja
    with traducir_errores():
        session.flush()
    return socio


# NOTA: aca habia dos funciones que se eliminaron.
#
# 1. obtener_todos(): duplicaba listar() sin eager loading ni limite, y su
#    parametro incluir_inactivos significaba lo contrario que el solo_activos
#    de la ruta, asi que el filtro quedaba invertido y el listado mostraba
#    a los socios dados de baja.
#
# 2. eliminar(): hacia session.commit() adentro del repositorio, rompiendo la
#    regla del README ("los repositorios hacen flush(), nunca commit()").
#    Ademas escribia datetime.now() en una columna DATE y, si el socio no
#    existia, devolvia None en silencio y la ruta contestaba 200 diciendo
#    "dado de baja correctamente" sin haber tocado nada.
#    La baja logica correcta es dar_de_baja(), que esta mas arriba.