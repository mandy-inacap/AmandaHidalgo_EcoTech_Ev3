"""EcoTech Solutions - Sistema de gestión de empleados (consola).
Uso:  python main.py          menú interactivo
      python main.py --demo   demostración automática (base temporal en memoria)
Unidad 3: se agregan consultas a servicios externos (indicadores y clima) protegidas con inicio de sesión."""
import sys
from datetime import date
from getpass import getpass

from dominio import (AccesoDenegadoError, Credencial, Departamento, DatoInvalidoError, EcoTechError, Empleado,
                     ErrorServicioExterno, Perfil, ParteDiario, Permiso, Proyecto, ParticipacionProyecto,
                     RegistroDuplicadoError, ReporteExcel, ReportePDF)
from dominio.validaciones import ciudad_valida, fecha_consulta_valida, indicador_valido, monto_valido
from repositorio import ConexionBD, ConsultaRepositorio, DepartamentoRepositorio, EmpleadoRepositorio
from servicios import (MODULO_CLIMA, MODULO_INDICADORES, PERMISOS_POR_PERFIL, ClienteClima, ClienteIndicadores,
                       ServicioAutenticacion, crear_perfil)


# ---------- Entradas de usuario con validación ----------

def pedir_texto(mensaje, obligatorio=True):
    while True:
        valor = input(mensaje).strip()
        if valor or not obligatorio:
            return valor
        print("  Este dato es obligatorio.")


def pedir_entero(mensaje):
    while True:
        try:
            return int(input(mensaje))
        except ValueError:
            print("  Ingresa un número entero válido.")


def pedir_decimal(mensaje):
    while True:
        try:
            return float(input(mensaje).replace(",", "."))
        except ValueError:
            print("  Ingresa un número válido (ej: 1500000).")


def pedir_fecha(mensaje):
    while True:
        try:
            return date.fromisoformat(input(mensaje).strip())
        except ValueError:
            print("  Fecha inválida. Usa el formato AAAA-MM-DD (ej: 2024-04-01).")


# ---------- Acciones del menú ----------

def registrar_empleado(repo_emp, repo_dep):
    empleado = Empleado(pedir_entero("Id: "), pedir_texto("Nombre completo: "),
                        pedir_texto("Dirección: ", False), pedir_texto("Teléfono: ", False),
                        pedir_texto("Correo: "), pedir_decimal("Sueldo base: "),
                        pedir_fecha("Fecha de ingreso (AAAA-MM-DD): "))
    codigo = pedir_texto("Código de departamento (Enter para ninguno): ", False)
    if codigo:
        empleado.cambiarDepartamento(repo_dep.obtener_por_codigo(int(codigo)))
    repo_emp.guardar(empleado)
    print("Empleado registrado.")


def listar_empleados(repo_emp):
    empleados = repo_emp.listar_activos()
    if not empleados:
        print("No hay empleados registrados.")
    for e in empleados:
        print(" ", e)


def buscar_empleado(repo_emp):
    print(repo_emp.obtener_por_id(pedir_entero("Id a buscar: ")))


def actualizar_empleado(repo_emp):
    empleado = repo_emp.obtener_por_id(pedir_entero("Id del empleado a actualizar: "))
    print("Actual:", empleado)
    empleado.sueldoBase = pedir_decimal("Nuevo sueldo base: ")
    repo_emp.actualizar(empleado)
    print("Empleado actualizado.")


def eliminar_empleado(repo_emp):
    repo_emp.eliminar(pedir_entero("Id del empleado a eliminar: "))
    print("Empleado eliminado.")


def crear_departamento(repo_dep):
    repo_dep.guardar(Departamento(pedir_entero("Código: "), pedir_texto("Nombre: ")))
    print("Departamento creado.")


def listar_departamentos(repo_dep):
    deptos = repo_dep.listar()
    if not deptos:
        print("No hay departamentos registrados.")
    for d in deptos:
        print(" ", d)


def eliminar_departamento(repo_dep):
    repo_dep.eliminar(pedir_entero("Código del departamento a eliminar: "))
    print("Departamento eliminado.")


def registrar_con_credencial(repo_emp):
    empleado = Empleado(pedir_entero("Id: "), pedir_texto("Nombre completo: "), "", "",
                        pedir_texto("Correo: "), pedir_decimal("Sueldo base: "),
                        pedir_fecha("Fecha de ingreso (AAAA-MM-DD): "))
    usuario = pedir_texto("Nombre de usuario: ")
    clave = getpass("Clave (8+ caracteres, mayúscula, minúscula y número): ")   # no se muestra en pantalla
    if clave != getpass("Repite la clave: "):
        print("Las claves no coinciden.")
        return
    perfiles = list(PERMISOS_POR_PERFIL)
    etiqueta = pedir_texto(f"Perfil ({', '.join(perfiles)}): ").capitalize()
    if etiqueta not in perfiles:
        raise DatoInvalidoError("Perfil no válido.")
    repo_emp.registrar_con_credencial(empleado, Credencial(empleado, usuario, clave, crear_perfil(etiqueta)))
    print("Empleado y credencial registrados.")


