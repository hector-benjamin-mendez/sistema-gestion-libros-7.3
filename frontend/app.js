/* ============================================================
   Sistema de Gestion Bibliotecaria - Grupo 7.3
   Modulo unico del frontend.

   Antes este archivo existia pero NINGUN HTML lo cargaba, y cada pagina
   reimplementaba la misma logica adentro de un <script> inline: tres
   versiones de "renderizar tabla", dos de "guardar libro", ninguna
   compartida. Ahora las paginas solo declaran su HTML y este archivo
   maneja todo, eligiendo que hacer segun <body data-pagina="...">.
   ============================================================ */

'use strict';

const API = '/api';   // ruta relativa: el mismo server sirve el front y la API

/* ------------------------------------------------------------------
   1. UTILIDADES
   ------------------------------------------------------------------ */

/** Escapa HTML. Sin esto, un libro titulado <img src=x onerror=...>
 *  ejecuta codigo al renderizar la tabla (XSS). */
function esc(valor) {
  if (valor === null || valor === undefined) return '';
  return String(valor)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

/** Retrasa la ejecucion: evita disparar una consulta por cada tecla. */
function esperar(fn, ms = 350) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

function fechaLegible(iso) {
  if (!iso) return '—';
  const [a, m, d] = iso.split('-');
  return `${d}/${m}/${a}`;
}

function $(sel) { return document.querySelector(sel); }
function $$(sel) { return Array.from(document.querySelectorAll(sel)); }

/* ------------------------------------------------------------------
   2. AVISOS  (reemplazan a alert())
   ------------------------------------------------------------------ */

function avisar(mensaje, tipo = 'info', duracion = 5000) {
  let cont = $('#contenedor-avisos');
  if (!cont) {
    cont = document.createElement('div');
    cont.id = 'contenedor-avisos';
    document.body.appendChild(cont);
  }

  const aviso = document.createElement('div');
  aviso.className = `aviso aviso-${tipo}`;
  aviso.setAttribute('role', tipo === 'error' ? 'alert' : 'status');
  aviso.innerHTML = `
    <span>${esc(mensaje)}</span>
    <button class="cerrar" aria-label="Cerrar aviso">&times;</button>`;

  const cerrar = () => {
    aviso.classList.add('saliendo');
    setTimeout(() => aviso.remove(), 250);
  };
  aviso.querySelector('.cerrar').addEventListener('click', cerrar);
  cont.appendChild(aviso);
  if (duracion) setTimeout(cerrar, duracion);
}

/* ------------------------------------------------------------------
   3. CLIENTE HTTP
   ------------------------------------------------------------------ */

class ErrorApi extends Error {
  constructor(mensaje, estado) {
    super(mensaje);
    this.estado = estado;
  }
}

/**
 * Envoltorio de fetch. Su trabajo principal es RESCATAR el mensaje del
 * backend: antes se descartaba y se mostraba "Error al guardar el libro
 * en el servidor", ocultandole al usuario que el problema real era, por
 * ejemplo, un DNI duplicado.
 */
async function pedir(ruta, opciones = {}) {
  let respuesta;
  try {
    respuesta = await fetch(`${API}${ruta}`, {
      headers: opciones.cuerpo ? { 'Content-Type': 'application/json' } : {},
      method: opciones.metodo || 'GET',
      body: opciones.cuerpo ? JSON.stringify(opciones.cuerpo) : undefined,
    });
  } catch {
    throw new ErrorApi('No se pudo conectar con el servidor. Verificá que uvicorn esté corriendo.', 0);
  }

  if (respuesta.status === 204) return null;

  let datos = null;
  try { datos = await respuesta.json(); } catch { /* cuerpo vacio o no JSON */ }

  if (!respuesta.ok) {
    let detalle = datos && datos.detail;
    if (Array.isArray(detalle)) {
      detalle = detalle.map(e => e.msg || JSON.stringify(e)).join(' | ');
    }
    throw new ErrorApi(detalle || `El servidor respondió ${respuesta.status}.`, respuesta.status);
  }
  return datos;
}

const api = {
  obtener: (ruta) => pedir(ruta),
  crear:   (ruta, cuerpo) => pedir(ruta, { metodo: 'POST', cuerpo }),
  editar:  (ruta, cuerpo) => pedir(ruta, { metodo: 'PUT', cuerpo }),
  borrar:  (ruta) => pedir(ruta, { metodo: 'DELETE' }),
};

/** Arma un query string salteando los filtros vacios. */
function consulta(params) {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== '' && v !== null && v !== undefined) p.append(k, v);
  });
  const s = p.toString();
  return s ? `?${s}` : '';
}

