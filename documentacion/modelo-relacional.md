# Modelo relacional — Sistema de Gestión Bibliotecaria

**Grupo 7.3** · TP de Base de Datos · Biblioteca barrial
Motor: MySQL 8.0+ · InnoDB · `utf8mb4`

Este documento cubre el punto "Diseño de la Base de Datos" de la consigna:
descripción de cada tabla, clave primaria, claves foráneas y tipo de dato de
cada campo. El script ejecutable está en `backend/database/schema.sql`.

---

## 1. Resumen del diseño

La base tiene **11 tablas**. Tres decisiones de modelado sostienen todo lo demás:

**Un libro no es un ejemplar.** `libro` guarda el *título* (Dune, con su ISBN,
su editorial y su fecha de publicación). `ejemplar` guarda cada *copia física*
que está en el estante, con su código de inventario y su estado. Lo que se
presta es un ejemplar, nunca un libro. Sin esta separación no se podría saber
cuál de las tres copias de Dune se llevó cada socio, ni cuántas quedan
disponibles.

**La política de préstamo es un dato, no código.** La tabla `rango` guarda
cuántos libros puede llevarse un socio y por cuántos días. Cambiar la política
de la biblioteca es un `UPDATE`, no modificar el programa.

**No se almacena nada que se pueda calcular.** No hay un campo
`cantidad_ejemplares` en `libro`, ni un `esta_prestado` en `ejemplar` que
duplique la información de `prestamos`, ni un `esta_vencido`. Todo eso se
deriva con consultas. Un dato derivado almacenado es un dato que tarde o
temprano queda desincronizado.

### Relaciones

| Relación | Cardinalidad | Cómo se implementa |
|---|---|---|
| género → subgénero | 1:N | FK `subgenero.id_genero` |
| grupo editorial → editorial | 1:N | FK `editorial.id_grupo_editorial` |
| subgénero → libro | 1:N | FK `libro.id_subgenero` |
| editorial → libro | 1:N | FK `libro.id_editorial` |
| **libro ↔ autor** | **N:M** | **tabla intermedia `libro_autor`** |
| libro → ejemplar | 1:N | FK `ejemplar.id_libro` |
| rango → socio | 1:N | FK `socio.id_rango` |
| socio → préstamo | 1:N | FK `prestamos.id_socio` |
| ejemplar → préstamo | 1:N | FK `prestamos.id_ejemplar` |

La única relación N:M es libro–autor: un libro puede tener varios autores
(*Cosmos*, de Sagan y Druyan) y un autor escribe varios libros. Se resuelve con
tabla intermedia y clave primaria compuesta, nunca con una FK simple.

---

## 2. Descripción de cada tabla

### `genero`
Clasificación de primer nivel del catálogo (Ficción, Ensayo, Infantil).

| Campo | Tipo | Nulo | Clave | Descripción |
|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | No | **PK** | Identificador |
| `nombre` | VARCHAR(100) | No | UNIQUE | Nombre del género |

*Por qué `nombre` es UNIQUE:* dos géneros con el mismo nombre serían el mismo género.

---

### `subgenero`
Clasificación de segundo nivel, siempre colgando de un género.

| Campo | Tipo | Nulo | Clave | Descripción |
|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | No | **PK** | Identificador |
| `nombre` | VARCHAR(100) | No | | Nombre del subgénero |
| `id_genero` | INT | No | **FK → `genero.id`** | Género al que pertenece |

- **FK:** `id_genero` → `genero(id)` · `ON DELETE RESTRICT` `ON UPDATE CASCADE`
- **UNIQUE compuesto** `(id_genero, nombre)`: puede haber "Cuento" en Ficción y
  "Cuento" en Infantil, pero no dos veces dentro del mismo género.
- *Por qué RESTRICT:* borrar un género que tiene subgéneros con libros
  encadenaría el borrado de medio catálogo. La base lo impide.

---

### `grupo_editorial`
Casa matriz que agrupa varios sellos (Grupo Planeta, Penguin Random House).

| Campo | Tipo | Nulo | Clave | Descripción |
|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | No | **PK** | Identificador |
| `nombre` | VARCHAR(100) | No | UNIQUE | Nombre del grupo |

---

