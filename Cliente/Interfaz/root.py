"""
Controlador Maestro de la Aplicacion (root).
Se mantiene vivo en segundo plano coordinando la navegacion,
el audio continuo, la persistencia local y el puente de red TCP sin duplicar ventanas.
"""
from __future__ import annotations
import json
import math
import socket
import struct
import sys
import threading
import wave
from pathlib import Path
import pygame

from Cliente.Interfaz.Components.ui_helpers import COLORES_AVATAR

CONFIG_PATH = Path(__file__).resolve().parent.parent / "Recursos" / "config_local.json"
AUDIO_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "Recursos" / "ambiente_espacial.wav"


def _asegurar_pista_espacial_default(ruta_wav: Path) -> None:
    """
    Descripcion:
        Verifica si existe el archivo de audio base en Cliente/Recursos/ y, en caso de no
        existir, sintetiza matematicamente un archivo .wav ambiental espacial para cumplir
        con CA-09.10 sin depender de recursos externos.
    Entradas:
        ruta_wav (Path): Ruta absoluta donde se verificara o creara el archivo .wav.
    Salidas:
        None: Escribe el archivo binario .wav en disco si no existia previamente.
    Restricciones:
        Requiere permisos de escritura en la carpeta Cliente/Recursos/.
    """
    if ruta_wav.exists():
        return
    try:
        ruta_wav.parent.mkdir(parents=True, exist_ok=True)
        sample_rate = 22050
        duracion_seg = 4
        n_samples = sample_rate * duracion_seg
        with wave.open(str(ruta_wav), "w") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            frames = bytearray()
            # Sintesis aditiva de un acorde ambiental (110Hz + 164.81Hz + 220Hz) con envolvente LFO
            for i in range(n_samples):
                t = i / float(sample_rate)
                envolvente = 0.85 + 0.15 * math.sin(2.0 * math.pi * 0.5 * t)
                onda = (
                    0.45 * math.sin(2.0 * math.pi * 110.0 * t)
                    + 0.35 * math.sin(2.0 * math.pi * 164.81 * t)
                    + 0.20 * math.sin(2.0 * math.pi * 220.0 * t)
                )
                valor = int(max(-32767, min(32767, onda * envolvente * 4500)))
                frames.extend(struct.pack("<h", valor))
            wav_file.writeframes(bytes(frames))
    except Exception as e:
        print(f"[AUDIO] No se pudo generar audio base: {e}")