/* ------------------------------------------------------------------
   4. ESTADOS DE TABLA
   ------------------------------------------------------------------ */

function filaMensaje(tbody, columnas, titulo, detalle, esError = false) {
  tbody.innerHTML = `
    <tr class="fila-mensaje ${esError ? 'es-error' : ''}">
      <td colspan="${columnas}">
        <span class="titulo-mensaje">${esc(titulo)}</span>
        ${esc(detalle || '')}
      </td>
    </tr>`;
}

function filaCargando(tbody, columnas) {
  const celdas = Array.from({ length: columnas },
    () => '<td><span class="cargando-linea"></span></td>').join('');
  tbody.innerHTML = `<tr>${celdas}</tr><tr>${celdas}</tr><tr>${celdas}</tr>`;
}

function contarEn(selector, cantidad, sustantivo) {
  const el = $(selector);
  if (el) el.textContent = `${cantidad} ${sustantivo}${cantidad === 1 ? '' : 's'}`;
}

/* ------------------------------------------------------------------
   5. MODAL
   ------------------------------------------------------------------ */

const modal = {
  abrir(titulo, htmlCuerpo, alGuardar) {
    let fondo = $('#fondo-modal');
    if (!fondo) {
      fondo = document.createElement('div');
      fondo.id = 'fondo-modal';
      fondo.className = 'fondo-modal';
      document.body.appendChild(fondo);
    }
    fondo.innerHTML = `
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="titulo-modal">
        <h3 id="titulo-modal">${esc(titulo)}</h3>
        <form id="form-modal">
          ${htmlCuerpo}
          <div class="acciones-formulario">
            <button type="button" class="btn-secundario" data-cerrar>Cancelar</button>
            <button type="submit">Guardar cambios</button>
          </div>
        </form>
      </div>`;
    fondo.classList.add('abierto');

    const cerrar = () => {
      fondo.classList.remove('abierto');
      document.removeEventListener('keydown', porEscape);
    };
    const porEscape = (e) => { if (e.key === 'Escape') cerrar(); };

    fondo.querySelector('[data-cerrar]').addEventListener('click', cerrar);
    fondo.addEventListener('click', (e) => { if (e.target === fondo) cerrar(); });
    document.addEventListener('keydown', porEscape);

    fondo.querySelector('#form-modal').addEventListener('submit', async (e) => {
      e.preventDefault();
      const boton = e.target.querySelector('button[type="submit"]');
      boton.disabled = true;
      boton.textContent = 'Guardando…';
      try {
        await alGuardar(new FormData(e.target));
        cerrar();
      } catch (err) {
        avisar(err.message, 'error', 8000);
        boton.disabled = false;
        boton.textContent = 'Guardar cambios';
      }
    });

    const primero = fondo.querySelector('input, select');
    if (primero) primero.focus();
    return cerrar;
  },
};

/* ------------------------------------------------------------------
   6. CATALOGOS  (se piden una vez y se reutilizan)
   ------------------------------------------------------------------ */

const catalogos = {
  _cache: {},
  async traer(nombre) {
    if (!this._cache[nombre]) {
      this._cache[nombre] = await api.obtener(`/catalogo/${nombre}`);
    }
    return this._cache[nombre];
  },
  invalidar(nombre) { delete this._cache[nombre]; },
};

