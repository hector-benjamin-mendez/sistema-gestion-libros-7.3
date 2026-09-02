"""
Punto de entrada de la API.

Levantar con:  uvicorn server:app --reload
Documentacion automatica en:  http://127.0.0.1:8000/docs

Cambios respecto de la version anterior:
  - Depends se importaba sin usarse.
  - habia dos redirecciones /libros -> /api/libros que parcheaban un sintoma
    (el front pegandole a la URL equivocada) en vez de la causa. Se sacaron:
    ademas chocaban conceptualmente con el StaticFiles montado en "/".
  - allow_origins=["*"] junto con allow_credentials=True es una combinacion
    invalida segun la especificacion de CORS y los navegadores la rechazan.
    Como el front se sirve desde el mismo origen, se listan origenes concretos.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from routes import catalogo, ejemplares, libros, prestamos, socios
from utils.error_handlers import register_exception_handlers

app = FastAPI(
    title="Sistema de Gestion Bibliotecaria",
    description="TP de Base de Datos - Biblioteca barrial. Grupo 7.3.",
    version="1.1.0",
)

# Origenes concretos: el front servido por este mismo server y el caso de
# abrir los HTML con Live Server durante el desarrollo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(libros.router)
app.include_router(socios.router)
app.include_router(ejemplares.router)
app.include_router(prestamos.router)
app.include_router(catalogo.router)


@app.get("/api/health", tags=["Sistema"])
def health_check():
    """Sirve para que el frontend avise si el servidor esta caido."""
    return {"status": "ok", "version": app.version}


# ---- Frontend estatico ----
# Se monta AL FINAL: si se montara antes, "/" se tragaria las rutas de la API.
RUTA_FRONTEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")

if os.path.isdir(RUTA_FRONTEND):
    @app.get("/", include_in_schema=False)
    def inicio():
        return FileResponse(os.path.join(RUTA_FRONTEND, "index.html"))

    app.mount("/", StaticFiles(directory=RUTA_FRONTEND, html=True), name="frontend")
