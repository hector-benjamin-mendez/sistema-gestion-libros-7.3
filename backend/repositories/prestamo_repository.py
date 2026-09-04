"""Acceso a datos de la entidad Prestamo.

Un préstamo está ACTIVO cuando fecha_devolucion IS NULL. Esa es la
definición en todo el sistema.

El préstamo apunta a `libro`, o sea a LA COPIA: no se presta "IT", se
presta la copia INV-000009 de IT (corrección 3).

Novedad: `registrar_devolucion` recibe EN QUÉ ESTADO volvió la copia y
lo guarda en el préstamo además de actualizar la copia. Ese es el dato
que permite decir "esta copia se rompió en manos de Augusto" y no solo
"esta copia está rota".
"""

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from models import Estado, Libro, Prestamo, Titulo
from repositories import estado_repository, socio_repository
from utils.db_errors import (
    ReglaDeDatos,
    RegistroNoEncontrado,
    traducir_errores,
)
from utils.texto import normalizar


def _con_relaciones():
    """Carga socio, copia, título y estado de una sola vez.

    Sin esto, listar 20 préstamos y mostrar el título de cada uno son 20
    consultas extra (el clásico N+1).
    """
    return (
        joinedload(Prestamo.socio),
        joinedload(Prestamo.libro).joinedload(Libro.titulo).selectinload(Titulo.autores),
        joinedload(Prestamo.libro).joinedload(Libro.estado),
        joinedload(Prestamo.estado_devolucion),
    )


# ---------- Alta ----------

def crear(session: Session, *, id_socio: int, id_libro: int,
          fecha_prestamo: date, fecha_vencimiento: date) -> Prestamo:
    """Registra el préstamo y nada más.

    No toca el estado de la copia ni valida reglas de negocio. Para el
    flujo completo está `prestar()`, que es lo que conviene usar.
    """
    prestamo = Prestamo(
        id_socio=id_socio,
        id_libro=id_libro,
        fecha_prestamo=fecha_prestamo,
        fecha_vencimiento=fecha_vencimiento,
    )
    with traducir_errores():
        session.add(prestamo)
        session.flush()
    return prestamo


def prestar(session: Session, *, id_socio: int, id_libro: int,
            fecha_prestamo: date | None = None,
            dias: int | None = None) -> Prestamo:
    """Presta una copia: crea el préstamo Y la marca como prestada.

    Las dos cosas van juntas en la misma sesión a propósito. Separarlas
    es lo que produce copias que figuran disponibles en el sistema y no
    están en el estante.

    · `dias`: si no se pasa, sale del rango del socio.
    · Verifica que el estado de la copia habilite el préstamo. Eso NO es
      una regla de negocio de Héctor: es coherencia de la tabla `estado`.
      Las reglas de él (límite del rango, socio suspendido) siguen siendo
      suyas; acá están los insumos para chequearlas.

    No hace commit: eso lo decide quien orquesta.
    """
    socio = socio_repository.obtener_o_error(session, id_socio)

    libro = session.get(Libro, id_libro)
    if libro is None:
        raise RegistroNoEncontrado(f"No existe la copia con id {id_libro}.")

    if not libro.estado.permite_prestamo:
        raise ReglaDeDatos(
            f"La copia {libro.codigo_inventario} no se puede prestar: "
            f"está en estado '{libro.estado.nombre}'."
        )

    inicio = fecha_prestamo or date.today()
    plazo = dias if dias is not None else socio.rango.dias_prestamo

    prestamo = crear(
        session,
        id_socio=id_socio,
        id_libro=id_libro,
        fecha_prestamo=inicio,
        fecha_vencimiento=inicio + timedelta(days=plazo),
    )
    libro.estado = estado_repository.resolver(
        session, nombre_estado=estado_repository.PRESTADO
    )
    with traducir_errores():
        session.flush()
    return prestamo


# ---------- Devolución ----------

def registrar_devolucion(session: Session, prestamo_id: int, *,
                         fecha_devolucion: date | None = None,
                         nombre_estado: str = estado_repository.DISPONIBLE,
                         id_estado: int | None = None,
                         observaciones: str | None = None) -> Prestamo:
    """Cierra el préstamo dejando asentado CÓMO volvió la copia.

    El ejemplo de la corrección 3, tal cual:

        registrar_devolucion(
            session, prestamo.id,
            fecha_devolucion=date(2026, 8, 26),
            nombre_estado="dañado",
            observaciones="Volvió con la tapa arrancada.",
        )

    Después de esto la copia queda en estado 'dañado' y el préstamo
    guarda que volvió así, de manos de ese socio. Recién con ese dato
    registrado la suspensión se puede justificar.
    """
    prestamo = obtener_o_error(session, prestamo_id)
    if prestamo.fecha_devolucion is not None:
        raise ReglaDeDatos(f"El préstamo {prestamo_id} ya fue devuelto.")

    estado = estado_repository.resolver(
        session, id_estado=id_estado, nombre_estado=nombre_estado
    )

    fecha = fecha_devolucion or date.today()
    if fecha < prestamo.fecha_prestamo:
        raise ReglaDeDatos(
            "La devolución no puede ser anterior a la fecha del préstamo."
        )

    prestamo.fecha_devolucion = fecha
    prestamo.estado_devolucion = estado
    prestamo.observaciones = normalizar(observaciones)
    # La copia queda en el mismo estado en el que volvió.
    prestamo.libro.estado = estado

    with traducir_errores():
        session.flush()
    return prestamo


