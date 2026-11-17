import re

from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password

NOMBRE_MIN_LETRAS = 3
NOMBRE_MAX = 150          
PASSWORD_MIN = 8

_CARACTERES_PERMITIDOS_NOMBRE = set(" -'’.")

_PARTICULAS = {"de", "del", "la", "las", "los", "y"}


def _capitalizar(texto):
    return texto[:1].upper() + texto[1:].lower()


def normalizar_nombre(nombre):#limpia espacios y deja cada palabra con inicial mayuscula
    palabras = " ".join((nombre or "").split()).split(" ")
    resultado = []
    for i, palabra in enumerate(palabras):
        if i > 0 and palabra.lower() in _PARTICULAS:
            resultado.append(palabra.lower())
            continue
        partes = re.split(r"([-'’.])", palabra)
        resultado.append("".join(_capitalizar(p) for p in partes))
    return " ".join(resultado)


def validar_nombre(nombre):
    nombre = normalizar_nombre(nombre)

    if not nombre:
        raise ValidationError("Ingresa un nombre.")

    if any(c.isdigit() for c in nombre):
        raise ValidationError("El nombre no puede contener números.")

    if any(not (c.isalpha() or c in _CARACTERES_PERMITIDOS_NOMBRE) for c in nombre):
        raise ValidationError(
            "El nombre solo puede contener letras, espacios, guiones y apóstrofes."
        )

    if sum(c.isalpha() for c in nombre) < NOMBRE_MIN_LETRAS:
        raise ValidationError(
            f"El nombre debe tener al menos {NOMBRE_MIN_LETRAS} letras."
        )

    if len(nombre) > NOMBRE_MAX:
        raise ValidationError(
            f"El nombre no puede superar los {NOMBRE_MAX} caracteres."
        )




def validar_password(password):
    validate_password(password)


def primer_error(validador, valor):
    try:
        validador(valor)
    except ValidationError as error:
        return error.messages[0]
    return None