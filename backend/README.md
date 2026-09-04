# Capa de acceso a datos — Sistema de Gestión Bibliotecaria

Responsable: Bautista Cerino.
Versión 2: rehecha sobre las correcciones del profesor.

> **Leer esto antes de tocar el backend o el frontend.** El modelo cambió
> de forma, no de detalle: `libro` ya no significa lo mismo que antes.
> Al final del archivo está lo que le toca adaptar a cada uno.

---

## 1. El cambio grande: qué es ahora cada tabla

| Concepto | Antes | Ahora |
|---|---|---|
| La OBRA ("IT", de Stephen King) | columna `titulo` dentro de `libro` | tabla **`titulo`** |
| La COPIA FÍSICA (el objeto de papel) | tabla `ejemplar` | tabla **`libro`** |
| El género | `genero` → `subgenero` → `libro` | `genero` → `titulo` |
| El idioma | texto libre en `libro` | tabla **`idioma`** |
| El estado de la copia | texto libre + CHECK | tabla **`estado`** |
| La autoría | `libro_autor` | **`titulo_autor`** (es de la obra) |

Se cayeron `ejemplar` y `subgenero`. Quedan **12 tablas**.

La regla para no perderse: **una fila de `libro` es una cosa que se puede
tocar, prestar y romper.** Si la biblioteca tiene tres copias de IT, hay
un `titulo` y tres `libro`.

---

## 2. Estructura

| Carpeta | Contenido |
|---|---|
| `config/` | Configuración y conexión a MySQL (sin cambios) |
| `models/` | Las 12 clases ORM |
| `repositories/` | Acceso a datos, un módulo por entidad |
| `utils/` | Excepciones propias y normalización de texto |
| `database/` | `schema.sql` (estructura) y `seed.sql` (datos de prueba) |
| `tests/` | 68 pruebas de la capa de datos |

---

## 3. Puesta en marcha

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # completar con las credenciales locales

# El script crea la base solo: no hace falta crearla a mano.
mysql -u root -p < database/schema.sql
mysql -u root -p < database/seed.sql

# Base de pruebas (misma estructura, otro nombre).
sed 's/\bbiblioteca\b/biblioteca_test/g' database/schema.sql | mysql -u root -p

pytest -v
```

En phpMyAdmin: importar `schema.sql` y después `seed.sql`, en ese orden.
El script tiene dos triggers, pero son de una sola sentencia (`SET`, sin
`BEGIN...END`), así que **no hace falta tocar el delimitador**.

Probado sobre MySQL 9 y sobre MariaDB 10.11, con `ONLY_FULL_GROUP_BY`
activado y desactivado. Las 68 pruebas pasan en las cuatro combinaciones.

---

## 4. Cómo usar la capa desde FastAPI

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from config.database import get_session
from repositories import titulo_repository

def listar_catalogo(db: Session = Depends(get_session)):
    return titulo_repository.listar_con_stock(db, texto="dune")
```

### El commit es tuyo

Los repositorios hacen `flush()`, nunca `commit()`. Eso permite que
varias operaciones formen una sola transacción:

```python
copias = libro_repository.alta_por_texto(db, titulo="IT", ...)
db.commit()     # una sola vez, al final
```

Si algo falla en el medio, `db.rollback()` deshace todo junto y no queda
el título creado sin sus copias.

---

## 5. Las correcciones, traducidas a funciones

### Corrección 4 y 5 — cargar por texto, sin listas de selección

Todo el alta de material entra por **una sola función**:

```python
libro_repository.alta_por_texto(
    db,
    titulo="IT",
    genero="Terror",
    autores="King, Stephen",       # varios: separados por ';'
    editorial="Plaza & Janés",
    idioma="Español",
    isbn="9788497596718",
    edicion="2",
    cantidad=3,                    # tres copias de una
)
```

No hay ni un id de por medio: todo llega escrito y la capa resuelve o
crea el título, el género, la editorial, el idioma y los autores.
Cargar de nuevo el mismo título **no duplica nada**, porque cada tabla
tiene `UNIQUE` en el nombre y la collation `utf8mb4_unicode_ci` hace que
"minotauro", "Minotauro" y "MINOTAURO" sean el mismo valor.

