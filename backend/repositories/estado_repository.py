"""Acceso a datos de la entidad Estado (estado de una copia física).

Tabla nueva: sale del "IdEstado" de la corrección 2.

En la versión anterior la lista de estados vivía en una constante de
Python y en un CHECK del schema. Ahora es una tabla: agregar
"en encuadernación" es insertar una fila, no editar y volver a
desplegar el código.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import Estado
from utils.db_errors import RegistroNoEncontrado, traducir_errores
from utils.texto import normalizar, normalizar_obligatorio

# Nombres de los estados que el sistema da por sentados (los carga el
# seed). El resto de la capa los referencia por estas constantes y no
# escribiendo el string suelto en cada archivo.
DISPONIBLE = "disponible"
PRESTADO = "prestado"
EN_REPARACION = "en_reparacion"
DANIADO = "dañado"
EXTRAVIADO = "extraviado"
BAJA = "baja"


def crear(session: Session, *, nombre: str, permite_prestamo: bool = False,
          descripcion: str | None = None) -> Estado:
    estado = Estado(
        nombre=normalizar_obligatorio(nombre, "estado"),
        permite_prestamo=permite_prestamo,
        descripcion=normalizar(descripcion),
    )
    with traducir_errores():
        session.add(estado)
        session.flush()
    return estado


def obtener_por_id(session: Session, estado_id: int) -> Estado | None:
    return session.get(Estado, estado_id)


def obtener_o_error(session: Session, estado_id: int) -> Estado:
    estado = session.get(Estado, estado_id)
    if estado is None:
        raise RegistroNoEncontrado(f"No existe el estado con id {estado_id}.")
    return estado


def obtener_por_nombre(session: Session, nombre: str) -> Estado | None:
    limpio = normalizar_obligatorio(nombre, "estado")
    return session.scalars(select(Estado).where(Estado.nombre == limpio)).first()


def obtener_o_error_por_nombre(session: Session, nombre: str) -> Estado:
    """Los estados no se crean al vuelo: son una lista controlada.

    Si alguien pide uno que no está cargado, es un error de datos, no una
    invitación a inventarlo.
    """
    estado = obtener_por_nombre(session, nombre)
    if estado is None:
        raise RegistroNoEncontrado(
            f"No existe el estado '{nombre}'. Estados cargados: "
            f"{', '.join(e.nombre for e in listar(session))}."
        )
    return estado


def resolver(session: Session, *, id_estado: int | None = None,
             nombre_estado: str | None = None) -> Estado:
    """Devuelve la FILA de estado, se la pidan por id o por nombre.

    Los repositorios que cambian el estado de una copia usan esto y le
    asignan el objeto (`libro.estado = ...`) en vez de escribir el id
    suelto. Es lo que mantiene coherente lo que hay en memoria con lo
    que hay en la base: si solo se toca `libro.id_estado`, el objeto
    `libro.estado` que ya estaba cargado sigue mostrando el estado viejo.
    """
    if id_estado is None and nombre_estado is None:
        raise ValueError("Hay que indicar id_estado o nombre_estado.")
    if id_estado is not None:
        return obtener_o_error(session, id_estado)
    return obtener_o_error_por_nombre(session, nombre_estado)


def id_disponible(session: Session) -> int:
    """Atajo para el alta de copias: el estado inicial de una copia nueva."""
    return obtener_o_error_por_nombre(session, DISPONIBLE).id


def id_prestado(session: Session) -> int:
    return obtener_o_error_por_nombre(session, PRESTADO).id


def listar(session: Session, *, solo_prestables: bool = False,
           limite: int = 50, desplazamiento: int = 0) -> list[Estado]:
    stmt = select(Estado)
    if solo_prestables:
        stmt = stmt.where(Estado.permite_prestamo.is_(True))
    stmt = stmt.order_by(Estado.id).limit(limite).offset(desplazamiento)
    return list(session.scalars(stmt))


def contar(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Estado)) or 0


def actualizar(session: Session, estado_id: int, **campos) -> Estado:
    estado = obtener_o_error(session, estado_id)
    editables = {"nombre", "permite_prestamo", "descripcion"}
    for campo, valor in campos.items():
        if campo not in editables:
            raise ValueError(f"Campo no editable en Estado: {campo}")
        if campo == "nombre":
            valor = normalizar_obligatorio(valor, "estado")
        setattr(estado, campo, valor)
    with traducir_errores():
        session.flush()
    return estado


def eliminar(session: Session, estado_id: int) -> None:
    """Falla con ViolacionDeIntegridad si alguna copia está en ese estado."""
    estado = obtener_o_error(session, estado_id)
    with traducir_errores():
        session.delete(estado)
        session.flush()
