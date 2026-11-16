"""Inicio de sesión y control de acceso usando las clases del UML: Credencial, Perfil y Permiso."""
from datetime import datetime, timedelta

from dominio import AccesoDenegadoError, DatoInvalidoError, EcoTechError, GestorCifrado, Perfil, Permiso
from dominio.validaciones import nombre_usuario_valido

# Módulos nuevos de la Unidad 3
MODULO_INDICADORES = "API Indicadores"
MODULO_CLIMA = "API Clima"

# Qué permisos agrupa cada perfil (Perfil 1 ◆── 1..* Permiso)
PERMISOS_POR_PERFIL = {
    "Administrador": [("consultar", MODULO_INDICADORES), ("consultar", MODULO_CLIMA), ("gestionar", "Empleados")],
    "Analista": [("consultar", MODULO_INDICADORES), ("consultar", MODULO_CLIMA)],
    "Invitado": [("ver", "Menú principal")],
}


def crear_perfil(etiqueta):
    """Arma el Perfil con sus Permisos. Un perfil desconocido queda sin permisos."""
    perfil = Perfil(etiqueta)
    for accion, modulo in PERMISOS_POR_PERFIL.get(etiqueta, []):
        perfil.incluirPermiso(Permiso(accion, modulo))
    return perfil


class ServicioAutenticacion:
    MAX_INTENTOS = 3
    MINUTOS_BLOQUEO = 5
    MENSAJE_ERROR = "Usuario o clave incorrectos."   # mismo mensaje siempre, para no dar pistas

    def __init__(self, repo_empleados):
        self._repo = repo_empleados
        self.__intentos = {}     # usuario -> [intentos fallidos, bloqueado hasta]
        self.__sesion = None     # Credencial del usuario conectado

    @property
    def sesion(self):
        return self.__sesion

    def iniciarSesion(self, nombre_usuario, clave):
        try:
            nombre_usuario = nombre_usuario_valido(nombre_usuario)
        except DatoInvalidoError:
            raise AccesoDenegadoError(self.MENSAJE_ERROR) from None
        if not isinstance(clave, str) or not clave or len(clave) > 64:
            raise AccesoDenegadoError(self.MENSAJE_ERROR)

        self._revisar_bloqueo(nombre_usuario)
        try:
            credencial = self._repo.obtener_credencial(nombre_usuario)
        except EcoTechError:
            GestorCifrado.encriptar(clave)   # se calcula igual un hash para que el tiempo de respuesta sea parecido
            self._registrar_fallo(nombre_usuario)
            raise AccesoDenegadoError(self.MENSAJE_ERROR) from None

        if not credencial.validarAcceso(clave):    # compara contra el hash PBKDF2 y revisa que esté habilitada
            self._registrar_fallo(nombre_usuario)
            raise AccesoDenegadoError(self.MENSAJE_ERROR)

        self.__intentos.pop(nombre_usuario, None)
        credencial.perfil = crear_perfil(credencial.perfil.etiqueta)
        self.__sesion = credencial
        return credencial

    def cerrarSesion(self):
        self.__sesion = None

    def verificarPermiso(self, modulo):
        """Validación de acceso: solo pasa si hay sesión y su perfil tiene un permiso para ese módulo."""
        if self.__sesion is None:
            raise AccesoDenegadoError("Debes iniciar sesión primero.")
        if not any(p.areaModulo == modulo for p in self.__sesion.perfil.permisos):
            raise AccesoDenegadoError(f"Tu perfil ({self.__sesion.perfil.etiqueta}) no tiene permiso para {modulo}.")

    def _revisar_bloqueo(self, usuario):
        _, bloqueado_hasta = self.__intentos.get(usuario, [0, None])
        if bloqueado_hasta and datetime.now() < bloqueado_hasta:
            minutos = int((bloqueado_hasta - datetime.now()).total_seconds() // 60) + 1
            raise AccesoDenegadoError(f"Cuenta bloqueada por intentos fallidos. Intenta en {minutos} minuto(s).")

    def _registrar_fallo(self, usuario):
        fallos, _ = self.__intentos.get(usuario, [0, None])
        fallos += 1
        if fallos >= self.MAX_INTENTOS:
            self.__intentos[usuario] = [0, datetime.now() + timedelta(minutes=self.MINUTOS_BLOQUEO)]
        else:
            self.__intentos[usuario] = [fallos, None]
