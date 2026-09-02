"""
ABM completo de Socios + buscador.

Cambios respecto de la version anterior:
  - crear() recibia el modelo Pydantic contra una firma keyword-only -> TypeError 500.
  - el DELETE estaba declarado como "/api/socios/{id}" DENTRO de un router con
    prefix="/api/socios", asi que la ruta real quedaba /api/socios/api/socios/{id}
    y el frontend recibia 405.
  - solo_activos se pasaba a incluir_inactivos: significan lo contrario, el
    filtro estaba invertido y el listado mostraba a los dados de baja.
  - faltaba PUT (la M de ABM).
"""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from config.database import get_session
from repositories import socio_repository
from schemas.schemas import SocioCreate, SocioOut, SocioUpdate

router = APIRouter(prefix="/api/socios", tags=["Socios"])


@router.get("", response_model=List[SocioOut])
def listar_socios(
    texto: Optional[str] = Query(default=None, description="Busca en nombre, apellido o DNI"),
    solo_activos: bool = Query(default=True, description="Oculta los socios dados de baja"),
    id_rango: Optional[int] = None,
    limite: int = Query(default=50, ge=1, le=200),
    desplazamiento: int = Query(default=0, ge=0),
    db: Session = Depends(get_session),
):
    # El nombre del parametro y el del repositorio ahora coinciden.
    return socio_repository.listar(
        db,
        texto=texto,
        id_rango=id_rango,
        solo_activos=solo_activos,
        limite=limite,
        desplazamiento=desplazamiento,
    )


@router.get("/{id_socio}", response_model=SocioOut)
def obtener_socio(id_socio: int, db: Session = Depends(get_session)):
    return socio_repository.obtener_o_error(db, id_socio)


@router.post("", response_model=SocioOut, status_code=status.HTTP_201_CREATED)
def crear_socio(data: SocioCreate, db: Session = Depends(get_session)):
    nuevo = socio_repository.crear(
        db,
        nombre=data.nombre,
        apellido=data.apellido,
        dni=data.dni,
        email=data.email,
        telefono=data.telefono,
        id_rango=data.id_rango,
        fecha_alta=date.today(),
    )
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.put("/{id_socio}", response_model=SocioOut)
def modificar_socio(id_socio: int, data: SocioUpdate, db: Session = Depends(get_session)):
    cambios = data.model_dump(exclude_unset=True, exclude_none=True)
    if cambios:
        socio_repository.actualizar(db, id_socio, **cambios)
    else:
        socio_repository.obtener_o_error(db, id_socio)
    db.commit()
    return socio_repository.obtener_o_error(db, id_socio)


@router.delete("/{id_socio}", response_model=SocioOut)
def dar_de_baja_socio(id_socio: int, db: Session = Depends(get_session)):
    """
    Baja LOGICA: el socio queda en la base con fecha_baja cargada.
    Es lo correcto: si lo borraramos, sus prestamos historicos quedarian
    huerfanos y perderiamos las estadisticas que pide la consigna.
    Si el socio no existe -> 404 (antes devolvia 200 diciendo 'dado de baja
    correctamente' aunque no hubiera tocado nada).
    """
    socio = socio_repository.obtener_o_error(db, id_socio)
    if socio.fecha_baja is not None:
        # Idempotente: ya estaba de baja, no es un error.
        return socio
    actualizado = socio_repository.dar_de_baja(db, id_socio, fecha_baja=date.today())
    db.commit()
    return actualizado


@router.post("/{id_socio}/reactivar", response_model=SocioOut)
def reactivar_socio(id_socio: int, db: Session = Depends(get_session)):
    """Deshace la baja logica. Sin esto una baja por error es irreversible."""
    socio_repository.actualizar(db, id_socio, fecha_baja=None)
    db.commit()
    return socio_repository.obtener_o_error(db, id_socio)