async function poblarSelect(select, nombreCatalogo, textoVacio, seleccionado = null) {
  if (!select) return;
  try {
    const items = await catalogos.traer(nombreCatalogo);
    select.innerHTML = `<option value="">${esc(textoVacio)}</option>` +
      items.map(i => `<option value="${i.id}" ${String(i.id) === String(seleccionado) ? 'selected' : ''}>${esc(i.nombre)}</option>`).join('');
  } catch (err) {
    select.innerHTML = `<option value="">No se pudo cargar</option>`;
    avisar(`No se pudo cargar el listado de ${nombreCatalogo}: ${err.message}`, 'error');
  }
}

/* ------------------------------------------------------------------
   7. SALUD DEL SERVIDOR
   ------------------------------------------------------------------ */

async function verificarServidor() {
  const banner = $('#banner-servidor');
  try {
    await api.obtener('/health');
    if (banner) banner.classList.remove('visible');
    return true;
  } catch {
    if (banner) banner.classList.add('visible');
    return false;
  }
}

/* ==================================================================
   PAGINA: INICIO
   ================================================================== */

const paginaInicio = {
  async iniciar() {
    const campos = {
      'total-libros': ['total_libros', v => `${v} ejemplares en total`, 'total_ejemplares'],
      'total-socios': ['total_socios_activos', null, null],
      'total-prestamos': ['prestamos_activos', null, null],
      'total-vencidos': ['prestamos_vencidos', null, null],
    };
    try {
      // Un solo pedido para todo el panel. Antes se traian los listados
      // completos de libros y socios solo para hacerles .length, y la
      // tarjeta de prestamos tenia un 0 escrito a mano en el HTML.
      const e = await api.obtener('/catalogo/estadisticas');

      $('#total-libros').textContent = e.total_libros;
      $('#detalle-libros').textContent =
        `${e.total_ejemplares} ejemplares · ${e.ejemplares_disponibles} disponibles`;

      $('#total-socios').textContent = e.total_socios_activos;
      $('#detalle-socios').textContent = 'sin contar los dados de baja';

      $('#total-prestamos').textContent = e.prestamos_activos;
      $('#detalle-prestamos').textContent = 'ejemplares fuera de la biblioteca';

      $('#total-vencidos').textContent = e.prestamos_vencidos;
      $('#detalle-vencidos').textContent = e.prestamos_vencidos === 0
        ? 'todo al día'
        : 'pasaron la fecha de devolución';

      const tarjeta = $('#tarjeta-vencidos');
      if (tarjeta) tarjeta.classList.toggle('critica', e.prestamos_vencidos > 0);
    } catch (err) {
      $$('.metrica .valor').forEach(el => { el.textContent = '—'; });
      $$('.metrica .detalle').forEach(el => { el.textContent = 'sin datos'; });
      avisar(err.message, 'error', 0);
    }
  },
};

/* ==================================================================
   PAGINA: LIBROS
   ================================================================== */

