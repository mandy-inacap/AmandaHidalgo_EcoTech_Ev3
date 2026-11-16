from dominio.gestor_cifrado import GestorCifrado
from dominio.validaciones import clave_segura, nombre_usuario_valido


class Credencial:
    """Credencial de un Empleado (0..1), habilitada por un Perfil. Usa GestorCifrado."""

    def __init__(self, empleado, nombreUsuario, clave, perfil, habilitada=True, ya_cifrada=False):
        self.__nombreUsuario = nombre_usuario_valido(nombreUsuario)       # U3: validado y saneado
        if ya_cifrada:
            self.__claveCifrada = clave                          # viene desde la BD (ya es un hash)
        else:
            clave = clave_segura(clave)                          # U3: reglas de clave segura
            self.__claveCifrada = GestorCifrado.encriptar(clave)  # -claveCifrada : str
        self.__habilitada = habilitada                           # -habilitada : bool
        self.empleado = empleado
        self.perfil = perfil
        empleado._vincular_credencial(self)

    @property
    def nombreUsuario(self):
        return self.__nombreUsuario

    @property
    def claveCifrada(self):
        """Solo lectura: es el hash, nunca la clave en texto plano."""
        return self.__claveCifrada

    @property
    def habilitada(self):
        return self.__habilitada

    def validarAcceso(self, clave):
        return self.__habilitada and GestorCifrado.validar(clave, self.__claveCifrada)

    def actualizarClave(self, actual, nueva):
        if not self.validarAcceso(actual):
            return False
        self.__claveCifrada = GestorCifrado.encriptar(clave_segura(nueva))
        return True
