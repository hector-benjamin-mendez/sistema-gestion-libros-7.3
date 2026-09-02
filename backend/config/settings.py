"""Lee la configuración desde el archivo .env."""

import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

if not MYSQL_USER or not MYSQL_DATABASE:
    raise RuntimeError(
        "Faltan variables en el .env: MYSQL_USER y MYSQL_DATABASE son obligatorias."
    )

# quote_plus escapa caracteres especiales de la contraseña (@, /, #...)
DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{quote_plus(MYSQL_PASSWORD)}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
)

# --- Base de datos de pruebas (solo la usa pytest) ---
MYSQL_DATABASE_TEST = os.getenv("MYSQL_DATABASE_TEST", "biblioteca_test")

TEST_DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{quote_plus(MYSQL_PASSWORD)}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE_TEST}?charset=utf8mb4"
)