const paginaLibros = {
  columnas: 8,

  async iniciar() {
    await Promise.all([
      poblarSelect($('#id_subgenero'), 'subgeneros', 'Elegí un subgénero…'),
      poblarSelect($('#id_editorial'), 'editoriales', 'Elegí una editorial…'),
      poblarSelect($('#filtro-subgenero'), 'subgeneros', 'Todos los subgéneros'),
      poblarSelect($('#filtro-autor'), 'autores', 'Todos los autores'),
      this.poblarAutores(),
    ]);

    const buscarConEspera = esperar(() => this.listar());
    $('#buscar-libro').addEventListener('input', buscarConEspera);
    $('#filtro-subgenero').addEventListener('change', () => this.listar());
    $('#filtro-autor').addEventListener('change', () => this.listar());
    $('#form-libro').addEventListener('submit', (e) => this.guardar(e));

    // Delegacion de eventos: un solo listener para toda la tabla, en vez de
    // un onclick="" incrustado en cada fila.
    $('#tabla-libros').addEventListener('click', (e) => {
      const boton = e.target.closest('button[data-accion]');
      if (!boton) return;
      const id = Number(boton.dataset.id);
      if (boton.dataset.accion === 'editar') this.editar(id);
      if (boton.dataset.accion === 'borrar') this.borrar(id);
    });

    this.listar();
  },

  async poblarAutores() {
    const select = $('#autores_ids');
    if (!select) return;
    try {
      const autores = await catalogos.traer('autores');
      select.innerHTML = autores
        .map(a => `<option value="${a.id}">${esc(a.nombre)}</option>`).join('');
    } catch { /* el aviso ya lo dio poblarSelect */ }
  },

  /** El filtrado lo hace la BASE, no el navegador. Antes se descargaba
   *  el catalogo entero y se filtraba con .filter() en JavaScript. */
  async listar() {
    const tbody = $('#tabla-libros tbody');
    filaCargando(tbody, this.columnas);

    const params = consulta({
      titulo: $('#buscar-libro').value.trim(),
      id_subgenero: $('#filtro-subgenero').value,
      id_autor: $('#filtro-autor').value,
      limite: 100,
    });

    try {
      const libros = await api.obtener(`/libros${params}`);
      contarEn('#contador-libros', libros.length, 'libro');

      if (libros.length === 0) {
        filaMensaje(tbody, this.columnas, 'No hay libros para mostrar',
          'Probá con otro término de búsqueda o cargá el primer libro con el formulario de arriba.');
        return;
      }

      tbody.innerHTML = libros.map(l => `
        <tr>
          <td class="numero">${l.id}</td>
          <td><strong>${esc(l.titulo)}</strong></td>
          <td>${esc(l.isbn || '—')}</td>
          <td>${esc(l.autores.map(a => `${a.apellido}, ${a.nombre}`).join(' · ') || 'Sin autor cargado')}</td>
          <td>${esc(l.editorial ? l.editorial.nombre : '—')}</td>
          <td>${esc(l.subgenero ? l.subgenero.nombre : '—')}</td>
          <td>${fechaLegible(l.fecha_publicacion)}</td>
          <td class="acciones">
            <button class="btn-chico" data-accion="editar" data-id="${l.id}">Editar</button>
            <button class="btn-chico btn-peligro" data-accion="borrar" data-id="${l.id}">Eliminar</button>
          </td>
        </tr>`).join('');
    } catch (err) {
      filaMensaje(tbody, this.columnas, 'No se pudo cargar el catálogo', err.message, true);
    }
  },

  async guardar(evento) {
    evento.preventDefault();
    const boton = evento.target.querySelector('button[type="submit"]');
    boton.disabled = true;
    boton.textContent = 'Guardando…';

    const seleccionados = Array.from($('#autores_ids').selectedOptions).map(o => Number(o.value));

    try {
      const creado = await api.crear('/libros', {
        titulo: $('#titulo').value.trim(),
        isbn: $('#isbn').value.trim() || null,
        id_subgenero: Number($('#id_subgenero').value),
        id_editorial: Number($('#id_editorial').value),
        fecha_publicacion: $('#fecha_publicacion').value,
        idioma: $('#idioma').value.trim() || 'Espanol',
        numero_edicion: $('#numero_edicion').value.trim() || '1',
        autores_ids: seleccionados,
      });
      avisar(`Se guardó "${creado.titulo}".`, 'exito');
      evento.target.reset();
      this.listar();
    } catch (err) {
      avisar(err.message, 'error', 8000);
    } finally {
      boton.disabled = false;
      boton.textContent = 'Guardar libro';
    }
  },

  /** La M de ABM: antes no existia ningun boton de editar en el sistema. */
  async editar(id) {
    let libro, subgeneros, editoriales;
    try {
      [libro, subgeneros, editoriales] = await Promise.all([
        api.obtener(`/libros/${id}`),
        catalogos.traer('subgeneros'),
        catalogos.traer('editoriales'),
      ]);
    } catch (err) {
      avisar(err.message, 'error');
      return;
    }

    const opciones = (items, sel) => items
      .map(i => `<option value="${i.id}" ${i.id === sel ? 'selected' : ''}>${esc(i.nombre)}</option>`)
      .join('');

    modal.abrir(`Editar «${libro.titulo}»`, `
      <div class="campo">
        <label for="m-titulo">Título</label>
        <input id="m-titulo" name="titulo" value="${esc(libro.titulo)}" required>
      </div>
      <div class="campo">
        <label for="m-isbn">ISBN</label>
        <input id="m-isbn" name="isbn" value="${esc(libro.isbn || '')}">
      </div>
      <div class="campo">
        <label for="m-subgenero">Subgénero</label>
        <select id="m-subgenero" name="id_subgenero">${opciones(subgeneros, libro.id_subgenero)}</select>
      </div>
      <div class="campo">
        <label for="m-editorial">Editorial</label>
        <select id="m-editorial" name="id_editorial">${opciones(editoriales, libro.id_editorial)}</select>
      </div>
      <div class="campo">
        <label for="m-fecha">Publicación</label>
        <input id="m-fecha" name="fecha_publicacion" type="date" value="${esc(libro.fecha_publicacion)}">
      </div>
      <div class="campo">
        <label for="m-edicion">Edición</label>
        <input id="m-edicion" name="numero_edicion" value="${esc(libro.numero_edicion)}">
      </div>`,
      async (datos) => {
        await api.editar(`/libros/${id}`, {
          titulo: datos.get('titulo').trim(),
          isbn: datos.get('isbn').trim() || null,
          id_subgenero: Number(datos.get('id_subgenero')),
          id_editorial: Number(datos.get('id_editorial')),
          fecha_publicacion: datos.get('fecha_publicacion'),
          numero_edicion: datos.get('numero_edicion').trim(),
        });
        avisar('Libro actualizado.', 'exito');
        this.listar();
      });
  },

  async borrar(id) {
    if (!confirm('¿Eliminar este libro del catálogo?\n\nSi tiene ejemplares cargados, la base lo va a impedir.')) return;
    try {
      await api.borrar(`/libros/${id}`);
      avisar('Libro eliminado.', 'exito');
      this.listar();
    } catch (err) {
      avisar(err.message, 'error', 8000);
    }
  },
};

