"""Acceso a datos de la entidad Libro = LA COPIA FÍSICA.

OJO al cambio de significado (correcciones 2 y 3): en la versión
anterior `libro` era la ficha bibliográfica y `ejemplar` la copia. Ahora
la ficha se llama `titulo` y `libro` es el objeto de papel. Este
repositorio reemplaza al viejo `ejemplar_repository`.

Acá está el corazón de la corrección 3: cada fila es una unidad física
con su estado, su código de inventario y su historial de préstamos.
"""

from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from models import Estado, Libro, Titulo
from repositories import (
    editorial_repository,
    estado_repository,
    idioma_repository,
    titulo_repository,
)
from utils.db_errors import RegistroNoEncontrado, traducir_errores
from utils.texto import normalizar

_CAMPOS_EDITABLES = {
    "id_titulo", "id_editorial", "isbn", "id_estado",
    "edicion", "id_idioma", "codigo_inventario", "fecha_alta",
}


def crear(session: Session, *, id_titulo: int, id_editorial: int, id_idioma: int,
          fecha_alta: date | None = None, isbn: str | None = None,
          edicion: str | None = None, id_estado: int | None = None,
          codigo_inventario: str | None = None) -> Libro:
    """Da de alta UNA copia física.

    Si no se pasa estado, entra como 'disponible'. Si no se pasa código
    de inventario, se genera uno a partir del id (INV-000042): toda copia
    tiene que poder identificarse en el mostrador.
    """
    libro = Libro(
        id_titulo=id_titulo,
        id_editorial=id_editorial,
        id_idioma=id_idioma,
        isbn=normalizar(isbn),
        edicion=normalizar(edicion),
        id_estado=id_estado or estado_repository.id_disponible(session),
        codigo_inventario=normalizar(codigo_inventario),
        fecha_alta=fecha_alta or date.today(),
    )
    with traducir_errores():
        session.add(libro)
        session.flush()

        if libro.codigo_inventario is None:
            libro.codigo_inventario = f"INV-{libro.id:06d}"
            session.flush()
    return libro


def alta_por_texto(session: Session, *, titulo: str, editorial: str,
                   idioma: str, genero: str | None = None,
                   autores: str | None = None, isbn: str | None = None,
                   edicion: str | None = None, cantidad: int = 1,
                   fecha_alta: date | None = None) -> list[Libro]:
    """Alta completa desde el formulario, todo por texto.

    Es la función que resuelve las correcciones 4 y 5 de una sola vez:
    el HTML manda el título, el género, la editorial, los autores y el
    idioma ESCRITOS, y acá se resuelve o se crea cada cosa. No hay ni un
    `<select>` de por medio.

        alta_por_texto(
            session,
            titulo="IT", genero="Terror", autores="King, Stephen",
            editorial="Plaza & Janés", idioma="Español",
            isbn="9788497596718", edicion="2", cantidad=3,
        )

    `cantidad` existe porque una biblioteca no compra una copia: compra
    tres. Devuelve la lista de copias creadas, cada una con su código.

    IMPORTANTE: no hace commit. Si algo falla en el medio, el que llama
    hace rollback y no queda ni el título ni el autor a medio crear.
    """
    if cantidad < 1:
        raise ValueError("La cantidad de copias tiene que ser al menos 1.")

    fila_titulo = titulo_repository.obtener_o_crear_por_texto(
        session, nombre=titulo, genero=genero, autores=autores
    )
    fila_editorial = editorial_repository.obtener_o_crear(session, editorial)
    fila_idioma = idioma_repository.obtener_o_crear(session, idioma)
    id_disponible = estado_repository.id_disponible(session)

    return [
        crear(
            session,
            id_titulo=fila_titulo.id,
            id_editorial=fila_editorial.id,
            id_idioma=fila_idioma.id,
            id_estado=id_disponible,
            isbn=isbn,
            edicion=edicion,
            fecha_alta=fecha_alta,
        )
        for _ in range(cantidad)
    ]


def obtener_por_id(session: Session, libro_id: int) -> Libro | None:
    return session.get(Libro, libro_id)


def obtener_o_error(session: Session, libro_id: int) -> Libro:
    libro = session.get(Libro, libro_id)
    if libro is None:
        raise RegistroNoEncontrado(f"No existe la copia con id {libro_id}.")
    return libro


def obtener_por_codigo(session: Session, codigo: str) -> Libro | None:
    """Buscar por el código pegado en el lomo: es como se identifica una
    copia en el mostrador."""
    limpio = normalizar(codigo)
    if limpio is None:
        return None
    stmt = select(Libro).where(Libro.codigo_inventario == limpio)
    return session.scalars(stmt).first()


def obtener_detallado(session: Session, libro_id: int) -> Libro | None:
    """La copia con título, autores, editorial, idioma y estado cargados."""
    stmt = (
        select(Libro)
        .where(Libro.id == libro_id)
        .options(
            joinedload(Libro.titulo).selectinload(Titulo.autores),
            joinedload(Libro.editorial),
            joinedload(Libro.idioma),
            joinedload(Libro.estado),
        )
    )
    return session.scalars(stmt).unique().first()