# ---------- Unidad 3: consultas a servicios externos (requieren sesión) ----------

def iniciar_sesion(auth):
    print("\nINICIO DE SESIÓN")
    credencial = auth.iniciarSesion(input("Usuario: "), getpass("Clave: "))
    print(f"Bienvenido/a {credencial.empleado.nombreCompleto} - perfil {credencial.perfil.etiqueta}")


def consultar_indicador(auth, api, repo_con):
    auth.verificarPermiso(MODULO_INDICADORES)
    indicador = indicador_valido(input("Indicador (dolar, euro, uf, utm): "))
    fecha = input("Fecha dd-mm-aaaa (Enter para el último valor): ").strip()
    fecha = fecha_consulta_valida(fecha) if fecha else None
    dato = api.obtenerIndicador(indicador, fecha)
    print(f"{dato['indicador']} al {dato['fecha']}: ${dato['valor']:,.2f}")
    repo_con.registrar(auth.sesion.nombreUsuario, "Indicadores", f"{indicador} {fecha or 'hoy'}",
                       f"{dato['valor']:.2f}")


def convertir_dolares(auth, api, repo_con):
    auth.verificarPermiso(MODULO_INDICADORES)
    monto = monto_valido(input("Monto en dólares: "))
    total, dato = api.convertirAPesos(monto, "dolar")
    print(f"US$ {monto:,.2f} = ${total:,} CLP (dólar a ${dato['valor']:,.2f} el {dato['fecha']})")
    repo_con.registrar(auth.sesion.nombreUsuario, "Conversión", f"US$ {monto}", f"${total} CLP")


def consultar_clima(auth, api, repo_con):
    auth.verificarPermiso(MODULO_CLIMA)
    c = api.obtenerClima(ciudad_valida(input("Ciudad: ")))
    print(f"Clima en {c['ciudad']}, {c['region']} ({c['pais']}) - {c['hora']}")
    print(f"  {c['descripcion']} | {c['temperatura']} °C | humedad {c['humedad']} % | viento {c['viento']} km/h")
    repo_con.registrar(auth.sesion.nombreUsuario, "Clima", c["ciudad"], f"{c['temperatura']} °C {c['descripcion']}")


def ver_historial(auth, repo_con):
    filas = repo_con.ultimas_del_usuario(auth.sesion.nombreUsuario)
    if not filas:
        print("Aún no tienes consultas registradas.")
    for fecha_hora, servicio, parametro, resultado in filas:
        print(f"  {fecha_hora} | {servicio} | {parametro} -> {resultado}")


def menu_servicios(auth, repo_con):
    if auth.sesion is None:
        iniciar_sesion(auth)
    indicadores, clima = ClienteIndicadores(), ClienteClima()
    opciones = {
        "1": ("Consultar indicador económico", lambda: consultar_indicador(auth, indicadores, repo_con)),
        "2": ("Convertir dólares a pesos", lambda: convertir_dolares(auth, indicadores, repo_con)),
        "3": ("Consultar clima de una ciudad", lambda: consultar_clima(auth, clima, repo_con)),
        "4": ("Ver mis últimas consultas", lambda: ver_historial(auth, repo_con)),
    }
    while True:
        print(f"\n--- Servicios externos ({auth.sesion.nombreUsuario}) ---")
        for clave, (texto, _) in opciones.items():
            print(f" {clave}. {texto}")
        print(" 5. Cerrar sesión\n 0. Volver al menú principal")
        eleccion = input("Opción: ").strip()
        if eleccion == "0":
            return
        if eleccion == "5":
            auth.cerrarSesion()
            print("Sesión cerrada.")
            return
        if eleccion not in opciones:
            print("Opción no válida.")
            continue
        try:
            opciones[eleccion][1]()
        except (AccesoDenegadoError, DatoInvalidoError, ErrorServicioExterno) as error:
            print(f"  {error}")


# ---------- Demostración automática ----------

def titulo(texto):
    print(f"\n>>> {texto}")


