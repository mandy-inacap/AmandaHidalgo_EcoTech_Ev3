# EcoTech Solutions - Sistema de gestión de empleados (TI3021)

Aplicación de consola en Python (POO) con persistencia en SQLite. Implementa el diagrama UML final de la Unidad 1.
Base: entrega ES2 (Unidad 2). Avance EF03 (Unidad 3): consumo de servicios externos con acceso seguro.

## Estructura
- `dominio/`: clases del modelo (sin SQL) y excepciones propias.
- `repositorio/`: conexión y acceso a datos (todo el SQL, siempre parametrizado).
- `servicios/` (Unidad 3): clientes de APIs externas y servicio de autenticación.
- `datos/schema.sql`: tablas con llaves primarias y foráneas.
- `main.py`: menú por consola y demostración automática.

## Ejecución
1. `python -m venv venv` y activarlo (`venv\Scripts\activate` en Windows).
2. `pip install -r requirements.txt` (instala `requests`).
3. Copiar `.env.example` a `.env`.
4. `python main.py` para el menú, o `python main.py --demo` para la demostración automática.

## Unidad 3: servicios externos
- Opción 9: crear un empleado con credencial y perfil (Administrador, Analista o Invitado).
- Opción 11: iniciar sesión y consultar indicadores (mindicador.cl) o el clima (Open-Meteo).
- La clave se guarda con PBKDF2 + sal (`GestorCifrado`) y se valida con `Credencial.validarAcceso()`.
- El acceso se controla con los `Permiso` de cada `Perfil`; el perfil Invitado no puede consultar las APIs.
- Bloqueo de 5 minutos después de 3 intentos fallidos y mensaje de error genérico.
- Toda entrada pasa por `dominio/validaciones.py` (expresiones regulares y listas blancas) antes de llegar a la API.
- Las consultas quedan guardadas en la tabla `consulta_api`.
