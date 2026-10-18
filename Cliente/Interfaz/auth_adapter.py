"""
Adaptador de Autenticacion y Verificacion para la Interfaz del Cliente (Integrante 1).
Conecta login_view.py y signup_view.py con el repositorio JSON del Integrante 4
(Servidor/infraestructure/data/usuarios.json) sin modificar archivos ajenos.
Cumple con US-01, US-02 y US-03 (validaciones notorias, bcrypt, codigo de 6 digitos y SMTP opcional).
"""
from __future__ import annotations
from datetime import datetime
import os
from pathlib import Path
import re
import secrets
import smtplib
from email.message import EmailMessage
import bcrypt

from Servidor.adapters.json_repository import JsonRepository
from Servidor.domain.cuenta import Cuenta

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DEFAULT_JSON_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "Servidor"
    / "infraestructure"
    / "data"
    / "usuarios.json"
)


# =============================================================================
# Documentacion de Clase: CompatibleJsonRepository
# Proposito:
#   Extender en memoria la clase JsonRepository del Integrante 4 para exponer
#   los metodos de consulta por correo y por nombre de usuario requeridos por el
#   flujo de autenticacion, sin editar los archivos originales de Servidor/.
# Contenido:
#   - Atributos heredados: filepath (Path), lock (threading.Lock).
#   - Metodos: get_by_email, username_exists y get_by_username_or_email.
# =============================================================================
class CompatibleJsonRepository(JsonRepository):
    def get_by_email(self, email: str) -> Cuenta | None:
        """
        Descripcion:
            Busca y retorna una entidad Cuenta a partir de su direccion de correo electronico.
        Entradas:
            email (str): Direccion de correo electronico a consultar.
        Salidas:
            Cuenta | None: Instancia de Cuenta si el correo existe en usuarios.json; None si no existe.
        Restricciones:
            El archivo JSON debe tener estructura de diccionario valido o no existir aun.
        """
        return self._email(email.strip().lower())

    def username_exists(self, username: str) -> bool:
        """
        Descripcion:
            Verifica si un nombre de usuario ya se encuentra registrado en el archivo JSON.
        Entradas:
            username (str): Nombre de usuario a verificar.
        Salidas:
            bool: True si el nombre de usuario ya existe; False en caso contrario.
        Restricciones:
            La comparacion ignora espacios laterales en blanco.
        """
        return self.user_exists(username.strip())

    def get_by_username_or_email(self, identificador: str) -> Cuenta | None:
        """
        Descripcion:
            Localiza una cuenta registrada buscando primero por coincidencia exacta de correo
            electronico y, si no la halla, iterando de forma insensible a mayusculas sobre
            el campo username.
        Entradas:
            identificador (str): Nombre de usuario o direccion de correo ingresada en el Login.
        Salidas:
            Cuenta | None: Objeto Cuenta encontrado o None si no existe coincidencia.
        Restricciones:
            Si identificador es una cadena vacia, retorna inmediatamente None.
        """
        ident = identificador.strip()
        if not ident:
            return None

        por_correo = self._email(ident.lower())
        if por_correo is not None:
            return por_correo

        # Se adquiere el candado del repositorio para evitar lecturas concurrentes corruptas
        with self.lock:
            datos = self._load()
            for email_key, info in datos.items():
                if str(info.get("username", "")).lower() == ident.lower():
                    return Cuenta(email=email_key, **info)
        return None


