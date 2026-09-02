"""
Ejemplares (las copias fisicas de cada titulo).

Cambios respecto de la version anterior:
  - usaba db.query() directo desde la ruta, salteandose la capa de repositorios
    y mezclando la API vieja de SQLAlchemy 1.x con el estilo 2.0 del resto.
  - no tenia response_model: devolvia el objeto ORM entero sin contrato.
  - no habia alta de ejemplares, asi que no se podian cargar copias nuevas.
"""

from datetime import date
from typing import List

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from config.database import get_session
from repositories import ejemplar_repository, libro_repository
from schemas.schemas import EjemplarConLibro, EjemplarCreate, EjemplarOut

router = APIRouter(prefix="/api/ejemplares", tags=["Ejemplares"])


@router.get("", response_model=List[EjemplarConLibro])
def listar_ejemplares(
    id_libro: int | None = None,
    estado: str | None = None,
    limite: int = Query(default=50, ge=1, le=200),
    desplazamiento: int = Query(default=0, ge=0),
    db: Session = Depends(get_session),
):
    ejemplares = ejemplar_repository.listar(
        db, id_libro=id_libro, estado=estado,
        limite=limite, desplazamiento=desplazamiento,
    )
    # listar() ya trae el libro con joinedload: esto no dispara consultas.
    return [
        EjemplarConLibro(
            id=e.id, id_libro=e.id_libro, codigo_inventario=e.codigo_inventario,
            estado=e.estado, fecha_alta=e.fecha_alta,
            titulo_libro=e.libro.titulo if e.libro else None,
        )
        for e in ejemplares
    ]


@router.get("/libro/{id_libro}", response_model=List[EjemplarOut])
def listar_por_libro(
    id_libro: int,
    solo_disponibles: bool = True,
    db: Session = Depends(get_session),
):
    """Lo que consume el select de la pantalla de prestamos."""
    libro_repository.obtener_o_error(db, id_libro)     # 404 si el libro no existe
    if solo_disponibles:
        return ejemplar_repository.disponibles_de_libro(db, id_libro)
    return ejemplar_repository.listar(db, id_libro=id_libro, limite=200)


@router.get("/libro/{id_libro}/resumen")
def resumen_por_estado(id_libro: int, db: Session = Depends(get_session)):
    """Cuantas copias hay en cada estado. GROUP BY en la base."""
    libro_repository.obtener_o_error(db, id_libro)
    return ejemplar_repository.contar_por_estado(db, id_libro)


@router.post("", response_model=EjemplarOut, status_code=status.HTTP_201_CREATED)
def crear_ejemplar(data: EjemplarCreate, db: Session = Depends(get_session)):
    libro_repository.obtener_o_error(db, data.id_libro)
    nuevo = ejemplar_repository.crear(
        db,
        id_libro=data.id_libro,
        codigo_inventario=data.codigo_inventario,
        estado=data.estado,
        fecha_alta=date.today(),
    )
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.patch("/{id_ejemplar}/estado", response_model=EjemplarOut)
def cambiar_estado(id_ejemplar: int, estado: str, db: Session = Depends(get_session)):
    """Para mandar una copia a reparacion o darla de baja por deterioro."""
    actualizado = ejemplar_repository.actualizar_estado(db, id_ejemplar, estado=estado)
    db.commit()
    return actualizado


@router.delete("/{id_ejemplar}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_ejemplar(id_ejemplar: int, db: Session = Depends(get_session)):
    """Si tiene prestamos historicos, la FK RESTRICT lo frena -> 409."""
    ejemplar_repository.eliminar(db, id_ejemplar)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
