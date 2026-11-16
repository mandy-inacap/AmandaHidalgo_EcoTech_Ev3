"""Validaciones compartidas por todas las clases del dominio."""
import re
import unicodedata
from datetime import date, datetime

from dominio.excepciones import DatoInvalidoError


def texto_no_vacio(valor, campo):
    if not isinstance(valor, str) or not valor.strip():
        raise DatoInvalidoError(f"{campo} no puede estar vacío.")
    return valor.strip()


def entero_positivo(valor, campo):
    if isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0:
        raise DatoInvalidoError(f"{campo} debe ser un número entero mayor a 0.")
    return valor


def numero_positivo(valor, campo):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or valor <= 0:
        raise DatoInvalidoError(f"{campo} debe ser un número mayor a 0.")
    return float(valor)


def correo_valido(valor):
    valor = texto_no_vacio(valor, "El correo")
    usuario, _, dominio = valor.partition("@")
    if not usuario or "." not in dominio:
        raise DatoInvalidoError("El correo no tiene un formato válido (ej: nombre@dominio.cl).")
    return valor


def fecha_valida(valor, campo):
    if not isinstance(valor, date):
        raise DatoInvalidoError(f"{campo} debe ser una fecha.")
    return valor


# ---------- Unidad 3: validación y saneamiento de entradas (login y consultas a APIs) ----------

PATRON_USUARIO = re.compile(r"[a-z0-9._]{4,20}")
PATRON_CIUDAD = re.compile(r"[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ' -]{2,50}")
INDICADORES_PERMITIDOS = ("dolar", "euro", "uf", "utm")   # lista blanca de mindicador.cl


def limpiar_texto(valor):
    """Quita caracteres de control (saltos, tabulaciones, nulos) y espacios repetidos."""
    if valor is None:
        return ""
    valor = unicodedata.normalize("NFC", str(valor))
    valor = "".join(c for c in valor if unicodedata.category(c)[0] != "C")
    return " ".join(valor.split())


def nombre_usuario_valido(valor):
    valor = limpiar_texto(valor).lower()
    if not PATRON_USUARIO.fullmatch(valor):
        raise DatoInvalidoError("El nombre de usuario debe tener de 4 a 20 caracteres: letras, números, '.' o '_'.")
    return valor


def clave_segura(valor):
    """La clave no se limpia (cambiaría lo que escribió el usuario), solo se revisa."""
    if not isinstance(valor, str) or not valor:
        raise DatoInvalidoError("La clave no puede estar vacía.")
    if len(valor) < 8 or len(valor) > 64:
        raise DatoInvalidoError("La clave debe tener entre 8 y 64 caracteres.")
    if any(unicodedata.category(c)[0] == "C" for c in valor):
        raise DatoInvalidoError("La clave tiene caracteres no permitidos.")
    if not (re.search(r"[A-Z]", valor) and re.search(r"[a-z]", valor) and re.search(r"[0-9]", valor)):
        raise DatoInvalidoError("La clave debe tener al menos una mayúscula, una minúscula y un número.")
    return valor


def ciudad_valida(valor):
    valor = limpiar_texto(valor)
    if not PATRON_CIUDAD.fullmatch(valor):
        raise DatoInvalidoError("Ciudad inválida: usa solo letras y espacios (2 a 50 caracteres).")
    return valor


def indicador_valido(valor):
    valor = limpiar_texto(valor).lower()
    if valor not in INDICADORES_PERMITIDOS:
        raise DatoInvalidoError(f"Indicador no válido. Opciones: {', '.join(INDICADORES_PERMITIDOS)}.")
    return valor


def fecha_consulta_valida(valor):
    """Fecha para la API en formato dd-mm-aaaa: debe existir y no ser futura."""
    valor = limpiar_texto(valor)
    try:
        fecha = datetime.strptime(valor, "%d-%m-%Y").date()
    except ValueError:
        raise DatoInvalidoError("Fecha inválida. Usa el formato dd-mm-aaaa (ej: 05-11-2026).") from None
    if fecha > date.today():
        raise DatoInvalidoError("La fecha no puede ser futura.")
    if fecha.year < 2000:
        raise DatoInvalidoError("Solo hay datos desde el año 2000.")
    return fecha.strftime("%d-%m-%Y")


def monto_valido(valor):
    try:
        monto = float(limpiar_texto(valor).replace(",", "."))
    except ValueError:
        raise DatoInvalidoError("El monto debe ser un número.") from None
    if not 0 < monto <= 1_000_000_000:
        raise DatoInvalidoError("El monto debe ser mayor a 0 y menor a mil millones.")
    return monto
