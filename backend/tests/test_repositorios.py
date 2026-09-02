"""CRUD y busquedas de los repositorios principales."""

from datetime import date

import pytest

from repositories import libro_repository, ejemplar_repository, socio_repository
from utils.db_errors import RegistroNoEncontrado


def test_crear_libro_le_asigna_id_y_autores(session, catalogo):
    creado = libro_repository.crear(
        session, titulo="Cosmos", isbn="9788499892204",
        id_subgenero=catalogo["subgenero"].id,
        id_editorial=catalogo["editorial"].id,
        fecha_publicacion=date(1980, 9, 28),
        idioma="Espanol", numero_edicion="3",
        autores_ids=[catalogo["autor"].id],
    )
    assert creado.id is not None
    assert [a.apellido for a in creado.autores] == ["Herbert"]


def test_buscar_libro_por_titulo_parcial(session, libro):
    resultados = libro_repository.listar(session, titulo="Dun")
    assert libro.titulo in [l.titulo for l in resultados]


def test_buscar_libro_por_autor(session, libro, catalogo):
    resultados = libro_repository.listar(session, id_autor=catalogo["autor"].id)
    assert len(resultados) == 1


def test_actualizar_libro_cambia_el_campo(session, libro):
    libro_repository.actualizar(session, libro.id, titulo="Dune (edicion revisada)")
    assert libro_repository.obtener_o_error(session, libro.id).titulo == "Dune (edicion revisada)"


def test_actualizar_campo_inexistente_falla(session, libro):
    with pytest.raises(ValueError):
        libro_repository.actualizar(session, libro.id, campo_inventado="x")


def test_eliminar_libro_lo_saca_de_la_base(session, catalogo):
    creado = libro_repository.crear(
        session, titulo="Descartable", id_subgenero=catalogo["subgenero"].id,
        id_editorial=catalogo["editorial"].id, fecha_publicacion=date(2000, 1, 1),
        idioma="Espanol", numero_edicion="1",
    )
    libro_repository.eliminar(session, creado.id)
    assert libro_repository.obtener_por_id(session, creado.id) is None


def test_ejemplares_disponibles_excluye_los_no_disponibles(session, libro, ejemplar):
    ejemplar_repository.crear(session, id_libro=libro.id,
                              codigo_inventario="INV-0002", fecha_alta=date.today())
    ejemplar_repository.actualizar_estado(session, ejemplar.id, "en_reparacion")
    disponibles = ejemplar_repository.disponibles_de_libro(session, libro.id)
    assert [e.codigo_inventario for e in disponibles] == ["INV-0002"]


def test_estado_invalido_es_rechazado(session, ejemplar):
    with pytest.raises(ValueError):
        ejemplar_repository.actualizar_estado(session, ejemplar.id, "extraviadisimo")


def test_buscar_socio_por_apellido(session, socio):
    assert socio_repository.listar(session, texto="Gimen")[0].id == socio.id


def test_baja_logica_conserva_el_socio(session, socio):
    socio_repository.dar_de_baja(session, socio.id, date(2026, 1, 31))
    assert socio_repository.obtener_o_error(session, socio.id).fecha_baja is not None
    assert socio_repository.listar(session, solo_activos=True) == []


def test_pedir_id_inexistente_levanta_no_encontrado(session):
    with pytest.raises(RegistroNoEncontrado):
        libro_repository.obtener_o_error(session, 999999)
