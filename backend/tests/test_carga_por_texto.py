"""Carga por escritura libre: correcciones 4 y 5.

  4) "manejar el tema de las editoriales y generos desde el html, que se
      pueda cargar, mejor dicho cargar POR TITULO"
  5) "No nos gusta la lista de seleccion para editorial y autores.
      Queremos que sea por texto."

O sea: el formulario manda texto y la base tiene que resolverlo sin
llenarse de duplicados. Eso es lo que verifica este archivo.
"""

from datetime import date

import pytest

from repositories import (
    autor_repository,
    editorial_repository,
    genero_repository,
    libro_repository,
    titulo_repository,
)
from utils.texto import separar_lista, separar_nombre_autor


# ---------- Parseo de lo que se tipea ----------

@pytest.mark.parametrize("texto, esperado", [
    ("Stephen King",       ("Stephen", "King")),
    ("King, Stephen",      ("Stephen", "King")),
    ("Ursula K. Le Guin",  ("Ursula K.", "Le Guin")),
    ("Borges",             ("", "Borges")),
    ("  Carl   Sagan  ",   ("Carl", "Sagan")),
])
def test_separar_nombre_de_autor(texto, esperado):
    assert separar_nombre_autor(texto) == esperado


def test_varios_autores_se_separan_por_punto_y_coma():
    """La coma queda libre para la forma 'Apellido, Nombre'."""
    assert separar_lista("Sagan, Carl; Druyan, Ann") == ["Sagan, Carl", "Druyan, Ann"]


# ---------- Buscar o crear ----------

def test_el_genero_escrito_se_crea_una_sola_vez(session):
    primero = genero_repository.obtener_o_crear(session, "Policial")
    segundo = genero_repository.obtener_o_crear(session, "  policial ")
    assert primero.id == segundo.id


def test_la_editorial_escrita_se_crea_una_sola_vez(session):
    primera = editorial_repository.obtener_o_crear(session, "Anagrama")
    segunda = editorial_repository.obtener_o_crear(session, "ANAGRAMA")
    assert primera.id == segunda.id


def test_la_editorial_creada_por_texto_no_exige_grupo_editorial(session):
    """Nadie sabe el grupo editorial mientras carga un libro."""
    creada = editorial_repository.obtener_o_crear(session, "Ediciones del Barrio")
    assert creada.id_grupo_editorial is None


def test_el_autor_escrito_se_crea_una_sola_vez_aunque_cambie_la_forma(session):
    primero = autor_repository.obtener_o_crear_por_texto(session, "Stephen King")
    segundo = autor_repository.obtener_o_crear_por_texto(session, "King, Stephen")
    assert primero.id == segundo.id


def test_el_autocompletado_sugiere_lo_que_ya_existe(session, catalogo):
    sugerencias = editorial_repository.sugerir(session, "plaza")
    assert catalogo["editorial"].id in [fila.id for fila in sugerencias]


# ---------- Alta completa desde el formulario ----------

def test_alta_por_texto_crea_titulo_genero_editorial_idioma_y_autores(session, estados):
    copias = libro_repository.alta_por_texto(
        session,
        titulo="La invención de Morel",
        genero="Ciencia ficción",
        autores="Bioy Casares, Adolfo",
        editorial="Losada",
        idioma="Español",
        isbn="9789500300001",
        edicion="1",
    )

    assert len(copias) == 1
    copia = copias[0]
    assert copia.titulo.nombre == "La invención de Morel"
    assert copia.titulo.genero.nombre == "Ciencia ficción"
    assert copia.editorial.nombre == "Losada"
    assert copia.idioma.nombre == "Español"
    assert [a.apellido for a in copia.titulo.autores] == ["Bioy Casares"]
    assert copia.estado.nombre == "disponible"
    assert copia.codigo_inventario is not None


def test_alta_por_texto_carga_varias_copias_de_una(session, estados):
    """Una biblioteca no compra una copia: compra tres."""
    copias = libro_repository.alta_por_texto(
        session, titulo="El Aleph", genero="Cuento",
        autores="Borges, Jorge Luis", editorial="Emecé",
        idioma="Español", cantidad=3,
    )
    assert len(copias) == 3
    assert len({c.id for c in copias}) == 3
    assert len({c.codigo_inventario for c in copias}) == 3
    # Tres objetos distintos, un solo título.
    assert len({c.id_titulo for c in copias}) == 1


def test_cargar_otra_copia_del_mismo_titulo_no_duplica_nada(session, titulo, catalogo):
    """La segunda carga de IT reusa el título, el género y la editorial."""
    titulos_antes = titulo_repository.contar(session)

    copias = libro_repository.alta_por_texto(
        session, titulo="it", editorial="Plaza & Janés", idioma="Español",
    )

    assert titulo_repository.contar(session) == titulos_antes
    assert copias[0].id_titulo == titulo.id
    assert copias[0].id_editorial == catalogo["editorial"].id


def test_un_titulo_nuevo_sin_genero_es_rechazado(session, estados):
    with pytest.raises(ValueError):
        libro_repository.alta_por_texto(
            session, titulo="Obra sin clasificar",
            editorial="Losada", idioma="Español",
        )


def test_cargar_un_titulo_existente_le_suma_autores_sin_pisar_los_viejos(
    session, titulo, catalogo
):
    libro_repository.alta_por_texto(
        session, titulo="IT", editorial="Plaza & Janés", idioma="Español",
        autores="Straub, Peter",
    )
    apellidos = sorted(autor.apellido for autor in titulo.autores)
    assert apellidos == ["King", "Straub"]


def test_la_cantidad_tiene_que_ser_positiva(session, estados):
    with pytest.raises(ValueError):
        libro_repository.alta_por_texto(
            session, titulo="X", genero="Y", editorial="Z",
            idioma="Español", cantidad=0,
        )


def test_el_alta_por_texto_respeta_la_fecha_de_alta(session, estados):
    copias = libro_repository.alta_por_texto(
        session, titulo="Rayuela", genero="Novela", editorial="Sudamericana",
        idioma="Español", fecha_alta=date(2020, 5, 1),
    )
    assert copias[0].fecha_alta == date(2020, 5, 1)