El parser de autores acepta las dos formas que usa la gente:

| Se escribe | Se guarda |
|---|---|
| `Stephen King` | nombre `Stephen`, apellido `King` |
| `King, Stephen` | nombre `Stephen`, apellido `King` |
| `Ursula K. Le Guin` | nombre `Ursula K.`, apellido `Le Guin` |
| `Borges` | nombre vacío, apellido `Borges` |

Para el autocompletado de los inputs (así no se escriben dos variantes
del mismo nombre):

```python
editorial_repository.sugerir(db, "plaz")   # -> Plaza & Janés
autor_repository.sugerir(db, "kin")        # -> King, Stephen
titulo_repository.sugerir(db, "it")        # -> IT
```

### Corrección 3 — control de cada unidad física

```python
# Se presta LA COPIA, no el título.
prestamo = prestamo_repository.prestar(db, id_socio=4, id_libro=9)

# Vuelve rota:
prestamo_repository.registrar_devolucion(
    db, prestamo.id,
    fecha_devolucion=date(2026, 8, 26),
    nombre_estado="dañado",
    observaciones="Volvió con la tapa arrancada.",
)

# Y se puede sancionar:
socio_repository.suspender_por_dias(db, 4, 30)
```

Después de eso, el sistema puede contestar las tres preguntas que antes
no podía:

```python
prestamo_repository.historial_de_copia(db, 9)
# -> quién tuvo esta copia y en qué estado la devolvió cada uno

prestamo_repository.devoluciones_en_mal_estado(db, id_socio=4)
# -> los antecedentes del socio, para justificar la suspensión

libro_repository.resumen_inventario(db)
# -> {'copias': 11, 'disponibles': 7, 'fuera_de_circulacion': 4}
```

`suspendido_hasta` **vence solo**: no hace falta ningún proceso que
limpie las suspensiones viejas.

```python
socio.puede_pedir_prestado()   # False si está de baja o suspendido hoy
```

---

## 6. Repositorios disponibles

Todos reciben la `session` como primer parámetro.

| Módulo | Funciones principales |
|---|---|
| `titulo_repository` | `obtener_o_crear_por_texto`, `crear`, `obtener_o_error`, `obtener_completo`, `listar`, **`listar_con_stock`**, `sugerir`, `contar`, `actualizar`, `asignar_autores`, `eliminar` |
| `libro_repository` | **`alta_por_texto`**, `crear`, `obtener_o_error`, `obtener_por_codigo`, `obtener_detallado`, `listar`, `disponibles_de_titulo`, `contar_por_estado`, `resumen_inventario`, `cambiar_estado`, `actualizar`, `eliminar` |
| `prestamo_repository` | **`prestar`**, **`registrar_devolucion`**, `crear`, `listar`, `historial_de_copia`, `devoluciones_en_mal_estado`, `activos_de_socio`, `contar_activos_de_socio`, `copia_esta_prestada`, `eliminar` |
| `socio_repository` | `crear`, `obtener_o_error`, `obtener_por_dni`, `obtener_por_email`, `listar`, `actualizar`, `dar_de_baja`, `reactivar`, **`suspender_por_dias`**, `levantar_suspension`, `esta_habilitado` |
| `estado_repository` | `resolver`, `obtener_o_error_por_nombre`, `listar(solo_prestables=)`, CRUD |
| `genero_repository`, `editorial_repository`, `autor_repository`, `idioma_repository` | CRUD + **`obtener_o_crear`** (por texto) + `sugerir` |
| `grupo_editorial_repository`, `rango_repository` | CRUD estándar |

`listar()` de cada repositorio acepta `limite` y `desplazamiento`: nunca
se devuelve la tabla entera.

---

## 7. Excepciones

Definidas en `utils/db_errors.py`. Todas heredan de `ErrorDeDatos`.

| Excepción | Cuándo ocurre | HTTP sugerido |
|---|---|---|
| `RegistroNoEncontrado` | Se pidió un id (o un estado) que no existe | 404 |
| `RegistroDuplicado` | Choca contra UNIQUE (dni, email, título, código) | 409 |
| `ViolacionDeIntegridad` | Referencia inexistente o borrado bloqueado por FK | 409 |
| `ReglaDeDatos` | Devolver dos veces, prestar una copia rota | 409 |
| `ValueError` | Campo no editable, texto vacío, cantidad inválida | 422 |

