# Sistema de Gestión Bibliotecaria

TP de Base de Datos — Grupo 7.3
Sistema de gestión para una biblioteca barrial: catálogo, padrón de socios y
control de préstamos sobre una base de datos relacional.

## Arquitectura

```
Navegador  ──HTTP/JSON──▶  FastAPI  ──SQLAlchemy──▶  MySQL
(HTML/CSS/JS)              (backend)                 (11 tablas)
```

El frontend no se conecta nunca a MySQL: habla solo con la API.

| Carpeta | Contenido |
|---|---|
| `backend/config/` | Configuración y conexión a MySQL |
| `backend/models/` | Las 11 clases ORM que mapean el diseño |
| `backend/repositories/` | Acceso a datos, un módulo por entidad |
| `backend/routes/` | Endpoints de la API |
| `backend/schemas/` | Contratos de entrada y salida (Pydantic) |
| `backend/utils/` | Excepciones propias y manejo de errores HTTP |
| `backend/database/` | `schema.sql` y `seed.sql` |
| `backend/tests/` | Pruebas de la capa de datos |
| `frontend/` | Las cuatro pantallas y el módulo `app.js` |
| `documentacion/` | Modelo relacional, tablas, PK, FK y tipos de dato |

## Puesta en marcha

```bash
# 1. Base de datos
mysql -u root -p < backend/database/schema.sql
mysql -u root -p biblioteca < backend/database/seed.sql

# 2. Entorno de Python
cd backend
python3 -m venv venv
source venv/bin/activate          # en Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Credenciales
cp .env.example .env               # completar con el usuario y clave locales

# 4. Levantar el servidor
uvicorn server:app --reload
```

Abrir **http://127.0.0.1:8000** — el mismo servidor sirve el frontend y la API.
La documentación automática de los endpoints está en **/docs**.

Requiere MySQL 8.0 o superior: el esquema usa restricciones `CHECK` y una
columna generada.

## Pruebas

```bash
cd backend
mysql -u root -p -e "CREATE DATABASE biblioteca_test CHARACTER SET utf8mb4;"
mysql -u root -p biblioteca_test < database/schema.sql
pytest
```

## Endpoints

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/api/libros` | Listado y buscador (`titulo`, `id_subgenero`, `id_autor`) |
| GET | `/api/libros/{id}` | Un libro con sus autores y relaciones |
| POST | `/api/libros` | Alta |
| PUT | `/api/libros/{id}` | Modificación |
| DELETE | `/api/libros/{id}` | Baja |
| GET | `/api/socios` | Padrón y buscador (`texto`, `solo_activos`) |
| POST | `/api/socios` | Alta |
| PUT | `/api/socios/{id}` | Modificación |
| DELETE | `/api/socios/{id}` | Baja lógica |
| POST | `/api/socios/{id}/reactivar` | Deshace la baja |
| GET | `/api/ejemplares/libro/{id}` | Copias de un título (`solo_disponibles`) |
| POST | `/api/ejemplares` | Alta de una copia |
| GET | `/api/prestamos` | Listado (`solo_activos`, `solo_vencidos`, `id_socio`) |
| POST | `/api/prestamos` | Registra un préstamo |
| POST | `/api/prestamos/{id}/devolucion` | Registra la devolución |
| GET | `/api/catalogo/*` | Géneros, subgéneros, editoriales, autores, rangos |
| GET | `/api/catalogo/estadisticas` | Números del panel de inicio |

## Reglas de negocio

- Se presta un **ejemplar** (copia física), nunca un título.
- El vencimiento lo calcula el sistema con los `dias_prestamo` del rango del socio.
- Un socio no puede superar el `max_prestamos` de su rango.
- Un socio dado de baja no puede retirar material.
- Un ejemplar no puede estar en dos préstamos activos: lo garantiza la base.
- Un préstamo está activo cuando `fecha_devolucion IS NULL`.

## Convención de transacciones

Los repositorios hacen `flush()`, nunca `commit()`. El `commit()` lo hace la
ruta, una sola vez al final, para que varias operaciones formen una única
transacción:

```python
prestamo = prestamo_repository.crear(db, ...)
ejemplar_repository.actualizar_estado(db, id_ejemplar, "prestado")
db.commit()   # una sola vez
```

Así, si algo falla en el medio, no queda un ejemplar marcado como prestado sin
préstamo asociado.
