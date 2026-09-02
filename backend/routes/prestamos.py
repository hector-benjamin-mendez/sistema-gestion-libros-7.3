"""
Prestamos y devoluciones.

Cambios respecto de la version anterior:
  - llamaba a prestamo_repository.obtener_prestamos_activos() y obtener_todos(),
    que NO EXISTEN -> AttributeError -> 500 en TODO el modulo.
  - contaba prestamos activos con len(lista): traia los objetos para contarlos.
    Ahora usa contar_activos_de_socio(), que hace SELECT COUNT(*).
  - no validaba que el ejemplar existiera ni que estuviera disponible:
    un id inexistente reventaba contra la FK como 500.
  - si el rango del socio no existia, rango.max_prestamos daba AttributeError.
  - la respuesta no traia el titulo ni el socio, asi que el front no podia
    mostrar nada util sin pedir cada registro aparte.
"""

from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from config.database import get_session
from repositories import (
    ejemplar_repository,
    prestamo_repository,
    rango_repository,
    socio_repository,
)
from schemas.schemas import PrestamoCreate, PrestamoOut

router = APIRouter(prefix="/api/prestamos", tags=["Prestamos"])


def _a_dto(prestamo, hoy: date | None = None) -> PrestamoOut:
    """
    Arma la respuesta enriquecida. Las relaciones ya vienen cargadas por el
    eager loading del repositorio, asi que esto NO dispara consultas nuevas.
    Los campos calculados (devuelto, vencido, dias_atraso) se derivan aca:
    no se guardan en la base porque son datos derivables.
    """
    hoy = hoy or date.today()
    devuelto = prestamo.fecha_devolucion is not None
    vencido = (not devuelto) and prestamo.fecha_vencimiento < hoy
    atraso = (hoy - prestamo.fecha_vencimiento).days if vencido else 0

    socio = prestamo.socio
    ejemplar = prestamo.ejemplar
    libro = ejemplar.libro if ejemplar is not None else None

    return PrestamoOut(
        id=prestamo.id,
        id_socio=prestamo.id_socio,
        id_ejemplar=prestamo.id_ejemplar,
        fecha_prestamo=prestamo.fecha_prestamo,
        fecha_vencimiento=prestamo.fecha_vencimiento,
        fecha_devolucion=prestamo.fecha_devolucion,
        socio_nombre=f"{socio.apellido}, {socio.nombre}" if socio else None,
        libro_titulo=libro.titulo if libro else None,
        codigo_inventario=ejemplar.codigo_inventario if ejemplar else None,
        devuelto=devuelto,
        vencido=vencido,
        dias_atraso=atraso,
    )


@router.get("", response_model=List[PrestamoOut])
def listar_prestamos(
    solo_activos: bool = Query(default=False, description="Solo los no devueltos"),
    solo_vencidos: bool = Query(default=False, description="Activos y pasados de fecha"),
    id_socio: Optional[int] = None,
    id_ejemplar: Optional[int] = None,
    limite: int = Query(default=50, ge=1, le=200),
    desplazamiento: int = Query(default=0, ge=0),
    db: Session = Depends(get_session),
):
    """Listado con filtros. El filtrado lo hace la base, no el navegador."""
    hoy = date.today()
    prestamos = prestamo_repository.listar(
        db,
        id_socio=id_socio,
        id_ejemplar=id_ejemplar,
        solo_activos=solo_activos,
        vencidos_al=hoy if solo_vencidos else None,
        limite=limite,
        desplazamiento=desplazamiento,
    )
    return [_a_dto(p, hoy) for p in prestamos]


@router.get("/{id_prestamo}", response_model=PrestamoOut)
def obtener_prestamo(id_prestamo: int, db: Session = Depends(get_session)):
    return _a_dto(prestamo_repository.obtener_o_error(db, id_prestamo))


@router.post("", response_model=PrestamoOut, status_code=status.HTTP_201_CREATED)
def crear_prestamo(data: PrestamoCreate, db: Session = Depends(get_session)):
    hoy = date.today()

    # 1. El socio tiene que existir y estar activo.
    socio = socio_repository.obtener_por_id(db, data.id_socio)
    if socio is None:
        raise HTTPException(404, detail="El socio no existe.")
    if socio.fecha_baja is not None:
        raise HTTPException(409, detail="El socio esta dado de baja y no puede retirar material.")

    # 2. El rango define la politica (cuantos y por cuantos dias).
    rango = rango_repository.obtener_por_id(db, socio.id_rango)
    if rango is None:
        raise HTTPException(409, detail="El socio no tiene un rango valido asignado.")

    # 3. El ejemplar tiene que existir y estar disponible.
    ejemplar = ejemplar_repository.obtener_por_id(db, data.id_ejemplar)
    if ejemplar is None:
        raise HTTPException(404, detail="El ejemplar no existe.")
    if ejemplar.estado != "disponible":
        raise HTTPException(409, detail=f"El ejemplar no esta disponible (estado: {ejemplar.estado}).")
    if prestamo_repository.ejemplar_esta_prestado(db, data.id_ejemplar):
        raise HTTPException(409, detail="El ejemplar ya figura en un prestamo activo.")

    # 4. Tope de prestamos simultaneos: COUNT(*), no len(lista).
    activos = prestamo_repository.contar_activos_de_socio(db, socio.id)
    if activos >= rango.max_prestamos:
        raise HTTPException(
            409,
            detail=(f"El socio ya tiene {activos} prestamos activos y su rango "
                    f"'{rango.nombre}' permite {rango.max_prestamos}."),
        )

    # 5. Un solo commit al final: prestamo + cambio de estado son una
    #    unica transaccion. Si algo falla, no queda un ejemplar marcado
    #    como prestado sin prestamo asociado.
    nuevo = prestamo_repository.crear(
        db,
        id_socio=socio.id,
        id_ejemplar=ejemplar.id,
        fecha_prestamo=hoy,
        fecha_vencimiento=hoy + timedelta(days=rango.dias_prestamo),
    )
    ejemplar_repository.actualizar_estado(db, ejemplar.id, estado="prestado")
    db.commit()

    return _a_dto(prestamo_repository.obtener_o_error(db, nuevo.id), hoy)


@router.post("/{id_prestamo}/devolucion", response_model=PrestamoOut)
def registrar_devolucion(id_prestamo: int, db: Session = Depends(get_session)):
    """
    Devolucion REAL contra la base. Antes el frontend marcaba un booleano en
    memoria y avisaba 'registrada con exito' sin guardar nada.
    """
    hoy = date.today()
    prestamo = prestamo_repository.obtener_o_error(db, id_prestamo)
    if prestamo.fecha_devolucion is not None:
        raise HTTPException(409, detail="Este prestamo ya fue devuelto.")

    prestamo_repository.registrar_devolucion(db, id_prestamo, fecha_devolucion=hoy)
    # El ejemplar vuelve al estante salvo que estuviera dado de baja.
    if prestamo.ejemplar is not None and prestamo.ejemplar.estado != "baja":
        ejemplar_repository.actualizar_estado(db, prestamo.id_ejemplar, estado="disponible")
    db.commit()

    return _a_dto(prestamo_repository.obtener_o_error(db, id_prestamo), hoy)
