"""Acceso a datos de la entidad Titulo (la OBRA).

Tabla nueva de la corrección 1. Es la que ordena todo el catálogo: el
usuario busca "IT", encuentra un solo resultado y ahí ve cuántas copias
hay y cuántas están disponibles.

Corrección 4 ("cargar POR TITULO"): `obtener_o_crear_por_texto` recibe
el título, el género y los autores como texto y resuelve o crea todo lo
que haga falta.
"""

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from models import Autor, Estado, Libro, Titulo
from repositories import autor_repository, genero_repository
from utils.db_errors import RegistroNoEncontrado, traducir_errores
from utils.texto import normalizar, normalizar_obligatorio


def crear(session: Session, *, nombre: str, id_genero: int,
          autores_ids: list[int] | None = None) -> Titulo:
    titulo = Titulo(
        nombre=normalizar_obligatorio(nombre, "título"),
        id_genero=id_genero,
    )
    if autores_ids:
        titulo.autores = _autores_por_ids(session, autores_ids)
    with traducir_errores():
        session.add(titulo)
        session.flush()
    return titulo


def obtener_por_id(session: Session, titulo_id: int) -> Titulo | None:
    return session.get(Titulo, titulo_id)


def obtener_o_error(session: Session, titulo_id: int) -> Titulo:
    titulo = session.get(Titulo, titulo_id)
    if titulo is None:
        raise RegistroNoEncontrado(f"No existe el título con id {titulo_id}.")
    return titulo


def obtener_por_nombre(session: Session, nombre: str) -> Titulo | None:
    limpio = normalizar_obligatorio(nombre, "título")
    return session.scalars(select(Titulo).where(Titulo.nombre == limpio)).first()


def obtener_completo(session: Session, titulo_id: int) -> Titulo | None:
    """El título con género, autores y todas sus copias ya cargados.

    Es la pantalla de detalle: una sola llamada trae todo lo que hay que
    mostrar, sin una consulta por copia.
    """
    stmt = (
        select(Titulo)
        .where(Titulo.id == titulo_id)
        .options(
            selectinload(Titulo.genero),
            selectinload(Titulo.autores),
            selectinload(Titulo.libros).selectinload(Libro.estado),
            selectinload(Titulo.libros).selectinload(Libro.editorial),
        )
    )
    return session.scalars(stmt).unique().first()


def obtener_o_crear_por_texto(session: Session, *, nombre: str,
                              genero: str | None = None,
                              autores: str | None = None) -> Titulo:
    """Resuelve el título a partir de lo que se escribió en el formulario.

    · Si el título ya existe, lo devuelve y le SUMA los autores nuevos
      que hayan venido (nunca los reemplaza: dos altas de la misma obra
      no tienen por qué traer la misma lista completa).
    · Si no existe, lo crea, y de paso crea el género y los autores que
      falten.

    `genero` es obligatorio solo cuando el título es nuevo: para cargar
    una segunda copia de un título ya existente no hace falta volver a
    escribirlo.
    """
    limpio = normalizar_obligatorio(nombre, "título")
    existente = obtener_por_nombre(session, limpio)

    autores_nuevos = autor_repository.obtener_o_crear_varios(session, autores)

    if existente is not None:
        ya_estan = {autor.id for autor in existente.autores}
        for autor in autores_nuevos:
            if autor.id not in ya_estan:
                existente.autores.append(autor)
        if autores_nuevos:
            with traducir_errores():
                session.flush()
        return existente

    if normalizar(genero) is None:
        raise ValueError(
            f"El título '{limpio}' es nuevo: hay que indicar el género."
        )

    fila_genero = genero_repository.obtener_o_crear(session, genero)
    titulo = Titulo(nombre=limpio, id_genero=fila_genero.id)
    titulo.autores = autores_nuevos
    with traducir_errores():
        session.add(titulo)
        session.flush()
    return titulo


def listar(session: Session, *, texto: str | None = None,
           id_genero: int | None = None, id_autor: int | None = None,
           limite: int = 50, desplazamiento: int = 0) -> list[Titulo]:
    stmt = select(Titulo).options(
        selectinload(Titulo.genero),
        selectinload(Titulo.autores),
    )
    if texto:
        stmt = stmt.where(Titulo.nombre.like(f"%{texto.strip()}%"))
    if id_genero:
        stmt = stmt.where(Titulo.id_genero == id_genero)
    if id_autor:
        stmt = stmt.join(Titulo.autores).where(Autor.id == id_autor)
    stmt = stmt.order_by(Titulo.nombre).limit(limite).offset(desplazamiento)
    return list(session.scalars(stmt).unique())