# ---------- Consultas ----------

def obtener_por_id(session: Session, prestamo_id: int) -> Prestamo | None:
    return session.get(Prestamo, prestamo_id)


def obtener_o_error(session: Session, prestamo_id: int) -> Prestamo:
    prestamo = session.get(Prestamo, prestamo_id)
    if prestamo is None:
        raise RegistroNoEncontrado(f"No existe el préstamo con id {prestamo_id}.")
    return prestamo


def obtener_detallado(session: Session, prestamo_id: int) -> Prestamo | None:
    stmt = (
        select(Prestamo)
        .where(Prestamo.id == prestamo_id)
        .options(*_con_relaciones())
    )
    return session.scalars(stmt).unique().first()


def listar(session: Session, *, id_socio: int | None = None,
           id_libro: int | None = None, id_titulo: int | None = None,
           solo_activos: bool = False, vencidos_al: date | None = None,
           id_estado_devolucion: int | None = None,
           limite: int = 50, desplazamiento: int = 0) -> list[Prestamo]:
    stmt = select(Prestamo).options(*_con_relaciones())

    if id_socio:
        stmt = stmt.where(Prestamo.id_socio == id_socio)
    if id_libro:
        stmt = stmt.where(Prestamo.id_libro == id_libro)
    if id_titulo:
        stmt = stmt.join(Prestamo.libro).where(Libro.id_titulo == id_titulo)
    if solo_activos:
        stmt = stmt.where(Prestamo.fecha_devolucion.is_(None))
    if vencidos_al is not None:
        stmt = stmt.where(
            Prestamo.fecha_devolucion.is_(None),
            Prestamo.fecha_vencimiento < vencidos_al,
        )
    if id_estado_devolucion:
        stmt = stmt.where(Prestamo.id_estado_devolucion == id_estado_devolucion)

    stmt = (
        stmt.order_by(Prestamo.fecha_prestamo.desc(), Prestamo.id.desc())
        .limit(limite)
        .offset(desplazamiento)
    )
    return list(session.scalars(stmt).unique())


def historial_de_copia(session: Session, id_libro: int,
                       limite: int = 50) -> list[Prestamo]:
    """Todo lo que le pasó a UNA copia física: quién la tuvo y cómo volvió.

    Es la consulta que hace posible el ejemplo de la corrección 3. Sin
    ella, "la copia está rota" es un dato sin responsable.
    """
    stmt = (
        select(Prestamo)
        .where(Prestamo.id_libro == id_libro)
        .options(*_con_relaciones())
        .order_by(Prestamo.fecha_prestamo.desc())
        .limit(limite)
    )
    return list(session.scalars(stmt).unique())


def devoluciones_en_mal_estado(session: Session, *, id_socio: int | None = None,
                               desde: date | None = None,
                               limite: int = 50) -> list[Prestamo]:
    """Préstamos que volvieron en un estado que no habilita el préstamo.

    O sea: rotos, extraviados o mandados a reparar. Es el antecedente que
    se mira antes de decidir una suspensión.
    """
    stmt = (
        select(Prestamo)
        .join(Estado, Estado.id == Prestamo.id_estado_devolucion)
        .where(Estado.permite_prestamo.is_(False))
        .options(*_con_relaciones())
    )
    if id_socio:
        stmt = stmt.where(Prestamo.id_socio == id_socio)
    if desde:
        stmt = stmt.where(Prestamo.fecha_devolucion >= desde)

    stmt = stmt.order_by(Prestamo.fecha_devolucion.desc()).limit(limite)
    return list(session.scalars(stmt).unique())


def activos_de_socio(session: Session, id_socio: int) -> list[Prestamo]:
    stmt = (
        select(Prestamo)
        .where(Prestamo.id_socio == id_socio, Prestamo.fecha_devolucion.is_(None))
        .options(*_con_relaciones())
        .order_by(Prestamo.fecha_vencimiento)
    )
    return list(session.scalars(stmt).unique())


def contar_activos_de_socio(session: Session, id_socio: int) -> int:
    """Se compara contra socio.rango.max_prestamos. Es un COUNT(*): no
    trae las filas para después medir la lista con len()."""
    stmt = (
        select(func.count())
        .select_from(Prestamo)
        .where(Prestamo.id_socio == id_socio, Prestamo.fecha_devolucion.is_(None))
    )
    return session.scalar(stmt) or 0


def contar(session: Session, *, solo_activos: bool = False,
           vencidos_al: date | None = None) -> int:
    stmt = select(func.count()).select_from(Prestamo)
    if solo_activos:
        stmt = stmt.where(Prestamo.fecha_devolucion.is_(None))
    if vencidos_al is not None:
        stmt = stmt.where(
            Prestamo.fecha_devolucion.is_(None),
            Prestamo.fecha_vencimiento < vencidos_al,
        )
    return session.scalar(stmt) or 0


def copia_esta_prestada(session: Session, id_libro: int) -> bool:
    stmt = (
        select(Prestamo.id)
        .where(Prestamo.id_libro == id_libro, Prestamo.fecha_devolucion.is_(None))
        .limit(1)
    )
    return session.scalars(stmt).first() is not None


def eliminar(session: Session, prestamo_id: int) -> None:
    """Solo para corregir una carga equivocada. El historial no se borra."""
    prestamo = obtener_o_error(session, prestamo_id)
    with traducir_errores():
        session.delete(prestamo)
        session.flush()
