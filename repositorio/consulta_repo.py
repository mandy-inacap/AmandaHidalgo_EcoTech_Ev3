from datetime import datetime

from repositorio.base_repo import BaseRepositorio


class ConsultaRepositorio(BaseRepositorio):
    """Historial de consultas a las APIs externas (persistencia local). SQL siempre con parámetros (?)."""

    def registrar(self, nombre_usuario, servicio, parametro, resultado):
        self._ejecutar("INSERT INTO consulta_api (fecha_hora, nombre_usuario, servicio, parametro, resultado) "
                       "VALUES (?, ?, ?, ?, ?)",
                       (datetime.now().isoformat(timespec="seconds"), nombre_usuario, servicio, parametro, resultado))

    def ultimas_del_usuario(self, nombre_usuario, cantidad=10):
        return self._consultar("SELECT fecha_hora, servicio, parametro, resultado FROM consulta_api "
                               "WHERE nombre_usuario = ? ORDER BY id DESC LIMIT ?", (nombre_usuario, cantidad))