def listar_con_stock(session: Session, *, texto: str | None = None,
                     id_genero: int | None = None,
                     solo_con_disponibles: bool = False,
                     limite: int = 50, desplazamiento: int = 0) -> list[dict]:
    """El listado principal del catálogo: título + cuántas copias hay.

    Devuelve, por cada título: la fila, el total de copias y cuántas se
    pueden prestar hoy.

    Los dos números salen de la misma consulta con un GROUP BY. La
    alternativa —traer los títulos y después contar las copias de cada
    uno— son N+1 consultas: con 200 títulos, 201 viajes a la base.
    """
    disponibles = func.sum(
        case((Estado.permite_prestamo.is_(True), 1), else_=0)
    )
    stmt = (
        select(
            Titulo,
            func.count(Libro.id).label("copias"),
            disponibles.label("disponibles"),
        )
        .join(Libro, Libro.id_titulo == Titulo.id, isouter=True)
        .join(Estado, Estado.id == Libro.id_estado, isouter=True)
        .options(selectinload(Titulo.genero), selectinload(Titulo.autores))
        # Se agrupa por TODAS las columnas de titulo y no solo por el id.
        # Con `GROUP BY titulo.id` MySQL 8 y MariaDB tiran el error 1055
        # ("titulo.nombre isn't in GROUP BY") apenas está activo
        # ONLY_FULL_GROUP_BY, que es el modo por defecto de MySQL 8 en
        # adelante. Nombrándolas todas, la consulta corre igual en
        # cualquier configuración.
        .group_by(Titulo.id, Titulo.nombre, Titulo.id_genero)
    )
    if texto:
        stmt = stmt.where(Titulo.nombre.like(f"%{texto.strip()}%"))
    if id_genero:
        stmt = stmt.where(Titulo.id_genero == id_genero)
    if solo_con_disponibles:
        stmt = stmt.having(disponibles > 0)

    stmt = stmt.order_by(Titulo.nombre).limit(limite).offset(desplazamiento)

    return [
        {
            "titulo": titulo,
            "copias": int(copias or 0),
            "disponibles": int(cantidad_disponibles or 0),
        }
        for titulo, copias, cantidad_disponibles in session.execute(stmt).unique()
    ]


def contar(session: Session, *, texto: str | None = None,
           id_genero: int | None = None) -> int:
    stmt = select(func.count()).select_from(Titulo)
    if texto:
        stmt = stmt.where(Titulo.nombre.like(f"%{texto.strip()}%"))
    if id_genero:
        stmt = stmt.where(Titulo.id_genero == id_genero)
    return session.scalar(stmt) or 0


def sugerir(session: Session, texto: str, limite: int = 10) -> list[Titulo]:
    """Autocompletado del input de título en el alta de copias."""
    limpio = normalizar(texto)
    if limpio is None:
        return []
    stmt = (
        select(Titulo)
        .where(Titulo.nombre.like(f"%{limpio}%"))
        .order_by(Titulo.nombre)
        .limit(limite)
    )
    return list(session.scalars(stmt))


def actualizar(session: Session, titulo_id: int, **campos) -> Titulo:
    titulo = obtener_o_error(session, titulo_id)
    for campo, valor in campos.items():
        if campo not in ("nombre", "id_genero"):
            raise ValueError(f"Campo no editable en Titulo: {campo}")
        if campo == "nombre":
            valor = normalizar_obligatorio(valor, "título")
        setattr(titulo, campo, valor)
    with traducir_errores():
        session.flush()
    return titulo


def asignar_autores(session: Session, titulo_id: int,
                    autores_ids: list[int]) -> Titulo:
    """Reemplaza la lista completa de autores del título."""
    titulo = obtener_o_error(session, titulo_id)
    titulo.autores = _autores_por_ids(session, autores_ids)
    with traducir_errores():
        session.flush()
    return titulo


def eliminar(session: Session, titulo_id: int) -> None:
    """Falla con ViolacionDeIntegridad si el título tiene copias cargadas.

    Es a propósito: borrar un título con copias en el estante dejaría
    objetos físicos sin ficha.
    """
    titulo = obtener_o_error(session, titulo_id)
    with traducir_errores():
        session.delete(titulo)
        session.flush()


def _autores_por_ids(session: Session, autores_ids: list[int]) -> list[Autor]:
    autores = list(session.scalars(select(Autor).where(Autor.id.in_(autores_ids))))
    faltantes = set(autores_ids) - {autor.id for autor in autores}
    if faltantes:
        raise RegistroNoEncontrado(f"No existen los autores: {sorted(faltantes)}")
    return autores