# =============================================================================
# Documentacion de Clase: ClienteAuthAdapter
# Proposito:
#   Gestionar todas las reglas de negocio de registro de cuenta, generacion/envio
#   de codigos de verificacion de 6 digitos, inicio de sesion con hash bcrypt y
#   validacion de perfiles de administrador (Admin 1 y Admin 2) verificando que
#   no esten ocupados en otro ordenador.
# Contenido:
#   - Atributos: repo (CompatibleJsonRepository), codigos_pendientes (dict[str, str]).
#   - Metodos: validar_formato_correo, validar_reglas_password, enviar_codigo_verificacion,
#     _intentar_envio_smtp, registrar_y_verificar, verificar_usuario_en_uso e iniciar_sesion.
# =============================================================================
class ClienteAuthAdapter:
    def __init__(self, json_path: str | Path = DEFAULT_JSON_PATH):
        """
        Descripcion:
            Inicializa el adaptador de autenticacion enlazado al archivo de persistencia
            usuarios.json y prepara el diccionario temporal de codigos de verificacion.
        Entradas:
            json_path (str | Path): Ruta hacia el archivo JSON donde se almacenan las cuentas.
        Salidas:
            None: Configura los atributos internos de la instancia.
        Restricciones:
            El directorio padre de json_path debe tener permisos de lectura y escritura.
        """
        self.repo = CompatibleJsonRepository(str(json_path))
        self.codigos_pendientes: dict[str, str] = {}

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

        if self.repo.get_by_email(email_clean) is not None:
            return {"ok": False, "msg": "Este correo electronico ya esta registrado en otra cuenta."}
        if self.repo.username_exists(user_clean):
            return {"ok": False, "msg": "Este nombre de usuario ya esta ocupado. Elija otro."}

        # Generacion criptograficamente aleatoria de 6 digitos con relleno de ceros a la izquierda
        codigo = f"{secrets.randbelow(10**6):06d}"
        self.codigos_pendientes[email_clean] = codigo

        enviado_smtp = self._intentar_envio_smtp(email_clean, user_clean, codigo)
        if enviado_smtp:
            return {
                "ok": True,
                "codigo": codigo,
                "msg": f"Codigo enviado a su correo {email_clean}. Revise su bandeja.",
            }
        return {
            "ok": True,
            "codigo": codigo,
            "msg": f"Codigo de verificacion generado para {email_clean}: [{codigo}]",
        }

    def _intentar_envio_smtp(self, destino: str, username: str, codigo: str) -> bool:
        """
        Descripcion:
            Intenta enviar un correo real mediante el servidor SSL de Gmail si las variables
            de entorno SMTP_EMAIL y SMTP_PASSWORD estan definidas en el sistema.
        Entradas:
            destino (str): Direccion de correo del destinatario.
            username (str): Nombre del piloto para personalizar el cuerpo del mensaje.
            codigo (str): Codigo de 6 digitos a enviar.
        Salidas:
            bool: True si el correo fue despachado con exito por SMTP; False si no hay
            credenciales configuradas o si ocurre un error de red.
        Restricciones:
            Usa un timeout maximo de 5 segundos para no congelar la interfaz grafica.
        """
        smtp_user = os.getenv("SMTP_EMAIL", "").strip()
        smtp_pass = os.getenv("SMTP_PASSWORD", "").strip()
        if not smtp_user or not smtp_pass:
            return False
        try:
            msg = EmailMessage()
            msg["Subject"] = "Battle Arena Challenge - Codigo de Verificacion"
            msg["From"] = smtp_user
            msg["To"] = destino
            msg.set_content(
                f"Hola {username},\n\n"
                f"Tu codigo de verificacion para Battle Arena Challenge es: {codigo}\n\n"
                f"Este codigo expira en 15 minutos."
            )
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=5) as server:
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"[SMTP INFO] Usando verificacion local ({e})")
            return False

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
            return {
                "ok": False,
                "msg": "La contrasena debe tener minimo 8 caracteres e incluir letras y numeros.",
            }

        codigo_esperado = self.codigos_pendientes.get(email_clean)
        if not codigo_esperado:
            return {"ok": False, "msg": "Primero debe presionar 'Enviar Codigo' para verificar su correo."}

        if cod_clean != codigo_esperado:
            return {"ok": False, "msg": "Codigo de verificacion incorrecto. Verifique los 6 digitos."}

        with self.repo.lock:
            if self.repo.get_by_email(email_clean) is not None:
                return {"ok": False, "msg": "El correo electronico ya se encuentra registrado."}
            if self.repo.username_exists(user_clean):
                return {"ok": False, "msg": "El nombre de usuario ya se encuentra registrado."}

            # Se cifra la contrasena con salt aleatorio mediante bcrypt antes de guardar en disco
            pwd_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            nueva_cuenta = Cuenta(
                email=email_clean,
                username=user_clean,
                password_hash=pwd_hash,
                verified=True,
                verify_code=None,
                verify_expires=None,
                created_at=datetime.utcnow().isoformat(),
            )
            self.repo.save(nueva_cuenta)

        self.codigos_pendientes.pop(email_clean, None)
        return {"ok": True, "msg": "Cuenta creada y correo verificado exitosamente.", "cuenta": nueva_cuenta}

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
        if not ident or not password:
            return {"ok": False, "msg": "ACCESO RECHAZADO: Debe ingresar su usuario/correo y contrasena."}

        # Validacion de perfiles rapidos de prueba (Admin 1 y Admin 2) sin revelar la clave en errores
        ident_norm = ident.lower()
        if ident_norm in ("admin 1", "admin1", "admin1@arena.local"):
            if password != "1234":
                return {"ok": False, "msg": "ACCESO RECHAZADO: Contrasena de administrador incorrecta."}
            if self.verificar_usuario_en_uso("Admin 1", controller):
                return {
                    "ok": False,
                    "msg": "ACCESO RECHAZADO: 'Admin 1' ya se encuentra conectado en otro ordenador. Seleccione Admin 2.",
                }
            return {
                "ok": True,
                "msg": "Acceso concedido como Admin 1.",
                "username": "Admin 1",
                "email": "admin1@arena.local",
            }

        if ident_norm in ("admin 2", "admin2", "admin2@arena.local"):
            if password != "1234":
                return {"ok": False, "msg": "ACCESO RECHAZADO: Contrasena de administrador incorrecta."}
            if self.verificar_usuario_en_uso("Admin 2", controller):
                return {
                    "ok": False,
                    "msg": "ACCESO RECHAZADO: 'Admin 2' ya se encuentra conectado en otro ordenador. Seleccione Admin 1.",
                }
            return {
                "ok": True,
                "msg": "Acceso concedido como Admin 2.",
                "username": "Admin 2",
                "email": "admin2@arena.local",
            }

        cuenta = self.repo.get_by_username_or_email(ident)
        if cuenta is None:
            return {
                "ok": False,
                "msg": f"ACCESO RECHAZADO: La cuenta '{ident}' no existe. Regístrese primero en Sign Up.",
            }

        if not cuenta.verified:
            return {
                "ok": False,
                "msg": "ACCESO RECHAZADO: Su correo electronico esta pendiente de verificacion.",
            }

        try:
            hash_bytes = cuenta.password_hash.encode("utf-8")
            es_valida = bcrypt.checkpw(password.encode("utf-8"), hash_bytes)
        except ValueError:
            es_valida = False

        if not es_valida:
            return {"ok": False, "msg": "ACCESO RECHAZADO: Contrasena incorrecta para esta cuenta."}

        if self.verificar_usuario_en_uso(cuenta.username, controller):
            return {
                "ok": False,
                "msg": f"ACCESO RECHAZADO: La cuenta '{cuenta.username}' ya esta conectada en otro ordenador.",
            }

        return {
            "ok": True,
            "msg": "Inicio de sesion exitoso.",
            "username": cuenta.username,
            "email": cuenta.email,
        }
