"""Indicadores económicos de Chile (dólar, euro, UF y UTM) desde mindicador.cl."""
import os

from dominio.excepciones import ErrorServicioExterno
from dominio.validaciones import fecha_consulta_valida, indicador_valido, monto_valido
from servicios.cliente_api import ClienteAPI


class ClienteIndicadores(ClienteAPI):

    def __init__(self):
        super().__init__()
        self._url = os.environ.get("ECOTECH_URL_INDICADORES", "https://mindicador.cl/api")

    def obtenerIndicador(self, indicador, fecha=None):
        indicador = indicador_valido(indicador)
        url = f"{self._url}/{indicador}"                 # el indicador ya pasó por la lista blanca
        if fecha:
            url += "/" + fecha_consulta_valida(fecha)
        datos = self._get(url)

        # Antes de usar el JSON se revisa que traiga lo que esperamos
        if not isinstance(datos, dict) or not isinstance(datos.get("serie"), list):
            raise ErrorServicioExterno("La respuesta del indicador no tiene el formato esperado.")
        if not datos["serie"]:
            raise ErrorServicioExterno("No hay valor para esa fecha (puede ser fin de semana o feriado).")
        try:
            ultimo = datos["serie"][0]
            return {"indicador": str(datos.get("nombre", indicador)),
                    "unidad": str(datos.get("unidad_medida", "")),
                    "fecha": str(ultimo["fecha"])[:10],
                    "valor": float(ultimo["valor"])}
        except (KeyError, TypeError, ValueError):
            raise ErrorServicioExterno("Los datos del indicador vienen incompletos.") from None

    def convertirAPesos(self, monto, indicador="dolar"):
        monto = monto_valido(monto)
        dato = self.obtenerIndicador(indicador)
        return round(monto * dato["valor"]), dato