/* ==================================================================
   PAGINA: SOCIOS
   ================================================================== */

const paginaSocios = {
  columnas: 7,

  async iniciar() {
    await poblarSelect($('#id_rango'), 'rangos', 'Elegí un rango…');

    const buscarConEspera = esperar(() => this.listar());
    $('#buscar-socio').addEventListener('input', buscarConEspera);
    $('#filtro-estado-socio').addEventListener('change', () => this.listar());
    $('#form-socio').addEventListener('submit', (e) => this.guardar(e));

    $('#tabla-socios').addEventListener('click', (e) => {
      const boton = e.target.closest('button[data-accion]');
      if (!boton) return;
      const id = Number(boton.dataset.id);
      const acciones = {
        editar: () => this.editar(id),
        baja: () => this.darDeBaja(id),
        reactivar: () => this.reactivar(id),
      };
      (acciones[boton.dataset.accion] || (() => {}))();
    });

    this.listar();
  },

  async listar() {
    const tbody = $('#tabla-socios tbody');
    filaCargando(tbody, this.columnas);

    const params = consulta({
      texto: $('#buscar-socio').value.trim(),
      solo_activos: $('#filtro-estado-socio').value === 'activos',
      limite: 100,
    });

    try {
      const socios = await api.obtener(`/socios${params}`);
      contarEn('#contador-socios', socios.length, 'socio');

      if (socios.length === 0) {
        filaMensaje(tbody, this.columnas, 'No hay socios para mostrar',
          'Cambiá el filtro o registrá el primer socio con el formulario de arriba.');
        return;
      }

      tbody.innerHTML = socios.map(s => {
        const activo = !s.fecha_baja;
        return `
        <tr>
          <td class="numero">${s.id}</td>
          <td><strong>${esc(s.apellido)}, ${esc(s.nombre)}</strong></td>
          <td>${esc(s.dni)}</td>
          <td>${esc(s.email)}</td>
          <td>${esc(s.telefono || '—')}</td>
          <td>
            <span class="insignia ${activo ? 'insignia-verde' : 'insignia-gris'}">
              ${activo ? 'Activo' : 'Baja ' + fechaLegible(s.fecha_baja)}
            </span>
          </td>
          <td class="acciones">
            <button class="btn-chico" data-accion="editar" data-id="${s.id}">Editar</button>
            ${activo
              ? `<button class="btn-chico btn-peligro" data-accion="baja" data-id="${s.id}">Dar de baja</button>`
              : `<button class="btn-chico" data-accion="reactivar" data-id="${s.id}">Reactivar</button>`}
          </td>
        </tr>`;
      }).join('');
    } catch (err) {
      filaMensaje(tbody, this.columnas, 'No se pudo cargar el padrón', err.message, true);
    }
  },

  async guardar(evento) {
    evento.preventDefault();
    const boton = evento.target.querySelector('button[type="submit"]');
    boton.disabled = true;
    boton.textContent = 'Guardando…';
    try {
      const creado = await api.crear('/socios', {
        nombre: $('#nombre').value.trim(),
        apellido: $('#apellido').value.trim(),
        dni: $('#dni').value.trim(),
        email: $('#email').value.trim(),
        telefono: $('#telefono').value.trim() || null,
        id_rango: Number($('#id_rango').value),
      });
      avisar(`Se registró a ${creado.apellido}, ${creado.nombre}.`, 'exito');
      evento.target.reset();
      this.listar();
    } catch (err) {
      avisar(err.message, 'error', 8000);
    } finally {
      boton.disabled = false;
      boton.textContent = 'Guardar socio';
    }
  },

  async editar(id) {
    let socio, rangos;
    try {
      [socio, rangos] = await Promise.all([
        api.obtener(`/socios/${id}`),
        catalogos.traer('rangos'),
      ]);
    } catch (err) {
      avisar(err.message, 'error');
      return;
    }

    modal.abrir(`Editar a ${socio.apellido}, ${socio.nombre}`, `
      <div class="campo">
        <label for="m-nombre">Nombre</label>
        <input id="m-nombre" name="nombre" value="${esc(socio.nombre)}" required>
      </div>
      <div class="campo">
        <label for="m-apellido">Apellido</label>
        <input id="m-apellido" name="apellido" value="${esc(socio.apellido)}" required>
      </div>
      <div class="campo">
        <label for="m-dni">DNI</label>
        <input id="m-dni" name="dni" value="${esc(socio.dni)}" required>
      </div>
      <div class="campo">
        <label for="m-email">Email</label>
        <input id="m-email" name="email" type="email" value="${esc(socio.email)}" required>
      </div>
      <div class="campo">
        <label for="m-telefono">Teléfono</label>
        <input id="m-telefono" name="telefono" value="${esc(socio.telefono || '')}">
      </div>
      <div class="campo">
        <label for="m-rango">Rango</label>
        <select id="m-rango" name="id_rango">
          ${rangos.map(r => `<option value="${r.id}" ${r.id === socio.id_rango ? 'selected' : ''}>${esc(r.nombre)}</option>`).join('')}
        </select>
        <span class="ayuda">El rango define cuántos libros puede llevarse y por cuántos días.</span>
      </div>`,
      async (datos) => {
        await api.editar(`/socios/${id}`, {
          nombre: datos.get('nombre').trim(),
          apellido: datos.get('apellido').trim(),
          dni: datos.get('dni').trim(),
          email: datos.get('email').trim(),
          telefono: datos.get('telefono').trim() || null,
          id_rango: Number(datos.get('id_rango')),
        });
        avisar('Socio actualizado.', 'exito');
        this.listar();
      });
  },

  async darDeBaja(id) {
    if (!confirm('¿Dar de baja a este socio?\n\nNo se borra: queda en la base con fecha de baja y se puede reactivar.')) return;
    try {
      await api.borrar(`/socios/${id}`);
      avisar('Socio dado de baja.', 'exito');
      this.listar();
    } catch (err) {
      avisar(err.message, 'error', 8000);
    }
  },

  async reactivar(id) {
    try {
      await api.crear(`/socios/${id}/reactivar`, {});
      avisar('Socio reactivado.', 'exito');
      this.listar();
    } catch (err) {
      avisar(err.message, 'error', 8000);
    }
  },
};

