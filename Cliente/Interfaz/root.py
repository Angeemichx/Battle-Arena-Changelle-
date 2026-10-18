"""
Controlador Maestro de la Aplicacion (root).
Se mantiene vivo en segundo plano coordinando la navegacion,
el audio continuo, la persistencia local y el puente de red TCP sin duplicar ventanas.
"""
from __future__ import annotations
import json
import math
import os
import socket
import struct
import sys
import threading
import wave
from pathlib import Path
import pygame

from Cliente.Interfaz.components.ui_helpers import COLORES_AVATAR

CONFIG_PATH = Path(__file__).resolve().parent.parent / "Recursos" / "config_local.json"
AUDIO_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "Recursos" / "ambiente_espacial.wav"


def _asegurar_pista_espacial_default(ruta_wav: Path):
    """
    Si no existe ningun archivo de audio en Cliente/Recursos/, genera un archivo .wav
    ambiental suave para garantizar el cumplimiento de CA-09.10 sin dependencias externas.
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
            # Acorde espacial suave (La menor ambiental: 110Hz + 165Hz + 220Hz)
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


class AppController:
    def __init__(self, modo_estricto: bool = False):
        # Interruptor para activar/desactivar bloqueos de parametros (min 2 jugadores, codigos, etc.)
        self.modo_estricto = modo_estricto

        # 1. Sesion del Jugador
        self.usuario_actual = "Piloto"
        self.avatar_color = "#E63946"  # Rojo por defecto
        self.avatar_imagen = None
        self.es_creador = False
        self.mapa_seleccionado = "Estacion Estandar"
        self.jugadores_sala = []

        # 2. Parametros y Puente de Red (Compatible con Servidor/infraestructure/socket_server.py)
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

        # 4. Referencia de la ventana activa (para evitar ventanas multiples)
        self.ventana_actual = None

    def _obtener_ip_local(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def obtener_nombre_color(self, hex_color: str) -> str:
        for nombre, codigo in COLORES_AVATAR.items():
            if codigo.upper() == hex_color.upper():
                return nombre
        return "Rojo"

    def validar_color_disponible(self, hex_color: str, jugadores: list[dict]) -> bool:
        """
        Verifica que ningun otro jugador en la sala tenga ya asignado ese color (CA-10.3).
        """
        objetivo = hex_color.strip().upper()
        for j in jugadores:
            if not j.get("es_local", False) and str(j.get("color", "")).strip().upper() == objetivo:
                return False
        return True

    def cargar_config_local(self):
        """Carga las preferencias locales de avatar y volumen si existen (CA-06.4)."""
        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                self.avatar_color = datos.get("avatar_color", self.avatar_color)
                self.avatar_imagen = datos.get("avatar_imagen", self.avatar_imagen)
                self.volumen_musica = int(datos.get("volumen_musica", self.volumen_musica))
        except Exception:
            pass

    def guardar_config_local(self):
        """Guarda la eleccion de avatar y volumen en JSON del cliente (CA-06.4)."""
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

    def _iniciar_subsistema_audio(self):
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

    def actualizar_volumen_audio(self):
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.set_volume(self.volumen_musica / 100.0)
            self.guardar_config_local()
        except Exception:
            pass

    # =========================================================================
    # PUENTE DE SINCRONIZACION DE RED (US-10 / US-13)
    # =========================================================================
    def conectar_servidor_tcp(self, host: str | None = None, port: int | None = None) -> bool:
        """
        Intenta conectar al ServidorJuego TCP (del Integrante 3/4) sin bloquear la interfaz
        si el servidor no esta encendido.
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

    def _escuchar_servidor(self):
        buffer = ""
        while self.socket_cliente is not None:
            try:
                datos = self.socket_cliente.recv(4096)
                if not datos:
                    break
                buffer += datos.decode("utf-8")
                while "\n" in buffer:
                    linea, buffer = buffer.split("\n", 1)
                    if linea.strip():
                        msg = json.loads(linea)
                        self.actualizar_estado_red(msg)
            except Exception:
                break
        self.socket_cliente = None

    def actualizar_estado_red(self, mensaje: dict):
        """
        Procesa los mensajes JSON enviados por ServidorJuego:
        - {"tipo": "bienvenida", "id_jugador": 1}
        - {"tipo": "estado", "jugadores": [...], "activa": True, "ganador": None}
        - {"tipo": "accion", "jugador": 2, "mensaje": "..."}
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

    def enviar_movimiento_red(self, dx: int, dy: int):
        if self.socket_cliente is None:
            return
        try:
            paquete = json.dumps({"tipo": "movimiento", "dx": int(dx), "dy": int(dy)}) + "\n"
            self.socket_cliente.sendall(paquete.encode("utf-8"))
        except Exception:
            self.socket_cliente = None

    def enviar_accion_red(self, texto: str = "[EXTRAYENDO]"):
        if self.socket_cliente is None:
            return
        try:
            paquete = json.dumps({"tipo": "accion", "mensaje": texto}) + "\n"
            self.socket_cliente.sendall(paquete.encode("utf-8"))
        except Exception:
            self.socket_cliente = None

    # =========================================================================
    # NAVEGACION DE VENTANAS
    # =========================================================================
    def ejecutar(self):
        """Inicia el programa mostrando la pantalla de Login."""
        self.mostrar_login()

    def _cerrar_ventana_actual(self):
        """Cierra y destruye la ventana actual antes de abrir otra."""
        if self.ventana_actual is not None:
            try:
                self.ventana_actual.destroy()
            except Exception:
                pass
            self.ventana_actual = None

    def mostrar_login(self):
        self._cerrar_ventana_actual()
        from Cliente.Interfaz.login_view import LoginView
        self.ventana_actual = LoginView(self)
        self.ventana_actual.mainloop()

    def mostrar_signup(self):
        self._cerrar_ventana_actual()
        from Cliente.Interfaz.signup_view import SignupView
        self.ventana_actual = SignupView(self)
        self.ventana_actual.mainloop()

    def mostrar_hub(self):
        self._cerrar_ventana_actual()
        from Cliente.Interfaz.hub_view import HubView
        self.ventana_actual = HubView(self)
        self.ventana_actual.mainloop()

    def mostrar_jugar(self):
        self._cerrar_ventana_actual()
        from Cliente.Interfaz.jugar_view import JugarView
        self.ventana_actual = JugarView(self)
        self.ventana_actual.mainloop()

    def mostrar_perfil(self):
        self._cerrar_ventana_actual()
        from Cliente.Interfaz.perfil_view import PerfilView
        self.ventana_actual = PerfilView(self)
        self.ventana_actual.mainloop()

    def mostrar_settings(self, origen="hub"):
        self._cerrar_ventana_actual()
        from Cliente.Interfaz.settings_view import SettingsView
        self.ventana_actual = SettingsView(self, origen=origen)
        self.ventana_actual.mainloop()

    def volver_de_settings(self, origen="hub"):
        if origen == "lobby":
            self.entrar_al_lobby()
        else:
            self.mostrar_hub()

    def entrar_al_lobby(self):
        """Cierra Tkinter de forma limpia, intenta conectar red y abre el Lobby en Pygame."""
        self._cerrar_ventana_actual()
        self.conectar_servidor_tcp()
        from Cliente.Interfaz.lobby_view import iniciar_lobby_pygame
        iniciar_lobby_pygame(self)

    def iniciar_arena(self):
        """Inicia directamente la vista de la Arena en Pygame."""
        self._cerrar_ventana_actual()
        from Cliente.Interfaz.arena_view import iniciar_arena_pygame
        iniciar_arena_pygame(self)

    def cerrar_aplicacion(self):
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