def demostracion():
    bd = ConexionBD(":memory:")
    try:
        titulo("1. Conexión a la base de datos")
        print(f"Conexión exitosa a la base de datos (SQLite {bd.probar_conexion()}).")
        bd.inicializar_bd()
        repo_dep, repo_emp = DepartamentoRepositorio(bd), EmpleadoRepositorio(bd)

        titulo("2. CRUD de Departamento y Empleado")
        repo_dep.guardar(Departamento(1, "Sustentabilidad Industrial"))
        repo_dep.guardar(Departamento(2, "Recursos Humanos"))
        marcela = Empleado(1, "Marcela Iturra", "Av. Uno 123", "+56911111111",
                           "marcela@ecotech.cl", 1_500_000, date(2024, 4, 1))
        marcela.cambiarDepartamento(repo_dep.obtener_por_codigo(1))
        repo_emp.guardar(marcela)                                                    # Create
        repo_emp.guardar(Empleado(2, "Luis Pérez", "", "", "luis@ecotech.cl", 1_200_000, date(2023, 8, 15)))
        print("Listado:", *repo_emp.listar_activos(), sep="\n  ")                    # Read (lista)
        print("Búsqueda por id 1:", repo_emp.obtener_por_id(1))                      # Read (uno)
        marcela.sueldoBase = 1_650_000
        repo_emp.actualizar(marcela)                                                 # Update
        print("Sueldo actualizado:", repo_emp.obtener_por_id(1).sueldoBase)
        repo_emp.eliminar(2)                                                         # Delete (lógico)
        print("Activos tras eliminar el id 2:", [e.nombreCompleto for e in repo_emp.listar_activos()])
        repo_dep.eliminar(2)                                                         # Delete (físico)
        print("Departamentos:", [d.nombreDepto for d in repo_dep.listar()])

        titulo("3. Validaciones y manejo de errores (el programa no se interrumpe)")
        pruebas = [
            ("Sueldo negativo", lambda: Empleado(9, "Ana", "", "", "ana@ecotech.cl", -5, date(2024, 1, 1))),
            ("Correo inválido", lambda: Empleado(9, "Ana", "", "", "sin-arroba", 1000, date(2024, 1, 1))),
            ("Id repetido", lambda: repo_emp.guardar(Empleado(1, "Otro", "", "", "otro@ecotech.cl", 1000, date(2024, 1, 1)))),
            ("Empleado inexistente", lambda: repo_emp.obtener_por_id(999)),
        ]
        for nombre, accion in pruebas:
            try:
                accion()
            except EcoTechError as error:
                print(f"  {nombre}: {type(error).__name__} -> {error}")

        titulo("4. Prueba de inyección SQL con ' OR '1'='1")
        payload = "' OR '1'='1"
        resultado = repo_emp.buscar_por_nombre(payload)
        print(f"buscar_por_nombre({payload!r}) devolvió {len(resultado)} resultado(s): la consulta parametrizada "
              "trató el payload como un texto cualquiera.")
        print("Búsqueda legítima 'Marcela Iturra':", len(repo_emp.buscar_por_nombre("Marcela Iturra")), "resultado(s)")

        titulo("5. Transacción atómica (empleado + credencial)")
        ok = Empleado(10, "Jesús Capetillo", "", "", "jesus@ecotech.cl", 1_100_000, date(2025, 2, 1))
        repo_emp.registrar_con_credencial(ok, Credencial(ok, "jcapetillo", "Clave#2026", Perfil("Analista")))
        print("Caso éxito: empleado 10 guardado ->", repo_emp.obtener_por_id(10).nombreCompleto)
        malo = Empleado(11, "Roberto Gajardo", "", "", "roberto@ecotech.cl", 1_100_000, date(2025, 3, 1))
        try:
            repo_emp.registrar_con_credencial(malo, Credencial(malo, "jcapetillo", "Clave#2026", Perfil("Analista")))
        except RegistroDuplicadoError as error:
            print(f"Caso fallo: la 2ª escritura falló ({error})")
        try:
            repo_emp.obtener_por_id(11)
        except EcoTechError:
            print("Rollback comprobado: el empleado 11 NO quedó guardado (la BD sigue consistente).")

        titulo("6. Autenticación con la credencial guardada (la clave se almacena como hash)")
        cred = repo_emp.obtener_credencial("jcapetillo")
        print("Hash guardado:", cred.claveCifrada[:30] + "...")
        print("Clave correcta:", cred.validarAcceso("Clave#2026"), "| incorrecta:", cred.validarAcceso("otra"))

        titulo("7. Polimorfismo: una colección mixta de reportes")
        proyecto = Proyecto(1, "Huerta Urbana Conectada", "Sensores de riego", date(2025, 2, 1))
        ParticipacionProyecto(marcela, proyecto)
        ParteDiario(1, marcela, proyecto, date(2025, 4, 14), 6.5, "Calibración de sensores")
        try:
            ParteDiario(2, marcela, proyecto, date(2025, 4, 15), 30)
        except DatoInvalidoError as error:
            print("Parte diario inválido rechazado:", error)
        for reporte in (ReportePDF("horas por proyecto"), ReporteExcel("horas por proyecto")):
            texto = reporte.construir([marcela.departamento], [proyecto])
            print(f"  {type(reporte).__name__}.exportar() -> {len(reporte.exportar(texto))} bytes")

        titulo("8. Unidad 3: validación de entradas antes de consultar las APIs")
        entradas = [
            ("Ciudad con símbolos", lambda: ciudad_valida("Conce<script>")),
            ("Ciudad con ruta", lambda: ciudad_valida("../../etc")),
            ("Indicador fuera de la lista blanca", lambda: indicador_valido("bitcoin")),
            ("Fecha que no existe", lambda: fecha_consulta_valida("31-02-2025")),
            ("Fecha futura", lambda: fecha_consulta_valida("01-01-2099")),
            ("Monto negativo", lambda: monto_valido("-500")),
            ("Clave débil", lambda: Credencial(ok, "otro.usuario", "clave123", Perfil("Analista"))),
        ]
        for nombre, accion in entradas:
            try:
                accion()
            except DatoInvalidoError as error:
                print(f"  {nombre}: {error}")
        print("  Entrada limpia aceptada:", repr(ciudad_valida("  san   pedro de la paz ")))

        titulo("9. Unidad 3: inicio de sesión, bloqueo y permisos por perfil")
        auth = ServicioAutenticacion(repo_emp)
        invitado = Empleado(12, "Usuario Invitado", "", "", "invitado@ecotech.cl", 500_000, date(2025, 6, 1))
        repo_emp.registrar_con_credencial(invitado, Credencial(invitado, "invitado", "Visita2026", Perfil("Invitado")))
        for usuario, clave in (("jcapetillo", "Clave#2026"), ("invitado", "Visita2026")):
            cred = auth.iniciarSesion(usuario, clave)
            try:
                auth.verificarPermiso(MODULO_INDICADORES)
                print(f"  {usuario} ({cred.perfil.etiqueta}): puede consultar {MODULO_INDICADORES}")
            except AccesoDenegadoError as error:
                print(f"  {usuario}: {error}")
            auth.cerrarSesion()
        for intento in range(1, 5):
            try:
                auth.iniciarSesion("jcapetillo", "ClaveMala1")
            except AccesoDenegadoError as error:
                print(f"  Intento {intento} con clave incorrecta: {error}")
        try:
            auth.iniciarSesion("x' OR '1'='1", "a")
        except AccesoDenegadoError as error:
            print(f"  Usuario con inyección SQL: {error}")
    except EcoTechError as error:
        print(f"Error inesperado del sistema: {error}")
    finally:
        bd.cerrar()