### `editorial`
Sello editorial concreto (Minotauro, Emecé, Alfaguara).

| Campo | Tipo | Nulo | Clave | Descripción |
|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | No | **PK** | Identificador |
| `nombre` | VARCHAR(100) | No | | Nombre del sello |
| `direccion` | VARCHAR(255) | Sí | | Domicilio, si se conoce |
| `fecha_fundacion` | DATE | Sí | | Año de fundación, si se conoce |
| `id_grupo_editorial` | INT | No | **FK → `grupo_editorial.id`** | Grupo al que pertenece |

- **FK:** `id_grupo_editorial` → `grupo_editorial(id)` · RESTRICT / CASCADE
- **UNIQUE compuesto** `(id_grupo_editorial, nombre)`
- *Por qué `direccion` y `fecha_fundacion` son nulos:* son datos que la
  biblioteca puede no tener al cargar el sello. Obligarlos frenaría el alta.

---

### `autor`

| Campo | Tipo | Nulo | Clave | Descripción |
|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | No | **PK** | Identificador |
| `nombre` | VARCHAR(100) | No | | Nombre |
| `apellido` | VARCHAR(100) | No | | Apellido |
| `fecha_nacimiento` | DATE | Sí | | Fecha de nacimiento |
| `fecha_fallecimiento` | DATE | Sí | | Nulo si vive |
| `nacionalidad` | VARCHAR(60) | No | | Nacionalidad |

- **CHECK** `chk_autor_fechas`: `fecha_fallecimiento >= fecha_nacimiento`.
- *Por qué `fecha_nacimiento` admite nulo:* de muchos autores, sobre todo
  antiguos, no se conoce la fecha. Exigirla obligaría a inventar datos.
- *Por qué `fecha_fallecimiento` nulo significa "vive":* es la ausencia del
  hecho, no un dato faltante. No hace falta un campo `esta_vivo` aparte.

---

### `libro`
El **título**, no la copia física.

| Campo | Tipo | Nulo | Clave | Descripción |
|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | No | **PK** | Identificador |
| `titulo` | VARCHAR(255) | No | | Título |
| `isbn` | VARCHAR(20) | Sí | UNIQUE | ISBN sin guiones |
| `id_subgenero` | INT | No | **FK → `subgenero.id`** | Clasificación |
| `id_editorial` | INT | No | **FK → `editorial.id`** | Sello editor |
| `fecha_publicacion` | DATE | No | | Fecha de publicación |
| `idioma` | VARCHAR(50) | No | | Idioma de la edición |
| `numero_edicion` | VARCHAR(20) | No | | Número de edición |

- **FK:** `id_subgenero` → `subgenero(id)` · RESTRICT / CASCADE
- **FK:** `id_editorial` → `editorial(id)` · RESTRICT / CASCADE
- *Por qué `isbn` es VARCHAR y no numérico:* puede terminar en "X" como dígito
  verificador, y los ceros a la izquierda son significativos. Un tipo numérico
  los perdería.
- *Por qué `isbn` admite nulo siendo UNIQUE:* los libros viejos no tienen ISBN.
  MySQL permite varios `NULL` en una columna `UNIQUE`, así que la restricción
  sigue valiendo para los que sí lo tienen.
- *Por qué `numero_edicion` es VARCHAR:* en la práctica aparecen valores como
  "1ra revisada" o "2a corregida".

---

### `libro_autor`
Tabla intermedia que resuelve el N:M entre libros y autores. No tiene atributos
propios: existe únicamente para vincular.

| Campo | Tipo | Nulo | Clave | Descripción |
|---|---|---|---|---|
| `id_libro` | INT | No | **PK compuesta** · **FK → `libro.id`** | Libro |
| `id_autor` | INT | No | **PK compuesta** · **FK → `autor.id`** | Autor |

- **PK compuesta** `(id_libro, id_autor)`: impide que el mismo autor figure dos
  veces en el mismo libro, sin necesidad de un `id` propio.
- **FK:** ambas con `ON DELETE CASCADE`.
- *Por qué CASCADE y no RESTRICT como en el resto:* una fila de esta tabla no
  significa nada por sí sola. Si se borra el libro, el vínculo deja de tener
  sentido y se va con él.

---

