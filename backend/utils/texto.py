"""Normalización de texto para la carga por escritura libre.

Existe por las correcciones 4 y 5: la editorial, el género y los autores
ya no se eligen de una lista, se escriben. Si no se normaliza lo que
llega del formulario, la base termina con "  minotauro", "Minotauro " y
"Minotauro" como tres editoriales distintas.

Aclaración sobre mayúsculas y acentos: la comparación NO se hace acá.
La base usa la collation utf8mb4_unicode_ci, que ya trata "MINOTAURO",
"minotauro" y "Minotaurо" como el mismo valor al comparar. Acá solo se
limpian espacios, para que lo que se GUARDA quede prolijo.
"""

import re

_ESPACIOS = re.compile(r"\s+")

# Partículas que forman parte del apellido y no del nombre de pila.
# Sin esto, "Ursula K. Le Guin" se guardaría con apellido "Guin".
_PARTICULAS = {
    "de", "del", "la", "las", "los", "le", "van", "von",
    "da", "di", "dos", "san", "santa", "mac", "mc", "y",
}


def normalizar(texto: str | None) -> str | None:
    """Saca espacios de más. Devuelve None si no quedó nada."""
    if texto is None:
        return None
    limpio = _ESPACIOS.sub(" ", texto).strip()
    return limpio or None


def normalizar_obligatorio(texto: str | None, campo: str) -> str:
    """Igual que normalizar() pero exige que haya contenido."""
    limpio = normalizar(texto)
    if limpio is None:
        raise ValueError(f"El campo '{campo}' no puede estar vacío.")
    return limpio


def separar_lista(texto: str | None, separadores: str = ";\n") -> list[str]:
    """Parte un campo de texto en varios valores.

    Se corta por punto y coma (y por salto de línea), NO por coma: la
    coma queda libre para escribir "King, Stephen", que es como los
    bibliotecarios anotan los autores.

        >>> separar_lista("Sagan, Carl; Druyan, Ann")
        ['Sagan, Carl', 'Druyan, Ann']
    """
    limpio = normalizar(texto)
    if limpio is None:
        return []
    patron = "[" + re.escape(separadores) + "]"
    partes = (normalizar(parte) for parte in re.split(patron, limpio))
    return [parte for parte in partes if parte]


def separar_nombre_autor(texto: str) -> tuple[str, str]:
    """Convierte lo que se escribió en el input en (nombre, apellido).

    Acepta las dos formas que usa la gente:

        "King, Stephen"        -> ("Stephen", "King")     <- forma de ficha
        "Stephen King"         -> ("Stephen", "King")
        "Ursula K. Le Guin"    -> ("Ursula K.", "Le Guin")
        "Borges"               -> ("", "Borges")

    El nombre puede quedar vacío a propósito: la columna es
    NOT NULL DEFAULT '' justamente para que el UNIQUE (apellido, nombre)
    funcione cuando no se sabe el nombre de pila.
    """
    limpio = normalizar_obligatorio(texto, "autor")

    # Forma "Apellido, Nombre".
    if "," in limpio:
        apellido, _, nombre = limpio.partition(",")
        return normalizar(nombre) or "", normalizar_obligatorio(apellido, "autor")

    palabras = limpio.split(" ")
    if len(palabras) == 1:
        return "", palabras[0]

    # El apellido es la última palabra, más las partículas que la
    # preceden ("Le Guin", "de la Torre").
    corte = len(palabras) - 1
    while corte > 1 and palabras[corte - 1].lower().strip(".") in _PARTICULAS:
        corte -= 1

    return " ".join(palabras[:corte]), " ".join(palabras[corte:])
