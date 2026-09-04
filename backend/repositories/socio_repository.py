"""Acceso a datos de la entidad Socio.

Novedad de la corrección 3: la SUSPENSIÓN. El ejemplo del profesor
termina con "podés tomar la decisión de suspenderlo", así que el socio
tiene que poder quedar sancionado sin ser dado de baja.

Son dos cosas distintas y conviene no mezclarlas:
  · `fecha_baja`       -> se fue de la biblioteca. Baja lógica.
  · `suspendido_hasta` -> sigue siendo socio, pero no puede pedir libros
                          hasta esa fecha. Vence sola, nadie tiene que
                          acordarse de levantarla.
"""

from datetime import date, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from models import Socio
from utils.db_errors import RegistroNoEncontrado, traducir_errores
from utils.texto import normalizar, normalizar_obligatorio

_CAMPOS_EDITABLES = {
    "nombre", "apellido", "dni", "email", "telefono",
    "id_rango", "fecha_alta", "fecha_baja", "suspendido_hasta",
}


def crear(session: Session, *, nombre: str, apellido: str, dni: str, email: str,
          id_rango: int, fecha_alta: date | None = None,
          telefono: str | None = None) -> Socio:
    socio = Socio(
        nombre=normalizar_obligatorio(nombre, "nombre"),
        apellido=normalizar_obligatorio(apellido, "apellido"),
        dni=normalizar_obligatorio(dni, "DNI"),
        email=normalizar_obligatorio(email, "email"),
        telefono=normalizar(telefono),
        id_rango=id_rango,
        fecha_alta=fecha_alta or date.today(),
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
    limpio = normalizar_obligatorio(dni, "DNI")
    return session.scalars(select(Socio).where(Socio.dni == limpio)).first()


def obtener_por_email(session: Session, email: str) -> Socio | None:
    limpio = normalizar_obligatorio(email, "email")
    return session.scalars(select(Socio).where(Socio.email == limpio)).first()


def listar(session: Session, *, texto: str | None = None, id_rango: int | None = None,
           solo_activos: bool = False, solo_suspendidos: bool = False,
           al_dia: date | None = None,
           limite: int = 50, desplazamiento: int = 0) -> list[Socio]:
    """Padrón, con los filtros que usa la pantalla de socios.

    `texto` busca por apellido, nombre o DNI en una sola caja: es lo que
    hace el buscador del listado.
    """
    hoy = al_dia or date.today()
    stmt = select(Socio).options(joinedload(Socio.rango))

    if texto:
        patron = f"%{texto.strip()}%"
        stmt = stmt.where(
            or_(Socio.apellido.like(patron),
                Socio.nombre.like(patron),
                Socio.dni.like(patron))
        )
    if id_rango:
        stmt = stmt.where(Socio.id_rango == id_rango)
    if solo_activos:
        stmt = stmt.where(Socio.fecha_baja.is_(None))
    if solo_suspendidos:
        stmt = stmt.where(Socio.suspendido_hasta.is_not(None),
                          Socio.suspendido_hasta >= hoy)

    stmt = stmt.order_by(Socio.apellido, Socio.nombre).limit(limite).offset(desplazamiento)
    return list(session.scalars(stmt).unique())


def contar(session: Session, *, solo_activos: bool = False) -> int:
    stmt = select(func.count()).select_from(Socio)
    if solo_activos:
        stmt = stmt.where(Socio.fecha_baja.is_(None))
    return session.scalar(stmt) or 0


def actualizar(session: Session, socio_id: int, **campos) -> Socio:
    socio = obtener_o_error(session, socio_id)
    for campo, valor in campos.items():
        if campo not in _CAMPOS_EDITABLES:
            raise ValueError(f"Campo no editable en Socio: {campo}")
        if campo in ("nombre", "apellido", "dni", "email"):
            valor = normalizar_obligatorio(valor, campo)
        if campo == "telefono":
            valor = normalizar(valor)
        setattr(socio, campo, valor)
    with traducir_errores():
        session.flush()
    return socio


def dar_de_baja(session: Session, socio_id: int,
                fecha_baja: date | None = None) -> Socio:
    """Baja lógica: el socio queda en la base con fecha_baja cargada.

    No se borra nunca: sus préstamos históricos tienen que seguir
    apuntando a alguien.
    """
    socio = obtener_o_error(session, socio_id)
    socio.fecha_baja = fecha_baja or date.today()
    with traducir_errores():
        session.flush()
    return socio


def reactivar(session: Session, socio_id: int) -> Socio:
    socio = obtener_o_error(session, socio_id)
    socio.fecha_baja = None
    with traducir_errores():
        session.flush()
    return socio


# ---------- Suspensión (corrección 3) ----------

def suspender(session: Session, socio_id: int, *, hasta: date) -> Socio:
    """Sanciona al socio hasta la fecha indicada, inclusive."""
    socio = obtener_o_error(session, socio_id)
    if hasta < date.today():
        raise ValueError("La suspensión tiene que terminar en una fecha futura.")
    socio.suspendido_hasta = hasta
    with traducir_errores():
        session.flush()
    return socio


def suspender_por_dias(session: Session, socio_id: int, dias: int,
                       desde: date | None = None) -> Socio:
    """Lo mismo pero en la forma en que se piensa la sanción.

        suspender_por_dias(session, augusto.id, 30)

    Si el socio ya estaba suspendido, la nueva sanción se cuenta desde
    el final de la anterior: no la pisa.
    """
    if dias < 1:
        raise ValueError("La suspensión tiene que ser de al menos un día.")

    socio = obtener_o_error(session, socio_id)
    inicio = desde or date.today()
    if socio.suspendido_hasta and socio.suspendido_hasta > inicio:
        inicio = socio.suspendido_hasta

    socio.suspendido_hasta = inicio + timedelta(days=dias)
    with traducir_errores():
        session.flush()
    return socio


def levantar_suspension(session: Session, socio_id: int) -> Socio:
    socio = obtener_o_error(session, socio_id)
    socio.suspendido_hasta = None
    with traducir_errores():
        session.flush()
    return socio


def esta_habilitado(session: Session, socio_id: int,
                    al_dia: date | None = None) -> bool:
    """¿Puede pedir prestado? Contesta lo que la capa de servicios
    pregunta antes de cada préstamo: ni dado de baja ni suspendido."""
    return obtener_o_error(session, socio_id).puede_pedir_prestado(al_dia)
