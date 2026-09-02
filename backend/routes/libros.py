"""
ABM completo de Libros + buscador + listado paginado.

Cambios respecto de la version anterior:
  - crear() recibia el modelo Pydantic entero contra una firma keyword-only -> TypeError 500.
  - obtener_por_id() devolvia None y rompia el response_model -> 500 en vez de 404.
  - faltaban PUT y DELETE, o sea faltaban la M y la B de ABM.
  - se usaba obtener_todos() (sin eager loading) -> N+1: 24 consultas para 21 libros.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from config.database import get_session
from repositories import libro_repository
from schemas.schemas import LibroCreate, LibroOut, LibroUpdate

router = APIRouter(prefix="/api/libros", tags=["Libros"])


@router.get("", response_model=List[LibroOut])
def listar_libros(
    titulo: Optional[str] = Query(default=None, description="Busqueda parcial por titulo"),
    id_subgenero: Optional[int] = None,
    id_editorial: Optional[int] = None,
    id_autor: Optional[int] = None,
    limite: int = Query(default=50, ge=1, le=200),
    desplazamiento: int = Query(default=0, ge=0),
    db: Session = Depends(get_session),
):
    """
    Listado + buscador. Usa listar(), que trae autores, subgenero y editorial
    con eager loading: 2 consultas fijas en vez de una por cada libro.
    """
    return libro_repository.listar(
        db,
        titulo=titulo,
        id_subgenero=id_subgenero,
        id_editorial=id_editorial,
        id_autor=id_autor,
        limite=limite,
        desplazamiento=desplazamiento,
    )


@router.get("/contar")
def contar_libros(
    titulo: Optional[str] = None,
    id_subgenero: Optional[int] = None,
    db: Session = Depends(get_session),
):
    """Total de coincidencias, para que el front sepa cuantas paginas hay."""
    return {"total": libro_repository.contar(db, titulo=titulo, id_subgenero=id_subgenero)}


@router.get("/{id_libro}", response_model=LibroOut)
def obtener_libro(id_libro: int, db: Session = Depends(get_session)):
    # obtener_completo trae las relaciones; si no existe, obtener_o_error tira
    # RegistroNoEncontrado y el handler global lo convierte en 404.
    libro_repository.obtener_o_error(db, id_libro)
    return libro_repository.obtener_completo(db, id_libro)


@router.post("", response_model=LibroOut, status_code=status.HTTP_201_CREATED)
def crear_libro(data: LibroCreate, db: Session = Depends(get_session)):
    nuevo = libro_repository.crear(
        db,
        titulo=data.titulo,
        isbn=data.isbn,
        id_subgenero=data.id_subgenero,
        id_editorial=data.id_editorial,
        fecha_publicacion=data.fecha_publicacion,
        idioma=data.idioma,
        numero_edicion=data.numero_edicion,
        autores_ids=data.autores_ids or None,
    )
    db.commit()
    return libro_repository.obtener_completo(db, nuevo.id)


@router.put("/{id_libro}", response_model=LibroOut)
def modificar_libro(id_libro: int, data: LibroUpdate, db: Session = Depends(get_session)):
    """La M de ABM. Solo se tocan los campos que vienen en el cuerpo."""
    cambios = data.model_dump(exclude_unset=True, exclude_none=True)
    autores_ids = cambios.pop("autores_ids", None)

    if cambios:
        libro_repository.actualizar(db, id_libro, **cambios)
    if autores_ids is not None:
        libro_repository.asignar_autores(db, id_libro, autores_ids)
    if not cambios and autores_ids is None:
        libro_repository.obtener_o_error(db, id_libro)   # valida que exista

    db.commit()
    return libro_repository.obtener_completo(db, id_libro)


@router.delete("/{id_libro}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_libro(id_libro: int, db: Session = Depends(get_session)):
    """
    La B de ABM. Si el libro tiene ejemplares cargados, la FK con ON DELETE
    RESTRICT frena el borrado y el handler devuelve 409 con un mensaje claro.
    Eso es correcto: no queremos borrar un titulo que tiene copias en el estante.
    """
    libro_repository.eliminar(db, id_libro)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