# =============================================================================
# Documentacion de Clase: AppController
# Proposito:
#   Actuar como controlador central de la arquitectura hibrida (CustomTkinter + Pygame),
#   administrando la sesion del jugador, los parametros de la partida (tiempo y meta de
#   500 puntos), la reproduccion continua de musica en segundo plano, la persistencia
#   local en JSON y el puente de comunicacion por sockets TCP con el servidor.
# Contenido:
#   - Atributos principales: modo_estricto, auth_adapter, usuario_actual, avatar_color,
#     avatar_imagen, es_creador, mapa_seleccionado, tiempo_partida_min, puntos_meta (500),
#     jugadores_sala, ip_servidor, puerto_servidor, socket_cliente, estado_partida_red,
#     volumen_musica y ventana_actual.
#   - Metodos de configuracion y audio: _obtener_ip_local, obtener_nombre_color,
#     validar_color_disponible, cargar_config_local, guardar_config_local,
#     _iniciar_subsistema_audio y actualizar_volumen_audio.
#   - Metodos de red TCP: conectar_servidor_tcp, _escuchar_servidor, actualizar_estado_red,
#     enviar_movimiento_red, enviar_accion_red y enviar_configuracion_partida_red.
#   - Metodos de navegacion: ejecutar, _cerrar_ventana_actual, mostrar_login,
#     mostrar_admin_login, mostrar_signup, mostrar_recuperar_password, mostrar_hub,
#     mostrar_jugar, mostrar_perfil, mostrar_settings, volver_de_settings, entrar_al_lobby,
#     iniciar_arena y cerrar_aplicacion.
# =============================================================================
class AppController:
    def __init__(self, modo_estricto: bool = True):
        """
        Descripcion:
            Inicializa el estado global del cliente, carga la configuracion persistente
            de avatar y audio, e inicia la musica ambiental continua.
        Entradas:
            modo_estricto (bool): Indica si se aplican las restricciones estrictas (como
            exigir minimo 2 jugadores para despegar en el Lobby).
        Salidas:
            None: Configura todos los atributos de estado de la instancia.
        Restricciones:
            No abre ninguna ventana grafica hasta que se invoque explicitamente ejecutar().
        """
        self.modo_estricto = modo_estricto

        from Cliente.Interfaz.auth_adapter import ClienteAuthAdapter
        self.auth_adapter = ClienteAuthAdapter()

        # 1. Sesion del Jugador y Parametros de Partida (US-06 / US-08)
        self.usuario_actual = "Piloto"
        self.email_actual = ""
        self.avatar_color = "#E63946"  # Rojo por defecto
        self.avatar_imagen = None
        self.es_creador = False
        self.mapa_seleccionado = "Estacion Estandar"
        self.tiempo_partida_min = 3    # Duracion configurable en minutos (1, 3, 5)
        self.puntos_meta = 500         # Meta de puntos para ganar (por defecto 500 pts)
        self.tiempo_congelado_seg = 5  # Segundos de inmovilizacion (US-08)
        self.modo_fin = "tiempo"       # Forma de terminar: "tiempo" o "puntos" (CA-08.3)
        self.partida_en_curso = False  # Mientras sea True la configuracion queda bloqueada (CA-08.6)
        self.jugadores_sala = []
        self._cargar_configuracion_partida()

        # 2. Parametros y Puente de Red TCP
        self.ip_servidor = self._obtener_ip_local()
        self.puerto_servidor = 5555
        self.socket_cliente: socket.socket | None = None
        self.id_jugador_red: int | None = None
        self.estado_red_lock = threading.Lock()
        self.estado_partida_red: dict = {}
        self.acciones_remotas: dict[int, float] = {}

        # 3. Audio Persistente en Segundo Plano (CA-09.10)
        self.volumen_musica = 50
        self.cargar_config_local()
        self._iniciar_subsistema_audio()

        # 4. Referencia de la ventana activa (garantiza una sola ventana abierta a la vez)
        self.ventana_actual = None

    # ---- Configuracion de partida (US-08) --------------------------------
    def configuracion_partida(self):
        """Devuelve la configuracion vigente como ConfiguracionPartida (valida o lanza ConfiguracionInvalida)."""
        from Cliente.Config.configuracion import ConfiguracionPartida
        return ConfiguracionPartida(
            modo_fin=self.modo_fin,
            minutos=self.tiempo_partida_min,
            puntos_objetivo=self.puntos_meta,
            segundos_congelamiento=self.tiempo_congelado_seg,
        )

    def _cargar_configuracion_partida(self) -> None:
        """Carga la ultima configuracion guardada (CA-08.1). Ante cualquier fallo conserva los valores por defecto."""
        try:
            from Cliente.Config.config_repository import JsonConfiguracionRepository
            cfg = JsonConfiguracionRepository().cargar()
            self.modo_fin = cfg.modo_fin
            self.tiempo_partida_min = cfg.minutos
            self.puntos_meta = cfg.puntos_objetivo
            self.tiempo_congelado_seg = cfg.segundos_congelamiento
        except Exception as e:
            print(f"[CONFIG] No se pudo cargar la configuracion de partida: {e}")

    def guardar_configuracion_partida(self) -> bool:
        """Valida y persiste la configuracion actual. Devuelve False si no es valida o no se pudo guardar."""
        try:
            from Cliente.Config.config_repository import JsonConfiguracionRepository
            JsonConfiguracionRepository().guardar(self.configuracion_partida())
            return True
        except Exception as e:
            print(f"[CONFIG] No se pudo guardar la configuracion de partida: {e}")
            return False

    def configuracion_editable(self) -> bool:
        """La configuracion solo se puede cambiar antes de iniciar la partida (CA-08.6)."""
        return not self.partida_en_curso

    def _obtener_ip_local(self) -> str:
        """
        Descripcion:
            Detecta la direccion IPv4 de la interfaz de red activa del ordenador mediante
            un socket UDP sin enviar trafico real.
        Entradas:
            Ninguna.
        Salidas:
            str: Direccion IPv4 local detectada o '127.0.0.1' si no hay red disponible.
        Restricciones:
            No requiere conexion activa a Internet, pero devuelve loopback si falla el enrutamiento.
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def obtener_nombre_color(self, hex_color: str) -> str:
        """
        Descripcion:
            Traduce un codigo de color hexadecimal (#RRGGBB) a su nombre legible dentro
            del catalogo COLORES_AVATAR.
        Entradas:
            hex_color (str): Codigo hexadecimal del color a consultar.
        Salidas:
            str: Nombre del color ('Rojo', 'Azul', etc.); retorna 'Rojo' por defecto.
        Restricciones:
            La comparacion es insensible a mayusculas o minusculas.
        """
        for nombre, codigo in COLORES_AVATAR.items():
            if codigo.upper() == hex_color.upper():
                return nombre
        return "Rojo"

    def validar_color_disponible(self, hex_color: str, jugadores: list[dict]) -> bool:
        """
        Descripcion:
            Valida la regla de exclusion mutua de colores (CA-10.3), verificando que ningun
            otro jugador remoto en la sala tenga asignado el color solicitado.
        Entradas:
            hex_color (str): Codigo hexadecimal (#RRGGBB) que el jugador local desea elegir.
            jugadores (list[dict]): Lista de diccionarios de los jugadores presentes en la sala.
        Salidas:
            bool: True si el color esta libre; False si otro jugador ya lo ocupa.
        Restricciones:
            Ignora al propio jugador local (es_local == True) durante la validacion.
        """
        objetivo = hex_color.strip().upper()
        for j in jugadores:
            if not j.get("es_local", False) and str(j.get("color", "")).strip().upper() == objetivo:
                return False
        return True

    def resolver_conflicto_color(self, jugadores: list[dict]) -> str | None:
        """
        Descripcion:
            Detecta si el color actual del avatar del jugador local colisiona con el de
            algun otro jugador en la sala (CA-10.3). En caso de conflicto, reasigna
            automaticamente al jugador local el primer color disponible de COLORES_AVATAR.
        Entradas:
            jugadores (list[dict]): Lista de diccionarios de jugadores en la sala.
        Salidas:
            str | None: Nombre del nuevo color asignado si hubo conflicto, o None si no hubo colision.
        Restricciones:
            Modifica self.avatar_color si se detecta colision con un jugador remoto.
        """
        colores_otros = {
            str(j.get("color", "")).strip().upper()
            for j in jugadores
            if not j.get("es_local", False)
        }
        color_local_actual = str(self.avatar_color).strip().upper()

        if color_local_actual not in colores_otros:
            return None  # No hay conflicto, el color actual es unico

        # Conflicto detectado: reasignar al siguiente color libre de la paleta obligatoria
        for nombre, codigo in COLORES_AVATAR.items():
            if codigo.upper() not in colores_otros:
                self.avatar_color = codigo
                for j in jugadores:
                    if j.get("es_local", False):
                        j["color"] = codigo
                        j["color_nombre"] = nombre
                        break
                return nombre

        return None

    def cargar_config_local(self) -> None:
        """
        Descripcion:
            Lee el archivo Cliente/Recursos/config_local.json para restaurar las preferencias
            de color de avatar, ruta de imagen y volumen de musica del jugador.
        Entradas:
            Ninguna.
        Salidas:
            None: Actualiza los atributos avatar_color, avatar_imagen y volumen_musica.
        Restricciones:
            Si el archivo no existe o su JSON es invalido, conserva los valores por defecto.
        """
        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                self.avatar_color = datos.get("avatar_color", self.avatar_color)
                self.avatar_imagen = datos.get("avatar_imagen", self.avatar_imagen)
                self.volumen_musica = int(datos.get("volumen_musica", self.volumen_musica))
        except Exception:
            pass

    def guardar_config_local(self) -> None:
        """
        Descripcion:
            Persiste en Cliente/Recursos/config_local.json la configuracion actual de usuario,
            color de hitbox, imagen de avatar y volumen de musica (CA-06.4).
        Entradas:
            Ninguna.
        Salidas:
            None: Escribe el archivo JSON en disco.
        Restricciones:
            Requiere permisos de escritura en el directorio Cliente/Recursos/.
        """
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            datos = {
                "usuario": self.usuario_actual,
                "avatar_color": self.avatar_color,
                "avatar_imagen": self.avatar_imagen,
                "volumen_musica": self.volumen_musica,
            }
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(datos, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[CONFIG] No se pudo guardar config_local.json: {e}")

    def _iniciar_subsistema_audio(self) -> None:
        """
        Descripcion:
            Inicializa pygame.mixer, asegura la existencia de la pista de audio base y
            comienza su reproduccion en bucle infinito (-1) en segundo plano.
        Entradas:
            Ninguna.
        Salidas:
            None: Deja activo el canal musical de Pygame.
        Restricciones:
            Si el ordenador no cuenta con dispositivo de salida de audio, captura la
            excepcion para permitir que el juego funcione en modo silencioso.
        """
        try:
            _asegurar_pista_espacial_default(AUDIO_DEFAULT_PATH)
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.set_volume(self.volumen_musica / 100.0)
            recursos_dir = CONFIG_PATH.parent
            if recursos_dir.exists():
                for ext in ("*.ogg", "*.mp3", "*.wav"):
                    archivos = list(recursos_dir.glob(ext))
                    if archivos:
                        pygame.mixer.music.load(str(archivos[0]))
                        pygame.mixer.music.play(-1)
                        break
        except Exception as e:
            print(f"[AUDIO] Subsistema de audio no disponible: {e}")

    def actualizar_volumen_audio(self) -> None:
        """
        Descripcion:
            Aplica inmediatamente el nivel de volumen actual (0 a 100) al mezclador de
            musica de Pygame y guarda el cambio en config_local.json.
        Entradas:
            Ninguna.
        Salidas:
            None: Modifica el volumen del canal musical activo.
        Restricciones:
            volumen_musica debe encontrarse en el rango [0, 100].
        """
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.set_volume(self.volumen_musica / 100.0)
            self.guardar_config_local()
        except Exception:
            pass

    def conectar_servidor_tcp(self, host: str | None = None, port: int | None = None) -> bool:
        """
        Descripcion:
            Intenta abrir una conexion socket TCP hacia el servidor de juego y lanza un
            hilo daemon en segundo plano para escuchar paquetes JSON entrantes.
        Entradas:
            host (str | None): Direccion IP del servidor; si es None utiliza self.ip_servidor.
            port (int | None): Puerto TCP del servidor; si es None utiliza self.puerto_servidor.
        Salidas:
            bool: True si la conexion se establecio o ya estaba activa; False si el servidor
            no respondio dentro del timeout de 0.6 segundos.
        Restricciones:
            Usa un timeout corto (0.6s) al conectar para evitar bloquear la interfaz grafica
            cuando se prueba en modo local sin servidor encendido.
        """
        if self.socket_cliente is not None:
            return True
        target_host = host or self.ip_servidor
        target_port = port or self.puerto_servidor
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.6)
            sock.connect((target_host, int(target_port)))
            sock.settimeout(None)
            self.socket_cliente = sock
            hilo = threading.Thread(target=self._escuchar_servidor, daemon=True)
            hilo.start()
            return True
        except Exception:
            self.socket_cliente = None
            return False

    def _escuchar_servidor(self) -> None:
        """
        Descripcion:
            Bucle ejecutado en un hilo secundario que recibe flujos de bytes desde el socket
            TCP, reconstruye lineas delimitadas por '\\n' y decodifica cada paquete JSON.
        Entradas:
            Ninguna.
        Salidas:
            None: Invoca actualizar_estado_red por cada mensaje JSON recibido.
        Restricciones:
            Finaliza limpiamente cerrando la referencia socket_cliente si el servidor corta la conexion.
        """
        buffer = ""
        while self.socket_cliente is not None:
            try:
                datos = self.socket_cliente.recv(4096)
                if not datos:
                    break
                buffer += datos.decode("utf-8")
                # Se procesan todos los paquetes completos separados por salto de linea (NDJSON)
                while "\n" in buffer:
                    linea, buffer = buffer.split("\n", 1)
                    if linea.strip():
                        msg = json.loads(linea)
                        self.actualizar_estado_red(msg)
            except Exception:
                break
        self.socket_cliente = None

    def actualizar_estado_red(self, mensaje: dict) -> None:
        """
        Descripcion:
            Procesa de forma segura para hilos (thread-safe) un diccionario de estado
            enviado por el servidor TCP ('bienvenida', 'estado' o 'accion').
        Entradas:
            mensaje (dict): Diccionario decodificado desde el paquete JSON del servidor.
        Salidas:
            None: Actualiza id_jugador_red, estado_partida_red o acciones_remotas.
        Restricciones:
            mensaje debe ser un diccionario valido; protege la escritura con estado_red_lock.
        """
        import time
        with self.estado_red_lock:
            tipo = mensaje.get("tipo")
            if tipo == "bienvenida":
                self.id_jugador_red = mensaje.get("id_jugador")
            elif tipo == "estado":
                self.estado_partida_red = mensaje
            elif tipo == "accion":
                id_j = mensaje.get("jugador")
                if id_j is not None:
                    self.acciones_remotas[int(id_j)] = time.time() + 0.5

    def enviar_movimiento_red(self, x, y):
        """
        Descripcion:
            Envia al servidor TCP un paquete JSON con el vector de direccion (dx, dy)
            del jugador local.
        Entradas:
            x (int): Coordenada horizontal.
            y (int): Coordenada vertical.
        Salidas:
            None: Transmite el paquete por el socket si hay conexion activa.
        Restricciones:
            Si no existe conexion TCP activa, retorna sin lanzar excepcion.
        """
        if self.socket_cliente is None:
            return
        try:
            paquete = json.dumps({"tipo": "movimiento", "x": int(x), "y": int(y)}) + "\n"
            self.socket_cliente.sendall(paquete.encode("utf-8"))
        except Exception:
            self.socket_cliente = None

    def enviar_accion_red(self, texto: str = "[EXTRAYENDO]") -> None:
        """
        Descripcion:
            Envia al servidor TCP una notificacion de que el jugador local esta presionando
            el 5to boton de accion (por ejemplo, extrayendo energia en el Reactor).
        Entradas:
            texto (str): Etiqueta descriptiva de la accion realizada.
        Salidas:
            None: Transmite el paquete JSON al servidor.
        Restricciones:
            No bloquea el bucle de Pygame si el socket se desconecta abruptamente.
        """
        if self.socket_cliente is None:
            return
        try:
            paquete = json.dumps({"tipo": "accion", "mensaje": texto}) + "\n"
            self.socket_cliente.sendall(paquete.encode("utf-8"))
        except Exception:
            self.socket_cliente = None

    def enviar_configuracion_partida_red(self) -> None:
        """
        Descripcion:
            Transmite al servidor TCP la configuracion establecida por el Creador (minutos,
            meta de puntos, modo de fin y congelamiento) antes de arrancar la arena (US-08).
        Entradas:
            Ninguna.
        Salidas:
            None: Envia el paquete 'configurar_partida' si el socket esta activo.
        Restricciones:
            No bloquea la aplicacion si el socket se encuentra desconectado.
        """
        if self.socket_cliente is None:
            return
        try:
            msg = {
                "tipo": "configurar_partida",
                "minutos": int(self.tiempo_partida_min),
                "puntos": int(self.puntos_meta),
                "modo": self.modo_fin,
                "congelamiento": int(self.tiempo_congelado_seg),
            }
            paquete = json.dumps(msg) + "\n"
            self.socket_cliente.sendall(paquete.encode("utf-8"))
        except Exception:
            self.socket_cliente = None

    def ejecutar(self) -> None:
        """
        Descripcion:
            Punto de arranque del flujo visual del cliente; abre la ventana de Login.
        Entradas:
            Ninguna.
        Salidas:
            None: Transfiere el control al bucle de eventos de LoginView.
        Restricciones:
            Debe llamarse desde el hilo principal del proceso.
        """
        self.mostrar_login()

    def _cerrar_ventana_actual(self) -> None:
        """
        Descripcion:
            Destruye de forma segura la ventana CustomTkinter activa antes de instanciar
            una nueva vista, garantizando el principio de ventana unica.
        Entradas:
            Ninguna.
        Salidas:
            None: Libera los recursos de ventana_actual y la asigna a None.
        Restricciones:
            Captura cualquier TclError si la ventana ya habia sido cerrada previamente.
        """
        if self.ventana_actual is not None:
            try:
                self.ventana_actual.withdraw()
                for after_id in list(self.ventana_actual.tk.call("after", "info")):
                    try:
                        self.ventana_actual.after_cancel(after_id)
                    except Exception:
                        pass
                self.ventana_actual.destroy()
            except Exception:
                pass
            self.ventana_actual = None

    def mostrar_login(self) -> None:
        """
        Descripcion:
            Cierra la vista previa y despliega la ventana de Inicio de Sesion (LoginView).
        Entradas:
            Ninguna.
        Salidas:
            None: Inicia el mainloop de LoginView.
        Restricciones:
            Ninguna.
        """
        self._cerrar_ventana_actual()
        from Cliente.Interfaz.login_view import LoginView
        self.ventana_actual = LoginView(self)
        self.ventana_actual.mainloop()

    def mostrar_admin_login(self) -> None:
        """
        Descripcion:
            Cierra la vista previa y abre la ventana de autorizacion de Administrador
            (AdminAccessView) para ingresar la contrasena y elegir Admin 1 o Admin 2.
        Entradas:
            Ninguna.
        Salidas:
            None: Inicia el mainloop de AdminAccessView.
        Restricciones:
            Ninguna.
        """
        self._cerrar_ventana_actual()
        from Cliente.Interfaz.login_view import AdminAccessView
        self.ventana_actual = AdminAccessView(self)
        self.ventana_actual.mainloop()

    def mostrar_signup(self) -> None:
        """
        Descripcion:
            Cierra la vista actual y abre el formulario de Registro de Cuenta (SignupView).
        Entradas:
            Ninguna.
        Salidas:
            None: Inicia el mainloop de SignupView.
        Restricciones:
            Ninguna.
        """
        self._cerrar_ventana_actual()
        from Cliente.Interfaz.signup_view import SignupView
        self.ventana_actual = SignupView(self)
        self.ventana_actual.mainloop()

    def mostrar_recuperar_password(self) -> None:
        """
        Descripcion:
            Cierra la vista actual y abre la ventana de Recuperacion de Contrasena (US-05).
        Entradas:
            Ninguna.
        Salidas:
            None: Inicia el mainloop de RecuperarPasswordView.
        Restricciones:
            Ninguna.
        """
        self._cerrar_ventana_actual()
        from Cliente.Interfaz.recuperar_password_view import RecuperarPasswordView
        self.ventana_actual = RecuperarPasswordView(self)
        self.ventana_actual.mainloop()

    def mostrar_hub(self) -> None:
        """
        Descripcion:
            Cierra la vista actual y despliega el Menu Principal (HubView).
        Entradas:
            Ninguna.
        Salidas:
            None: Inicia el mainloop de HubView.
        Restricciones:
            Requiere que un usuario haya iniciado sesion previamente.
        """
        self._cerrar_ventana_actual()
        from Cliente.Interfaz.hub_view import HubView
        self.ventana_actual = HubView(self)
        self.ventana_actual.mainloop()

    def mostrar_jugar(self) -> None:
        """
        Descripcion:
            Cierra la vista actual y abre la pantalla de seleccion/creacion de sala (JugarView).
        Entradas:
            Ninguna.
        Salidas:
            None: Inicia el mainloop de JugarView.
        Restricciones:
            Ninguna.
        """
        self._cerrar_ventana_actual()
        from Cliente.Interfaz.jugar_view import JugarView
        self.ventana_actual = JugarView(self)
        self.ventana_actual.mainloop()

    def mostrar_avatar_select(self) -> None:
        """
        Descripcion:
            Cierra la vista actual y abre el selector de Avatar en CustomTkinter (AvatarSelectView - US-06).
        Entradas:
            Ninguna.
        Salidas:
            None: Inicia el mainloop de AvatarSelectView.
        Restricciones:
            Ninguna.
        """
        self._cerrar_ventana_actual()
        from Cliente.Interfaz.avatar_select_view import AvatarSelectView
        self.ventana_actual = AvatarSelectView(self)
        self.ventana_actual.mainloop()

    def mostrar_perfil(self) -> None:
        """
        Descripcion:
            Cierra la vista actual y abre la ventana de Perfil de Jugador (PerfilView).
        Entradas:
            Ninguna.
        Salidas:
            None: Inicia el mainloop de PerfilView.
        Restricciones:
            Ninguna.
        """
        self._cerrar_ventana_actual()
        from Cliente.Interfaz.perfil_view import PerfilView
        self.ventana_actual = PerfilView(self)
        self.ventana_actual.mainloop()

    def mostrar_settings(self, origen: str = "hub") -> None:
        """
        Descripcion:
            Cierra la vista actual y abre la ventana de Configuracion de Audio (SettingsView),
            recordando la pantalla de origen para regresar correctamente al pulsar 'Listo'.
        Entradas:
            origen (str): Identificador de la vista que abrio ajustes ('hub' o 'lobby').
        Salidas:
            None: Inicia el mainloop de SettingsView.
        Restricciones:
            origen debe ser 'hub' o 'lobby'.
        """
        self._cerrar_ventana_actual()
        from Cliente.Interfaz.settings_view import SettingsView
        self.ventana_actual = SettingsView(self, origen=origen)
        self.ventana_actual.mainloop()

    def volver_de_settings(self, origen: str = "hub") -> None:
        """
        Descripcion:
            Retorna desde la vista de Configuracion de Audio hacia la vista que la invoco.
        Entradas:
            origen (str): Vista de procedencia ('lobby' o 'hub').
        Salidas:
            None: Abre el Lobby Caminable o el Menu Principal segun corresponda.
        Restricciones:
            Ninguna.
        """
        if origen == "lobby":
            self.entrar_al_lobby()
        else:
            self.mostrar_hub()

    def entrar_al_lobby(self) -> None:
        """
        Descripcion:
            Destruye la ventana administrativa de CustomTkinter, intenta enlazar con el
            servidor TCP y transfiere el control al Lobby Caminable en Pygame.
        Entradas:
            Ninguna.
        Salidas:
            None: Ejecuta el bucle de eventos de iniciar_lobby_pygame.
        Restricciones:
            Cierra previamente cualquier ventana Tkinter para evitar dos ventanas simultaneas.
        """
        self._cerrar_ventana_actual()
        self.conectar_servidor_tcp()
        from Cliente.Interfaz.lobby_view import iniciar_lobby_pygame
        iniciar_lobby_pygame(self)

    def iniciar_arena(self) -> None:
        """
        Descripcion:
            Cierra cualquier ventana administrativa activa y lanza directamente la Arena
            de Batalla en Pygame.
        Entradas:
            Ninguna.
        Salidas:
            None: Ejecuta el bucle principal de iniciar_arena_pygame.
        Restricciones:
            Ninguna.
        """
        self._cerrar_ventana_actual()
        self.guardar_configuracion_partida()  # CA-08.1: se recuerda la ultima configuracion usada
        from Cliente.Interfaz.arena_view import iniciar_arena_pygame
        iniciar_arena_pygame(self)

    def cerrar_aplicacion(self) -> None:
        """
        Descripcion:
            Libera ordenadamente la ventana activa, cierra el socket TCP si existe,
            detiene el subsistema de audio/video de Pygame y termina el proceso.
        Entradas:
            Ninguna.
        Salidas:
            None: Finaliza la ejecucion del programa con codigo de salida 0.
        Restricciones:
            Ninguna.
        """
        self._cerrar_ventana_actual()
        if self.socket_cliente is not None:
            try:
                self.socket_cliente.close()
            except Exception:
                pass
            self.socket_cliente = None
        try:
            pygame.mixer.quit()
            pygame.quit()
        except Exception:
            pass
        sys.exit(0)
