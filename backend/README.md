# Capa de acceso a datos — Sistema de Gestion Bibliotecaria

Responsable: Bautista.
Estado: terminada. Lista para que se construya FastAPI encima.

## Que hay aca

| Carpeta | Contenido |
|---|---|
| `config/` | Configuracion y conexion a MySQL |
| `models/` | Las 11 clases ORM que mapean el diseno del PDF |
| `repositories/` | Funciones de acceso a datos, una por entidad |
| `utils/` | Excepciones propias de la capa de datos |
| `database/` | `schema.sql` (estructura) y `seed.sql` (datos de prueba) |
| `tests/` | Pruebas de la capa de datos |

## Puesta en marcha
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env # completar con las credenciales locales
mysql -u root -p -e "CREATE DATABASE biblioteca CHARACTER SET utf8mb4;"
mysql -u root -p biblioteca < database/schema.sql
mysql -u root -p biblioteca < database/seed.sql
## Como usar la capa desde FastAPI

`get_session()` esta pensada para inyeccion de dependencias:

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from config.database import get_session
from repositories import libro_repository

def listar_libros(db: Session = Depends(get_session)):
    return libro_repository.listar(db, titulo="dune")
```

## Regla importante: el commit es tuyo

Los repositorios hacen `flush()`, nunca `commit()`. Eso es intencional:
permite que varias operaciones formen una sola transaccion.

```python
# Ejemplo de orquestacion (capa de servicios — Hector)
prestamo = prestamo_repository.crear(db, ...)
ejemplar_repository.actualizar_estado(db, id_ejemplar, "prestado")
db.commit()   # una sola vez, al final
```

Si algo falla en el medio, `db.rollback()` deshace todo junto.

## Repositorios disponibles

Todos reciben la `session` como primer parametro.

| Modulo | Funciones principales |
|---|---|
| `libro_repository` | `crear`, `obtener_o_error`, `obtener_completo`, `obtener_por_isbn`, `listar` (filtros: titulo, subgenero, editorial, autor), `contar`, `actualizar`, `eliminar`, `asignar_autores` |
| `ejemplar_repository` | `crear`, `obtener_o_error`, `obtener_por_codigo`, `listar`, `disponibles_de_libro`, `contar_por_estado`, `actualizar_estado`, `actualizar`, `eliminar` |
| `socio_repository` | `crear`, `obtener_o_error`, `obtener_con_rango`, `obtener_por_dni`, `obtener_por_email`, `listar` (filtros: texto, rango, solo_activos), `actualizar`, `dar_de_baja`, `eliminar` |
| `prestamo_repository` | `crear`, `obtener_o_error`, `listar` (filtros: socio, ejemplar, solo_activos, vencidos_al), `activos_de_socio`, `contar_activos_de_socio`, `ejemplar_esta_prestado`, `registrar_devolucion`, `eliminar` |
| `genero_repository`, `subgenero_repository`, `grupo_editorial_repository`, `editorial_repository`, `autor_repository`, `rango_repository` | CRUD estandar: `crear`, `obtener_o_error`, `listar`, `contar`, `actualizar`, `eliminar` |

## Excepciones

Definidas en `utils/db_errors.py`. Todas heredan de `ErrorDeDatos`.

| Excepcion | Cuando ocurre | HTTP sugerido |
|---|---|---|
| `RegistroNoEncontrado` | Se pidio un id que no existe | 404 |
| `RegistroDuplicado` | Choca contra UNIQUE (dni, email, isbn, codigo_inventario) | 409 |
| `ViolacionDeIntegridad` | Referencia inexistente, o borrado bloqueado por FK | 409 / 422 |
| `ValueError` | Estado invalido o campo no editable | 422 |

## Reglas de negocio que NO estan implementadas aca

Corresponden a la capa de servicios. La capa de datos provee los insumos:

| Regla | Insumo disponible |
|---|---|
| Un socio no puede superar su limite de prestamos | `contar_activos_de_socio()` vs `socio.rango.max_prestamos` |
| Un ejemplar no puede prestarse dos veces a la vez | `ejemplar_esta_prestado()` |
| Calcular la fecha de vencimiento | `socio.rango.dias_prestamo` |
| Un socio dado de baja no puede pedir prestados | `socio.fecha_baja` |

Nota: la regla del ejemplar no se puede garantizar por constraint porque
MySQL no soporta indices parciales. Hay que consultarla antes de prestar.

## Estados de ejemplar

Lista cerrada, validada en `ejemplar_repository`:
`disponible`, `prestado`, `en_reparacion`, `baja`.

## Pruebas
pytest -v

Corren contra `biblioteca_test`, nunca contra `biblioteca`.
Cada test se ejecuta en una transaccion que se deshace al terminar.
