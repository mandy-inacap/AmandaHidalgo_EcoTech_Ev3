"""Clima actual por ciudad desde Open-Meteo (primero geocoding, luego el pronóstico)."""
import os

from dominio.excepciones import ErrorServicioExterno
from dominio.validaciones import ciudad_valida
from servicios.cliente_api import ClienteAPI

# Códigos WMO que entrega Open-Meteo (los más comunes)
DESCRIPCION_CLIMA = {
    0: "Despejado", 1: "Mayormente despejado", 2: "Parcialmente nublado", 3: "Nublado",
    45: "Neblina", 48: "Neblina con escarcha", 51: "Llovizna débil", 53: "Llovizna", 55: "Llovizna intensa",
    61: "Lluvia débil", 63: "Lluvia", 65: "Lluvia intensa", 71: "Nieve débil", 73: "Nieve",
    75: "Nieve intensa", 80: "Chubascos débiles", 81: "Chubascos", 82: "Chubascos fuertes", 95: "Tormenta",
}


class ClienteClima(ClienteAPI):

    def __init__(self):
        super().__init__()
        self._url_geo = os.environ.get("ECOTECH_URL_GEOCODING", "https://geocoding-api.open-meteo.com/v1/search")
        self._url_clima = os.environ.get("ECOTECH_URL_CLIMA", "https://api.open-meteo.com/v1/forecast")

    def buscarCiudad(self, ciudad):
        ciudad = ciudad_valida(ciudad)
        datos = self._get(self._url_geo, {"name": ciudad, "count": 1, "language": "es", "format": "json"})
        resultados = datos.get("results") if isinstance(datos, dict) else None
        if not resultados:
            raise ErrorServicioExterno(f"No se encontró la ciudad '{ciudad}'.")
        try:
            lugar = resultados[0]
            return {"nombre": str(lugar["name"]), "region": str(lugar.get("admin1", "")),
                    "pais": str(lugar.get("country", "")),
                    "latitud": float(lugar["latitude"]), "longitud": float(lugar["longitude"])}
        except (KeyError, TypeError, ValueError):
            raise ErrorServicioExterno("Los datos de la ciudad vienen incompletos.") from None

    def obtenerClima(self, ciudad):
        lugar = self.buscarCiudad(ciudad)
        datos = self._get(self._url_clima, {
            "latitude": lugar["latitud"], "longitude": lugar["longitud"],
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
            "timezone": "auto"})
        actual = datos.get("current") if isinstance(datos, dict) else None
        if not isinstance(actual, dict):
            raise ErrorServicioExterno("La respuesta del clima no tiene el formato esperado.")
        try:
            return {"ciudad": lugar["nombre"], "region": lugar["region"], "pais": lugar["pais"],
                    "hora": str(actual["time"]).replace("T", " "),
                    "temperatura": float(actual["temperature_2m"]),
                    "humedad": int(actual["relative_humidity_2m"]),
                    "viento": float(actual["wind_speed_10m"]),
                    "descripcion": DESCRIPCION_CLIMA.get(int(actual["weather_code"]), "Sin descripción")}
        except (KeyError, TypeError, ValueError):
            raise ErrorServicioExterno("Los datos del clima vienen incompletos.") from None