### `ejemplar`
La **copia física** que está en el estante. Es lo que se presta.

| Campo | Tipo | Nulo | Clave | Descripción |
|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | No | **PK** | Identificador |
| `id_libro` | INT | No | **FK → `libro.id`** | Título del que es copia |
| `codigo_inventario` | VARCHAR(30) | No | UNIQUE | Etiqueta física (INV-0001) |
| `estado` | VARCHAR(20) | No | | `disponible`, `prestado`, `en_reparacion`, `baja` |
| `fecha_alta` | DATE | No | | Fecha de incorporación |

- **FK:** `id_libro` → `libro(id)` · RESTRICT / CASCADE
- **CHECK** `chk_ejemplar_estado`: `estado IN ('disponible','prestado','en_reparacion','baja')`.
  La lista cerrada vive en la base, no solo en el programa: si estuviera solo en
  Python, cualquiera podría escribir "prestadoo" entrando por phpMyAdmin.
- *Por qué RESTRICT al borrar un libro:* si tiene copias en el estante, el
  título no se puede eliminar del catálogo. La base bloquea la operación.

---

### `rango`
Categoría de socio que define la política de préstamo.

| Campo | Tipo | Nulo | Clave | Descripción |
|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | No | **PK** | Identificador |
| `nombre` | VARCHAR(100) | No | UNIQUE | Estándar, Premium |
| `max_prestamos` | INT | No | | Cuántos puede tener a la vez |
| `dias_prestamo` | INT | No | | Duración del préstamo en días |

- **CHECK** `chk_rango_valores`: ambos valores mayores a cero.

---

### `socio`

| Campo | Tipo | Nulo | Clave | Descripción |
|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | No | **PK** | Identificador |
| `nombre` | VARCHAR(100) | No | | Nombre |
| `apellido` | VARCHAR(100) | No | | Apellido |
| `dni` | VARCHAR(15) | No | UNIQUE | Documento |
| `email` | VARCHAR(150) | No | UNIQUE | Correo de contacto |
| `telefono` | VARCHAR(30) | Sí | | Teléfono |
| `id_rango` | INT | No | **FK → `rango.id`** | Categoría |
| `fecha_alta` | DATE | No | | Alta como socio |
| `fecha_baja` | DATE | Sí | | Nulo = socio activo |

- **FK:** `id_rango` → `rango(id)` · RESTRICT / CASCADE
- **CHECK** `chk_socio_fechas`: `fecha_baja >= fecha_alta`.
- *Por qué `dni` y `telefono` son VARCHAR:* no se hacen cuentas con ellos, y un
  tipo numérico perdería ceros a la izquierda, guiones y prefijos.
- **Baja lógica.** Un socio nunca se borra: se le carga `fecha_baja`. Si se
  borrara la fila, sus préstamos históricos quedarían huérfanos y se perderían
  las estadísticas que pide la consigna. `fecha_baja IS NULL` es la definición
  de "socio activo" en todo el sistema.

---

### `prestamos`
El hecho central: qué ejemplar se llevó qué socio y cuándo.

| Campo | Tipo | Nulo | Clave | Descripción |
|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | No | **PK** | Identificador |
| `id_socio` | INT | No | **FK → `socio.id`** | Quién se lo llevó |
| `id_ejemplar` | INT | No | **FK → `ejemplar.id`** | Qué copia se llevó |
| `fecha_prestamo` | DATE | No | | Fecha de retiro |
| `fecha_vencimiento` | DATE | No | | Fecha límite de devolución |
| `fecha_devolucion` | DATE | Sí | | Nulo = préstamo activo |
| `ejemplar_en_curso` | INT (generada) | Sí | UNIQUE | Columna técnica, ver abajo |

- **FK:** `id_socio` → `socio(id)` · RESTRICT / CASCADE
- **FK:** `id_ejemplar` → `ejemplar(id)` · RESTRICT / CASCADE
- **CHECK** `chk_prestamo_vencimiento`: `fecha_vencimiento >= fecha_prestamo`
- **CHECK** `chk_prestamo_devolucion`: `fecha_devolucion >= fecha_prestamo`

**Un préstamo está activo cuando `fecha_devolucion IS NULL`.** Esa es la
definición única en todo el sistema; no hay un campo booleano `devuelto` que
pueda contradecirla.