def listar(session: Session, *, id_titulo: int | None = None,
           texto_titulo: str | None = None, id_estado: int | None = None,
           id_editorial: int | None = None, solo_disponibles: bool = False,
           limite: int = 50, desplazamiento: int = 0) -> list[Libro]:
    stmt = select(Libro).options(
        joinedload(Libro.titulo),
        joinedload(Libro.editorial),
        joinedload(Libro.estado),
        joinedload(Libro.idioma),
    )
    if id_titulo:
        stmt = stmt.where(Libro.id_titulo == id_titulo)
    if texto_titulo:
        # Buscar copias escribiendo el título, no el id.
        stmt = stmt.join(Libro.titulo).where(
            Titulo.nombre.like(f"%{texto_titulo.strip()}%")
        )
    if id_estado:
        stmt = stmt.where(Libro.id_estado == id_estado)
    if id_editorial:
        stmt = stmt.where(Libro.id_editorial == id_editorial)
    if solo_disponibles:
        # Sin hardcodear nombres de estado: se pregunta a la tabla.
        stmt = stmt.join(Libro.estado).where(Estado.permite_prestamo.is_(True))

    stmt = stmt.order_by(Libro.codigo_inventario).limit(limite).offset(desplazamiento)
    return list(session.scalars(stmt).unique())


def disponibles_de_titulo(session: Session, id_titulo: int) -> list[Libro]:
    """Las copias de esta obra que se pueden prestar ahora.

    Es lo que hay que mostrar cuando alguien elige un título para
    prestar: primero se elige la obra, después la copia concreta.
    """
    stmt = (
        select(Libro)
        .join(Libro.estado)
        .where(Libro.id_titulo == id_titulo, Estado.permite_prestamo.is_(True))
        .options(joinedload(Libro.estado), joinedload(Libro.editorial))
        .order_by(Libro.codigo_inventario)
    )
    return list(session.scalars(stmt).unique())


def contar(session: Session, *, id_titulo: int | None = None,
           solo_disponibles: bool = False) -> int:
    stmt = select(func.count()).select_from(Libro)
    if id_titulo:
        stmt = stmt.where(Libro.id_titulo == id_titulo)
    if solo_disponibles:
        stmt = stmt.join(Estado, Estado.id == Libro.id_estado).where(
            Estado.permite_prestamo.is_(True)
        )
    return session.scalar(stmt) or 0


def contar_por_estado(session: Session, id_titulo: int | None = None) -> dict[str, int]:
    """Cuántas copias hay en cada estado. Alimenta el panel de la biblioteca."""
    stmt = (
        select(Estado.nombre, func.count(Libro.id))
        .join(Libro, Libro.id_estado == Estado.id)
        .group_by(Estado.nombre)
    )
    if id_titulo:
        stmt = stmt.where(Libro.id_titulo == id_titulo)
    return {nombre: cantidad for nombre, cantidad in session.execute(stmt)}


def resumen_inventario(session: Session) -> dict[str, int]:
    """Los números del inventario físico, en una sola consulta.

    Total de copias, cuántas prestables y cuántas fuera de circulación
    (rotas, extraviadas, en reparación o dadas de baja). Es el resumen
    que pide la corrección 3: saber en qué estado está el patrimonio.
    """
    prestables = func.sum(case((Estado.permite_prestamo.is_(True), 1), else_=0))
    stmt = select(func.count(Libro.id), prestables).join(
        Estado, Estado.id == Libro.id_estado
    )
    total, disponibles = session.execute(stmt).one()
    total = int(total or 0)
    disponibles = int(disponibles or 0)
    return {
        "copias": total,
        "disponibles": disponibles,
        "fuera_de_circulacion": total - disponibles,
    }


def cambiar_estado(session: Session, libro_id: int, *,
                   id_estado: int | None = None,
                   nombre_estado: str | None = None) -> Libro:
    """Cambia el estado de la copia. Se puede pasar el id o el nombre.

    Es lo que se usa cuando una copia vuelve rota, se manda a reparar o
    se da de baja.
    """
    libro = obtener_o_error(session, libro_id)
    # Se asigna el objeto y no el id: así el `libro.estado` que ya está
    # cargado en memoria refleja el cambio en el acto.
    libro.estado = estado_repository.resolver(
        session, id_estado=id_estado, nombre_estado=nombre_estado
    )
    with traducir_errores():
        session.flush()
    return libro


def actualizar(session: Session, libro_id: int, **campos) -> Libro:
    libro = obtener_o_error(session, libro_id)
    for campo, valor in campos.items():
        if campo not in _CAMPOS_EDITABLES:
            raise ValueError(f"Campo no editable en Libro: {campo}")
        if campo in ("isbn", "edicion", "codigo_inventario"):
            valor = normalizar(valor)
        setattr(libro, campo, valor)
    with traducir_errores():
        session.flush()
    return libro


def eliminar(session: Session, libro_id: int) -> None:
    """Borrado físico. Falla si la copia tiene préstamos registrados.

    Para sacar de circulación una copia que ya se prestó alguna vez, lo
    correcto es `cambiar_estado(..., nombre_estado='baja')`: así el
    historial de préstamos no se pierde.
    """
    libro = obtener_o_error(session, libro_id)
    with traducir_errores():
        session.delete(libro)
        session.flush()
