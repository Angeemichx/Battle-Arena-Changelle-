"""
Adaptador de Autenticacion y Verificacion para la Interfaz del Cliente (Integrante 1).
Conecta login_view.py y signup_view.py con el repositorio JSON del Integrante 4
(Servidor/infraestructure/data/usuarios.json) sin modificar archivos ajenos.
Cumple con US-01, US-02 y US-03 (validaciones notorias, bcrypt, codigo de 6 digitos y SMTP opcional).
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
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


def _ahora() -> datetime:
    """
    Descripcion:
        Retorna la fecha y hora actual en tiempo universal coordinado (UTC) sin zona horaria
        para permitir comparaciones homogeneas entre marcas de expiracion.
    Entradas:
        Ninguna.
    Salidas:
        datetime: Instancia actual de datetime en UTC sin tzinfo.
    Restricciones:
        Ninguna.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass


_cargar_env_local()
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
                "msg": f"Codigo de verificacion enviado a {email_clean}. Revise su bandeja de entrada (y spam).",
            }
        return {
            "ok": False,
            "msg": (
                f"No se pudo enviar el codigo al correo {email_clean}.\n"
                "Verifique su conexion o que las credenciales SMTP esten en .env."
            ),
        }

    def _intentar_envio_smtp(
        self,
        destino: str,
        username: str,
        codigo: str,
        asunto: str = "Battle Arena Challenge - Codigo de Verificacion",
        cuerpo: str | None = None,
    ) -> bool:
        """
        Descripcion:
            Intenta enviar un correo real mediante el servidor SSL de Gmail usando las variables
            del archivo .env (SMTP_USER y SMTP_PASS) o variables de entorno.
        Entradas:
            destino (str): Direccion de correo del destinatario.
            username (str): Nombre del piloto para personalizar el cuerpo del mensaje.
            codigo (str): Codigo de 6 digitos a enviar.
            asunto (str): Asunto del correo.
            cuerpo (str | None): Cuerpo personalizado; si es None genera el mensaje de verificacion.
        Salidas:
            bool: True si el correo fue despachado con exito por SMTP; False si no hay
            credenciales configuradas o si ocurre un error de red.
        Restricciones:
            Usa un timeout maximo de 8 segundos para no congelar la interfaz grafica.
        """
        smtp_user = os.getenv("SMTP_USER", "").strip() or os.getenv("SMTP_EMAIL", "").strip()
        smtp_pass = os.getenv("SMTP_PASS", "").strip() or os.getenv("SMTP_PASSWORD", "").strip()
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
        smtp_port = int(os.getenv("SMTP_PORT", "465"))

        if not smtp_user or not smtp_pass:
            print("[SMTP] Falta SMTP_USER o SMTP_PASS en .env o entorno.", flush=True)
            return False
        try:
            msg = EmailMessage()
            msg["Subject"] = asunto
            msg["From"] = smtp_user
            msg["To"] = destino
            if cuerpo is None:
                cuerpo = (
                    f"Hola {username},\n\n"
                    f"Tu codigo de verificacion para Battle Arena Challenge es: {codigo}\n\n"
                    f"Este codigo expira en 15 minutos."
                )
            msg.set_content(cuerpo)
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=8) as server:
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            print(f"[SMTP] Correo enviado exitosamente a {destino} ({asunto})", flush=True)
            return True
        except Exception as e:
            print(f"[SMTP ERROR] Error enviando correo a {destino}: {e}", flush=True)
            return False

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

        with self.repo.lock:
            cuenta = self.repo._email(email_clean)
            if cuenta is None:
                return {"ok": False, "msg": "No existe ninguna cuenta registrada con este correo."}

            codigo = f"{secrets.randbelow(10**6):06d}"
            cuenta.reset_code = codigo
            cuenta.reset_expires = (_ahora() + timedelta(minutes=30)).isoformat()
            self.repo.save(cuenta)

        cuerpo = (
            f"Hola {cuenta.username},\n\n"
            f"Has solicitado restablecer tu contrasena en Battle Arena Challenge.\n"
            f"Tu codigo de seguridad de 6 digitos es: {codigo}\n\n"
            f"Este codigo expira en 30 minutos.\n"
            f"Si no solicitaste este cambio, puedes ignorar este mensaje de forma segura."
        )
        enviado = self._intentar_envio_smtp(
            destino=email_clean,
            username=cuenta.username,
            codigo=codigo,
            asunto="Battle Arena Challenge - Recuperar Contrasena",
            cuerpo=cuerpo,
        )
        if enviado:
            return {
                "ok": True,
                "msg": f"Codigo de recuperacion enviado a {email_clean}. Revise su bandeja de entrada (y spam).",
            }
        return {
            "ok": False,
            "msg": (
                f"No se pudo enviar el correo de recuperacion a {email_clean}.\n"
                "Verifique su conexion o que las credenciales SMTP esten en .env."
            ),
        }

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
        email_clean = email.strip().lower()
        cod_clean = codigo.strip()

        if not cod_clean:
            return {"ok": False, "msg": "Ingrese el codigo de 6 digitos recibido en su correo."}
        if not nueva_pass or not confirm_pass:
            return {"ok": False, "msg": "Debe ingresar y confirmar su nueva contrasena."}
        if nueva_pass != confirm_pass:
            return {"ok": False, "msg": "Las contrasenas no coinciden."}
        if not self.validar_reglas_password(nueva_pass):
            return {
                "ok": False,
                "msg": "Contrasena debil: requiere minimo 8 caracteres, al menos una letra y un numero.",
            }

        with self.repo.lock:
            cuenta = self.repo._email(email_clean)
            if (
                not cuenta
                or cuenta.reset_code != cod_clean
                or not cuenta.reset_expires
                or datetime.fromisoformat(cuenta.reset_expires) < _ahora()
            ):
                return {"ok": False, "msg": "Codigo invalido o expirado. Solicite uno nuevo."}

            cuenta.password_hash = bcrypt.hashpw(nueva_pass.encode(), bcrypt.gensalt()).decode()
            cuenta.reset_code = None
            cuenta.reset_expires = None
            self.repo.save(cuenta)

        return {"ok": True, "msg": "Contrasena restablecida con exito. Ya puede iniciar sesion."}

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