**Por qué `fecha_vencimiento` sí se almacena.** Podría calcularse como
`fecha_prestamo + rango.dias_prestamo`, pero sería un error: si la biblioteca
cambia la política de 14 a 21 días, todos los préstamos ya emitidos cambiarían
retroactivamente su vencimiento. La fecha es el compromiso congelado en el
momento del retiro, no una función del rango actual. Es un dato histórico, no
un derivado.

**La columna `ejemplar_en_curso`.** Es una columna generada:

```sql
ejemplar_en_curso INT
  GENERATED ALWAYS AS (IF(fecha_devolucion IS NULL, id_ejemplar, NULL)) STORED
```

Vale `id_ejemplar` mientras el préstamo está activo y `NULL` una vez devuelto.
Como MySQL admite muchos `NULL` en un índice `UNIQUE` pero no dos valores
iguales, la restricción `uq_prestamo_ejemplar_en_curso` **garantiza a nivel de
base que un ejemplar no pueda estar en dos préstamos activos al mismo tiempo**.
Antes esta regla se confiaba solo a una consulta previa en el código, que en
condiciones de concurrencia se puede colar.

---

## 3. Índices

Los índices no cambian el diseño: son optimización. Están elegidos mirando los
`WHERE` y `ORDER BY` que ejecuta la aplicación, no puestos por las dudas.

| Índice | Tabla | Para qué consulta |
|---|---|---|
| `idx_libro_titulo` | libro | `ORDER BY titulo` del catálogo |
| `ftx_libro_titulo` | libro | Búsqueda por texto (FULLTEXT) |
| `idx_libro_subgenero` | libro | Filtro por subgénero |
| `idx_libro_editorial` | libro | Filtro por editorial |
| `idx_socio_apellido_nombre` | socio | `ORDER BY apellido, nombre` del padrón |
| `idx_autor_apellido_nombre` | autor | Orden y búsqueda de autores |
| `idx_prestamos_ejemplar_activo` | prestamos | `id_ejemplar = ? AND fecha_devolucion IS NULL` |
| `idx_prestamos_socio_activo` | prestamos | `id_socio = ? AND fecha_devolucion IS NULL` |
| `idx_prestamos_vencimiento` | prestamos | Listado de vencidos del panel |
| `idx_ejemplar_libro_estado` | ejemplar | Copias disponibles de un título |

**Sobre las búsquedas por título.** Un índice B-tree **no puede usarse con
`LIKE '%texto%'`**, porque el comodín va adelante y el índice está ordenado por
el principio de la cadena. Por eso existe el índice `FULLTEXT`: para búsqueda
por substring hay que usar `MATCH ... AGAINST`. El `idx_libro_titulo` sigue
sirviendo, pero para el ordenamiento, no para el filtro.

**Sobre los índices compuestos.** Las dos consultas más frecuentes del sistema
combinan una FK con `fecha_devolucion IS NULL`. Un índice solo sobre
`fecha_devolucion` tiene baja selectividad (apenas dos valores distintos en la
práctica) y casi no ayuda; el compuesto, en cambio, resuelve la consulta entera.

---

## 4. Reglas de integridad, y dónde vive cada una

| Regla | Dónde se garantiza |
|---|---|
| Un ejemplar no puede estar en dos préstamos activos | **Base** (UNIQUE sobre columna generada) |
| El estado de un ejemplar es uno de cuatro valores | **Base** (CHECK) |
| Las fechas son coherentes entre sí | **Base** (CHECK) |
| DNI, email, ISBN y código de inventario no se repiten | **Base** (UNIQUE) |
| No se borra un libro con ejemplares | **Base** (FK RESTRICT) |
| Un socio no supera el máximo de préstamos de su rango | Aplicación (requiere leer `rango`) |
| Un socio dado de baja no puede retirar material | Aplicación |
| El vencimiento sale de `dias_prestamo` del rango | Aplicación |

El criterio: **todo lo que la base puede garantizar, lo garantiza la base.** Lo
que queda en la aplicación es lo que necesita consultar varias tablas para
decidir. Una regla que vive solo en el código se rompe apenas alguien entra por
phpMyAdmin.