/* ==================================================================
   PAGINA: PRESTAMOS
   ================================================================== */

const paginaPrestamos = {
  columnas: 8,

  async iniciar() {
    await Promise.all([
      this.poblarSocios(),
      this.poblarLibros(),
    ]);

    // Cascada libro -> ejemplares disponibles de ESE libro.
    // Antes el formulario mandaba id_libro cuando la API espera id_ejemplar:
    // se presta una COPIA FISICA, no un titulo.
    $('#id_libro').addEventListener('change', () => this.cargarEjemplares());
    $('#filtro-estado').addEventListener('change', () => this.listar());
    $('#form-prestamo').addEventListener('submit', (e) => this.registrar(e));

    $('#tabla-prestamos').addEventListener('click', (e) => {
      const boton = e.target.closest('button[data-accion="devolver"]');
      if (boton) this.devolver(Number(boton.dataset.id));
    });

    this.listar();
  },

  async poblarSocios() {
    const select = $('#id_socio');
    try {
      // solo_activos: un socio dado de baja no puede retirar material.
      const socios = await api.obtener('/socios?solo_activos=true&limite=200');
      select.innerHTML = '<option value="">Elegí un socio…</option>' +
        socios.map(s => `<option value="${s.id}">${esc(s.apellido)}, ${esc(s.nombre)} — DNI ${esc(s.dni)}</option>`).join('');
    } catch (err) {
      select.innerHTML = '<option value="">No se pudo cargar</option>';
      avisar(`No se pudo cargar el padrón: ${err.message}`, 'error');
    }
  },

  async poblarLibros() {
    const select = $('#id_libro');
    try {
      const libros = await api.obtener('/libros?limite=200');
      select.innerHTML = '<option value="">Elegí un título…</option>' +
        libros.map(l => `<option value="${l.id}">${esc(l.titulo)}</option>`).join('');
    } catch (err) {
      select.innerHTML = '<option value="">No se pudo cargar</option>';
      avisar(`No se pudo cargar el catálogo: ${err.message}`, 'error');
    }
  },

  async cargarEjemplares() {
    const select = $('#id_ejemplar');
    const idLibro = $('#id_libro').value;
    const boton = $('#form-prestamo button[type="submit"]');

    if (!idLibro) {
      select.innerHTML = '<option value="">Elegí primero un título</option>';
      select.disabled = true;
      boton.disabled = true;
      return;
    }

    select.disabled = true;
    select.innerHTML = '<option value="">Buscando ejemplares…</option>';

    try {
      const ejemplares = await api.obtener(`/ejemplares/libro/${idLibro}?solo_disponibles=true`);
      if (ejemplares.length === 0) {
        select.innerHTML = '<option value="">No hay ejemplares disponibles de este título</option>';
        boton.disabled = true;
        return;
      }
      select.innerHTML = '<option value="">Elegí un ejemplar…</option>' +
        ejemplares.map(e => `<option value="${e.id}">${esc(e.codigo_inventario)}</option>`).join('');
      select.disabled = false;
      boton.disabled = false;
    } catch (err) {
      select.innerHTML = '<option value="">Error al buscar ejemplares</option>';
      avisar(err.message, 'error');
    }
  },

  async listar() {
    const tbody = $('#tabla-prestamos tbody');
    filaCargando(tbody, this.columnas);

    const filtro = $('#filtro-estado').value;
    const params = consulta({
      solo_activos: filtro === 'activos',
      solo_vencidos: filtro === 'vencidos',
      limite: 100,
    });

    try {
      let prestamos = await api.obtener(`/prestamos${params}`);
      // "Devueltos" no tiene filtro propio en la API; se deriva del resto.
      if (filtro === 'devueltos') prestamos = prestamos.filter(p => p.devuelto);

      contarEn('#contador-prestamos', prestamos.length, 'préstamo');

      if (prestamos.length === 0) {
        filaMensaje(tbody, this.columnas, 'No hay préstamos para mostrar',
          'Registrá uno con el formulario de arriba o cambiá el filtro.');
        return;
      }

      tbody.innerHTML = prestamos.map(p => {
        let insignia;
        if (p.devuelto) {
          insignia = `<span class="insignia insignia-gris">Devuelto ${fechaLegible(p.fecha_devolucion)}</span>`;
        } else if (p.vencido) {
          insignia = `<span class="insignia insignia-roja">Vencido · ${p.dias_atraso} día${p.dias_atraso === 1 ? '' : 's'}</span>`;
        } else {
          insignia = `<span class="insignia insignia-verde">En préstamo</span>`;
        }

        return `
        <tr>
          <td class="numero">${p.id}</td>
          <td><strong>${esc(p.socio_nombre || '—')}</strong></td>
          <td>${esc(p.libro_titulo || '—')}</td>
          <td><code>${esc(p.codigo_inventario || '—')}</code></td>
          <td>${fechaLegible(p.fecha_prestamo)}</td>
          <td>${fechaLegible(p.fecha_vencimiento)}</td>
          <td>${insignia}</td>
          <td class="acciones">
            ${p.devuelto
              ? '<span style="color: var(--text-muted);">—</span>'
              : `<button class="btn-chico" data-accion="devolver" data-id="${p.id}">Registrar devolución</button>`}
          </td>
        </tr>`;
      }).join('');
    } catch (err) {
      filaMensaje(tbody, this.columnas, 'No se pudieron cargar los préstamos', err.message, true);
    }
  },

  async registrar(evento) {
    evento.preventDefault();
    const boton = evento.target.querySelector('button[type="submit"]');
    boton.disabled = true;
    boton.textContent = 'Registrando…';

    try {
      // El vencimiento NO lo elige el usuario: lo calcula el backend con
      // los dias_prestamo del rango del socio. Antes el formulario pedia
      // una fecha que despues el servidor ignoraba.
      const p = await api.crear('/prestamos', {
        id_socio: Number($('#id_socio').value),
        id_ejemplar: Number($('#id_ejemplar').value),
      });
      avisar(`Préstamo registrado. Vence el ${fechaLegible(p.fecha_vencimiento)}.`, 'exito', 7000);
      evento.target.reset();
      $('#id_ejemplar').innerHTML = '<option value="">Elegí primero un título</option>';
      $('#id_ejemplar').disabled = true;
      this.listar();
      this.poblarLibros();
    } catch (err) {
      // Sin "modo demostración": si el servidor rechaza, se ve el rechazo.
      avisar(err.message, 'error', 9000);
    } finally {
      boton.disabled = false;
      boton.textContent = 'Registrar préstamo';
    }
  },

  /** Devolucion REAL contra la base. Antes esta funcion solo cambiaba un
   *  booleano en memoria y avisaba "registrada con exito" sin guardar nada:
   *  al recargar la pagina, la devolucion desaparecia. */
  async devolver(id) {
    if (!confirm('¿Registrar la devolución de este ejemplar?')) return;
    try {
      await api.crear(`/prestamos/${id}/devolucion`, {});
      avisar('Devolución registrada. El ejemplar vuelve a estar disponible.', 'exito');
      this.listar();
      this.poblarLibros();
    } catch (err) {
      avisar(err.message, 'error', 8000);
    }
  },
};

/* ==================================================================
   ARRANQUE
   ================================================================== */

const paginas = {
  inicio: paginaInicio,
  libros: paginaLibros,
  socios: paginaSocios,
  prestamos: paginaPrestamos,
};

document.addEventListener('DOMContentLoaded', async () => {
  const nombre = document.body.dataset.pagina;
  const pagina = paginas[nombre];
  if (!pagina) return;

  const vivo = await verificarServidor();
  if (!vivo) {
    avisar('El servidor no responde. Ejecutá "uvicorn server:app --reload" desde la carpeta backend.', 'error', 0);
    return;
  }
  pagina.iniciar();
});