# ---------- Menú interactivo ----------

def menu():
    bd = ConexionBD()
    try:
        bd.inicializar_bd()
        print(f"Conexión exitosa a la base de datos (SQLite {bd.probar_conexion()}) - {bd.ruta}")
    except EcoTechError as error:
        print(f"No se pudo iniciar el sistema: {error}")
        return
    repo_dep, repo_emp = DepartamentoRepositorio(bd), EmpleadoRepositorio(bd)
    repo_con, auth = ConsultaRepositorio(bd), ServicioAutenticacion(repo_emp)
    opciones = {
        "1": ("Registrar empleado", lambda: registrar_empleado(repo_emp, repo_dep)),
        "2": ("Listar empleados", lambda: listar_empleados(repo_emp)),
        "3": ("Buscar empleado por id", lambda: buscar_empleado(repo_emp)),
        "4": ("Actualizar sueldo de un empleado", lambda: actualizar_empleado(repo_emp)),
        "5": ("Eliminar empleado", lambda: eliminar_empleado(repo_emp)),
        "6": ("Crear departamento", lambda: crear_departamento(repo_dep)),
        "7": ("Listar departamentos", lambda: listar_departamentos(repo_dep)),
        "8": ("Eliminar departamento", lambda: eliminar_departamento(repo_dep)),
        "9": ("Registrar empleado con credencial (transacción)", lambda: registrar_con_credencial(repo_emp)),
        "10": ("Ejecutar demostración automática", demostracion),
        "11": ("Servicios externos: indicadores y clima (requiere iniciar sesión)",
               lambda: menu_servicios(auth, repo_con)),
    }
    try:
        while True:
            print("\n=== EcoTech Solutions ===")
            for clave, (texto, _) in opciones.items():
                print(f"{clave:>2}. {texto}")
            print(" 0. Salir")
            eleccion = input("Opción: ").strip()
            if eleccion == "0":
                break
            if eleccion not in opciones:
                print("Opción no válida.")
                continue
            try:
                opciones[eleccion][1]()
            except AccesoDenegadoError as error:
                print(f"Acceso denegado: {error}")
            except EcoTechError as error:
                print(f"No se pudo completar la operación: {error}")
            except ValueError as error:
                print(f"Dato inválido: {error}")
    except (KeyboardInterrupt, EOFError):
        print("\nSesión finalizada.")
    finally:
        bd.cerrar()


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demostracion()
    else:
        menu()
