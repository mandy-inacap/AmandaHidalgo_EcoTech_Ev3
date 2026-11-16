"""Clase base para consumir APIs externas con la librería requests."""
import os

import requests

from dominio.excepciones import ErrorServicioExterno
from repositorio.conexion import cargar_env


class ClienteAPI:
    """Lógica común a todos los clientes: hacer el GET, controlar errores y devolver el JSON.
    Los clientes hijos solo saben qué URL llamar y cómo leer su respuesta."""

    def __init__(self):
        cargar_env()   # las URL y el timeout se leen del .env, no van escritos en el código
        self._timeout = int(os.environ.get("ECOTECH_API_TIMEOUT", "10"))
        self._sesion = requests.Session()
        self._sesion.headers.update({"User-Agent": "EcoTechSolutions/1.0"})

    def _get(self, url, parametros=None):
        # Los parámetros van en params= para que requests los codifique:
        # el texto del usuario nunca se pega directo en la URL.
        try:
            respuesta = self._sesion.get(url, params=parametros, timeout=self._timeout)
            respuesta.raise_for_status()
        except requests.exceptions.Timeout:
            raise ErrorServicioExterno("El servicio externo no respondió a tiempo.") from None
        except requests.exceptions.ConnectionError:
            raise ErrorServicioExterno("No hay conexión con el servicio externo.") from None
        except requests.exceptions.HTTPError:
            raise ErrorServicioExterno(f"El servicio externo respondió con error {respuesta.status_code}.") from None
        try:
            return respuesta.json()
        except ValueError:
            raise ErrorServicioExterno("La respuesta del servicio no viene en formato JSON.") from None
