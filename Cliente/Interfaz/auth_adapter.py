"""
Adaptador de Autenticacion y Verificacion para la Interfaz del Cliente (Integrante 1).
Conecta login_view.py y signup_view.py con el repositorio JSON del Integrante 4
(Servidor/infraestructure/data/usuarios.json) sin modificar archivos ajenos.
Cumple con US-01, US-02 y US-03 (validaciones notorias, bcrypt, codigo de 6 digitos y SMTP opcional).
"""
from __future__ import annotations
import os
import json
import re
import socket
from pathlib import Path
from types import SimpleNamespace

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def _cargar_env_local() -> None:
    """
    Descripcion:
        Lee y carga variables de entorno desde el archivo .env ubicado en la raiz del
        proyecto si dicho archivo existe y las claves no estan previamente en os.environ.
    Entradas:
        Ninguna.
    Salidas:
        None: Actualiza el diccionario os.environ con las variables definidas en .env.
    Restricciones:
        Ignora lineas de comentario que inician con '#' y omite claves vacias.
    """
    env_file = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_file.exists():
        try:
            with open(env_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        if k in ("SERVER_HOST", "SERVER_PORT") and k not in os.environ:
                            os.environ[k] = v.strip().strip("'\"")
        except Exception:
            pass
def _pedir(action: str, timeout: float = 15, **datos) -> dict:
    """Abre una conexión corta al servidor, envía una acción y devuelve su respuesta."""
    host = os.getenv("SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("SERVER_PORT", "5555"))
    try:
        sock = socket.create_connection((host, port), timeout=5)
    except OSError:
        return {"ok": False, "msg": f"No se pudo conectar al servidor ({host}:{port})."}
    try:
        sock.settimeout(timeout)
        sock.sendall((json.dumps({"action": action, **datos}) + "\n").encode("utf-8"))
        buf = ""
        while True:
            try:
                rx = sock.recv(4096)
            except socket.timeout:
                return {"ok": False, "msg": "El servidor no respondió."}
            except OSError:
                return {"ok": False, "msg": "Conexión perdida con el servidor."}
            if not rx:
                return {"ok": False, "msg": "El servidor cerró la conexión."}
            buf += rx.decode("utf-8")
            while "\n" in buf:
                linea, buf = buf.split("\n", 1)
                try:
                    msg = json.loads(linea)
                except json.JSONDecodeError:
                    continue
                if "ok" in msg:
                    return msg
                if msg.get("tipo") == "error":
                    return {"ok": False, "msg": msg.get("mensaje", "Error del servidor.")}
                # bienvenida / estado de partida: se ignoran
    finally:
        sock.close()

_cargar_env_local()

# =============================================================================
# Documentacion de Clase: ClienteAuthAdapter
# Proposito:
#   Gestionar todas las reglas de negocio de registro de cuenta, generacion/envio
#   de codigos de verificacion de 6 digitos, recuperacion de contrasena olvidada (US-05),
#   inicio de sesion con hash bcrypt y validacion de perfiles de administrador
#   (Admin 1 y Admin 2) verificando que no esten ocupados en otro ordenador.
# Contenido:
#   - Atributos: repo (CompatibleJsonRepository), codigos_pendientes (dict[str, str]).
#   - Metodos: validar_formato_correo, validar_reglas_password, enviar_codigo_verificacion,
#     _intentar_envio_smtp, solicitar_codigo_recuperacion, restablecer_password,
#     registrar_y_verificar, verificar_usuario_en_uso e iniciar_sesion.
# =============================================================================
class ClienteAuthAdapter:
    def __init__(self, *args, **kwargs):
        pass

    @staticmethod
    def validar_formato_correo(email: str) -> bool:
        """
        Descripcion:
            Comprueba mediante expresion regular si una cadena cumple el formato estandar
            de correo electronico (usuario@dominio.extension).
        Entradas:
            email (str): Cadena de correo electronico a evaluar.
        Salidas:
            bool: True si el formato es valido; False en caso contrario.
        Restricciones:
            No permite espacios en blanco ni ausencia de '@' o punto en el dominio.
        """
        return bool(EMAIL_RE.match(email.strip().lower()))

    @staticmethod
    def validar_reglas_password(password: str) -> bool:
        """
        Descripcion:
            Verifica que la contrasena cumpla la politica de seguridad: longitud minima
            de 8 caracteres y presencia de al menos una letra y un digito numerico.
        Entradas:
            password (str): Contrasena en texto plano ingresada por el usuario.
        Salidas:
            bool: True si cumple todas las reglas; False si incumple alguna.
        Restricciones:
            password debe ser de tipo str.
        """
        return (
            len(password) >= 8
            and any(c.isdigit() for c in password)
            and any(c.isalpha() for c in password)
        )

    def enviar_codigo_verificacion(self, email: str, username: str) -> dict:
        """
        Descripcion:
            Valida la disponibilidad del correo y nombre de usuario, genera un codigo
            criptograficamente seguro de 6 digitos e intenta enviarlo por SMTP (o lo
            retorna en el mensaje de estado para verificacion inmediata).
        Entradas:
            email (str): Correo electronico del aspirante a registrarse.
            username (str): Nombre de usuario unico deseado.
        Salidas:
            dict: Diccionario con claves 'ok' (bool), 'msg' (str) y opcionalmente 'codigo' (str).
        Restricciones:
            Rechaza la solicitud si el usuario o correo estan vacios o si ya existen en usuarios.json.
        """
        email_clean = email.strip().lower()
        user_clean = username.strip()

        if not user_clean:
            return {"ok": False, "msg": "Debe ingresar un nombre de usuario antes de solicitar el codigo."}
        if not self.validar_formato_correo(email_clean):
            return {"ok": False, "msg": "Formato de correo invalido (ejemplo: usuario@gmail.com)."}
        return _pedir("request_code", email=email_clean, username=user_clean)

    def solicitar_codigo_recuperacion(self, email: str) -> dict:
        """
        Descripcion:
            Genera un codigo de recuperacion de 6 digitos para la cuenta asociada al correo
            indicado (US-05) y lo envia mediante correo SMTP sin exponerlo en pantalla.
        Entradas:
            email (str): Correo registrado en el sistema.
        Salidas:
            dict: Claves 'ok' (bool) y 'msg' (str).
        Restricciones:
            Falla si el correo no existe o si no tiene formato valido.
        """
        email_clean = email.strip().lower()
        if not self.validar_formato_correo(email_clean):
            return {"ok": False, "msg": "Formato de correo invalido (ejemplo: usuario@gmail.com)."}
        return _pedir("forgot", email=email_clean)

    def restablecer_password(
        self, email: str, codigo: str, nueva_pass: str, confirm_pass: str
    ) -> dict:
        """
        Descripcion:
            Valida el codigo de seguridad de 6 digitos, comprueba las politicas de contrasena
            y actualiza el hash bcrypt en usuarios.json (US-05).
        Entradas:
            email (str): Correo electronico de la cuenta.
            codigo (str): Codigo de 6 digitos recibido por correo.
            nueva_pass (str): Nueva contrasena en texto plano.
            confirm_pass (str): Confirmacion de la nueva contrasena.
        Salidas:
            dict: Claves 'ok' (bool) y 'msg' (str).
        Restricciones:
            Requiere minimo 8 caracteres, al menos una letra y un numero.
        """
        cod_clean = codigo.strip()

        if not cod_clean:
            return {"ok": False, "msg": "Ingrese el codigo de 6 digitos recibido en su correo."}
        if not nueva_pass or not confirm_pass:
            return {"ok": False, "msg": "Debe ingresar y confirmar su nueva contrasena."}
        if nueva_pass != confirm_pass:
            return {"ok": False, "msg": "Las contrasenas no coinciden."}
        if not self.validar_reglas_password(nueva_pass):
            return {"ok": False, "msg": "Contrasena debil: requiere minimo 8 caracteres, al menos una letra y un numero."}
        return _pedir("reset", email=email.strip().lower(), code=cod_clean, new_password=nueva_pass)

    def registrar_y_verificar(
        self,
        email: str,
        username: str,
        password: str,
        confirm_password: str,
        codigo_ingresado: str,
    ) -> dict:
        """
        Descripcion:
            Ejecuta todas las validaciones de registro (US-01 y US-02), comprueba la
            coincidencia del codigo de 6 digitos, genera el hash bcrypt de la contrasena
            y persiste la nueva Cuenta verificada en usuarios.json.
        Entradas:
            email (str): Correo electronico del usuario.
            username (str): Nombre de usuario elegido.
            password (str): Contrasena en texto plano.
            confirm_password (str): Confirmacion de la contrasena.
            codigo_ingresado (str): Codigo de 6 digitos introducido por el usuario.
        Salidas:
            dict: Resultado con claves 'ok' (bool), 'msg' (str) y 'cuenta' (Cuenta, si tuvo exito).
        Restricciones:
            Requiere haber generado previamente un codigo mediante enviar_codigo_verificacion.
        """
        email_clean = email.strip().lower()
        user_clean = username.strip()
        cod_clean = codigo_ingresado.strip()

        if not user_clean or not email_clean or not password or not confirm_password or not cod_clean:
            return {"ok": False, "msg": "Todos los campos y el codigo de verificacion son obligatorios."}
        if not self.validar_formato_correo(email_clean):
            return {"ok": False, "msg": "El formato del correo electronico no es valido."}
        if password != confirm_password:
            return {"ok": False, "msg": "Las contrasenas ingresadas no coinciden."}
        if not self.validar_reglas_password(password):
            return {"ok": False, "msg": "La contrasena debe tener minimo 8 caracteres e incluir letras y numeros."}
        resp = _pedir("register_confirm", email=email_clean, username=user_clean,
                      password=password, code=cod_clean)
        if resp.get("ok"):
            resp["cuenta"] = SimpleNamespace(
                email=email_clean, username=user_clean, verified=True
            )
        return resp 

    def verificar_usuario_en_uso(self, username: str, controller=None) -> bool:
        """
        Descripcion:
            Comprueba si un nombre de usuario (especialmente 'Admin 1' o 'Admin 2') ya se
            encuentra conectado desde otro ordenador en el estado de red TCP o en la sala local.
        Entradas:
            username (str): Nombre del perfil o usuario a consultar.
            controller (AppController | None): Controlador maestro con el estado de red actual.
        Salidas:
            bool: True si el usuario ya aparece activo en la red o sala; False si esta libre.
        Restricciones:
            Si controller es None, asume que no hay sesion remota activa y retorna False.
        """
        if controller is None:
            return False
        objetivo = username.strip().lower()

        # 1. Revisar lista de jugadores reportados en tiempo real por el servidor TCP
        estado_red = getattr(controller, "estado_partida_red", None)
        if isinstance(estado_red, dict):
            for jug in estado_red.get("jugadores", []):
                if str(jug.get("nombre", "")).strip().lower() == objetivo:
                    return True

        # 2. Revisar jugadores remotos presentes en la sala actual
        for jug in getattr(controller, "jugadores_sala", []):
            if not jug.get("es_local", False) and str(jug.get("nombre", "")).strip().lower() == objetivo:
                return True
        return False

    def iniciar_sesion(self, identificador: str, password: str, controller=None) -> dict:
        """
        Descripcion:
            Autentica las credenciales ingresadas contra las cuentas de administrador de prueba
            ('Admin 1' y 'Admin 2') o contra el archivo usuarios.json mediante bcrypt,
            verificando ademas que la cuenta no este ocupada en otro ordenador.
        Entradas:
            identificador (str): Nombre de usuario o correo electronico.
            password (str): Contrasena en texto plano ingresada por el usuario.
            controller (AppController | None): Instancia del controlador para validar sesiones activas.
        Salidas:
            dict: Diccionario con 'ok' (bool), 'msg' (str) y, en caso exitoso, 'username' y 'email'.
        Restricciones:
            Nunca expone la contrasena esperada en los mensajes de error devueltos al usuario.
        """
        ident = identificador.strip()
        ident_norm = ident.lower()
        for nombre, alias in (
            ("Admin 1", ("admin 1", "admin1", "admin1@arena.local")),
            ("Admin 2", ("admin 2", "admin2", "admin2@arena.local")),
        ):
            if ident_norm in alias:
                otro = "Admin 2" if nombre == "Admin 1" else "Admin 1"
                if password != "1234":
                    return {"ok": False, "msg": "ACCESO RECHAZADO: Contrasena de administrador incorrecta."}
                if self.verificar_usuario_en_uso(nombre, controller):
                    return {"ok": False, "msg": f"ACCESO RECHAZADO: '{nombre}' ya se encuentra conectado en otro ordenador. Seleccione {otro}."}
                return {"ok": True, "msg": f"Acceso concedido como {nombre}.",
                        "username": nombre, "email": f"{nombre.replace(' ', '').lower()}@arena.local"}

        resp = _pedir("login", email=ident, password=password)
        if not resp.get("ok"):
            return {"ok": False, "msg": f"ACCESO RECHAZADO: {resp.get('msg', 'Error de acceso.')}"}

        username = resp.get("username", ident)
        if self.verificar_usuario_en_uso(username, controller):
            return {"ok": False, "msg": f"ACCESO RECHAZADO: La cuenta '{username}' ya esta conectada en otro ordenador."}
        return {"ok": True, "msg": "Inicio de sesion exitoso.",
                "username": username, "email": resp.get("email", "")}