"""
Catalogos para poblar los <select> del frontend + estadisticas.

Cambios respecto de la version anterior:
  - los cuatro endpoints llamaban a repositorio.obtener_todos(), funcion que
    no existe en ninguno de esos modulos. Los cuatro devolvian 500.
    La funcion correcta se llama listar().
  - se agrega /estadisticas porque la consigna marca "No existen estadisticas
    de prestamos" como uno de los problemas a resolver.
"""

from datetime import date
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from config.database import get_session
from models import Ejemplar, Libro, Prestamo, Socio
from repositories import (
    autor_repository,
    editorial_repository,
    genero_repository,
    rango_repository,
    subgenero_repository,
)
from schemas.schemas import Estadisticas, ItemCatalogo

router = APIRouter(prefix="/api/catalogo", tags=["Catalogo"])

_TOPE = 200   # los catalogos son chicos, pero nunca se devuelve sin limite


@router.get("/generos", response_model=List[ItemCatalogo])
def listar_generos(db: Session = Depends(get_session)):
    return genero_repository.listar(db, limite=_TOPE)


@router.get("/subgeneros", response_model=List[ItemCatalogo])
def listar_subgeneros(
    id_genero: int | None = Query(default=None),
    db: Session = Depends(get_session),
):
    if id_genero:
        return subgenero_repository.listar_por_genero(db, id_genero, limite=_TOPE)
    return subgenero_repository.listar(db, limite=_TOPE)


@router.get("/editoriales", response_model=List[ItemCatalogo])
def listar_editoriales(db: Session = Depends(get_session)):
    return editorial_repository.listar(db, limite=_TOPE)


@router.get("/autores", response_model=List[ItemCatalogo])
def listar_autores(db: Session = Depends(get_session)):
    autores = autor_repository.listar(db, limite=_TOPE)
    return [
        ItemCatalogo(id=a.id, nombre=f"{a.apellido}, {a.nombre}")
        for a in autores
    ]


@router.get("/rangos", response_model=List[ItemCatalogo])
def listar_rangos(db: Session = Depends(get_session)):
    return rango_repository.listar(db, limite=_TOPE)


@router.get("/estadisticas", response_model=Estadisticas)
def estadisticas(db: Session = Depends(get_session)):
    """
    Todos los numeros salen de COUNT(*) en la base. Nada de traer las filas
    para contarlas en Python, y nada de guardar contadores en columnas.
    """
    hoy = date.today()

    def contar(entidad, *condiciones):
        stmt = select(func.count()).select_from(entidad)
        if condiciones:
            stmt = stmt.where(*condiciones)
        return db.scalar(stmt) or 0

    return Estadisticas(
        total_libros=contar(Libro),
        total_ejemplares=contar(Ejemplar),
        ejemplares_disponibles=contar(Ejemplar, Ejemplar.estado == "disponible"),
        total_socios_activos=contar(Socio, Socio.fecha_baja.is_(None)),
        prestamos_activos=contar(Prestamo, Prestamo.fecha_devolucion.is_(None)),
        prestamos_vencidos=contar(
            Prestamo,
            Prestamo.fecha_devolucion.is_(None),
            Prestamo.fecha_vencimiento < hoy,
        ),
    )