---

## 8. Lo que la base garantiza sola

No hay que acordarse de chequearlo desde Python:

| Garantía | Cómo |
|---|---|
| Una copia no puede estar en dos préstamos activos | Columna `libro_en_curso` + índice `UNIQUE`, mantenida por triggers |
| No hay dos títulos, géneros, editoriales o idiomas con el mismo nombre | `UNIQUE` en cada `nombre` |
| No hay dos copias con el mismo código de inventario | `UNIQUE (codigo_inventario)` |
| El mismo autor no entra dos veces | `UNIQUE (apellido, nombre)` |
| No se registra cómo volvió algo que todavía no volvió | `CHECK` en `prestamos` |
| Las fechas son coherentes | `CHECK` en `autor`, `socio` y `prestamos` |
| No se borra un título, una editorial o un estado en uso | `ON DELETE RESTRICT` |

---

## 9. Reglas de negocio que NO están acá

Son de la capa de servicios. Esta capa da los insumos:

| Regla | Insumo |
|---|---|
| Un socio no puede superar el límite de su rango | `contar_activos_de_socio()` vs `socio.rango.max_prestamos` |
| Un socio de baja o suspendido no puede pedir | `socio_repository.esta_habilitado()` |
| Cuántos días dura el préstamo | `socio.rango.dias_prestamo` (ya lo aplica `prestar()`) |
| Cuándo corresponde suspender y por cuánto | `devoluciones_en_mal_estado()` da los antecedentes |

`prestar()` sí verifica que el estado de la copia habilite el préstamo,
porque eso no es una regla de negocio sino coherencia de la tabla
`estado`.

---

## 10. Qué le toca adaptar a cada uno

**Héctor (FastAPI).** Los endpoints de catálogo cambian de forma:

- `/api/libros` ahora es el catálogo de **títulos** → `titulo_repository.listar_con_stock()`
- `/api/ejemplares` pasa a ser `/api/copias` (o `/api/libros/{id}/copias`) → `libro_repository`
- El POST de alta de material recibe **texto**, no ids → `libro_repository.alta_por_texto()`
- El POST de préstamo manda `id_libro` (la copia), ya no `id_ejemplar`
- La devolución recibe además el estado en el que volvió la copia
- `/api/catalogo/subgeneros` desaparece; se agregan `idiomas` y `estados`
- Nuevos: `/api/socios/{id}/suspender`, `/api/copias/{id}/historial`

`prestar()` y `registrar_devolucion()` ya dejan coherentes las dos tablas
en la misma transacción: alcanza con llamar y hacer `commit()`.

**Melany (HTML/CSS).** Los `<select>` de editorial y autores se
reemplazan por `<input type="text">` (corrección 5), idealmente con
`<datalist>` para el autocompletado. El formulario de alta necesita un
campo nuevo: **cantidad de copias**. La pantalla de libros pasa a ser dos
niveles: listado de títulos → detalle con las copias.

**Santiago (JavaScript).** Ya no hay que poblar los `<select>` de
editorial ni de autores. En su lugar: al tipear, pegarle a
`/api/catalogo/sugerencias?...` y llenar el `<datalist>`. El flujo de
préstamo es en cascada: se busca el título → se listan sus copias
disponibles → se elige el código de inventario.

---

## 11. Pruebas

```bash
pytest -v
```

68 pruebas, corren contra `biblioteca_test` y nunca contra `biblioteca`.
Cada una se ejecuta dentro de una transacción que se deshace al terminar.

| Archivo | Qué cubre |
|---|---|
| `test_modelos.py` | Las 12 tablas, relaciones en las dos puntas, varias copias con el mismo ISBN |
| `test_repositorios.py` | CRUD, buscadores, stock por título, códigos de inventario |
| `test_carga_por_texto.py` | Correcciones 4 y 5: parseo de nombres, alta por texto, no duplicar |
| `test_prestamos_y_errores.py` | Ciclo de préstamo, el caso de Augusto completo, errores traducidos |
