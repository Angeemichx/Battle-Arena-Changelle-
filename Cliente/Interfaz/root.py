"""
Controlador Maestro de la Aplicacion (root).
Se mantiene vivo en segundo plano coordinando la navegacion,
el audio continuo y los datos de sesion/red sin duplicar ventanas.
"""
from __future__ import annotations
import json
import os
import socket
import sys
from pathlib import Path
import pygame

from Cliente.Interfaz.components.ui_helpers import COLORES_AVATAR

CONFIG_PATH = Path(__file__).resolve().parent.parent / "Recursos" / "config_local.json"


class AppController:
    def __init__(self):
        # 1. Sesion del Jugador
        self.usuario_actual = "Piloto"
        self.avatar_color = "#E63946"  # Rojo por defecto
        self.avatar_imagen = None
        self.es_creador = False
        self.mapa_seleccionado = "Estacion Estandar"
        self.jugadores_sala = []

        # 2. Parametros de Red (Sockets TCP)
        self.ip_servidor = self._obtener_ip_local()
        self.puerto_servidor = 5555
        self.socket_cliente = None

        # 3. Audio Persistente en Segundo Plano
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
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.set_volume(self.volumen_musica / 100.0)
            # Buscar pista musical en Cliente/Recursos si existe
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

    # Transiciones de Ventana
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
        """Cierra Tkinter de forma limpia y abre el Lobby Caminable en Pygame."""
        self._cerrar_ventana_actual()
        from Cliente.Interfaz.lobby_view import iniciar_lobby_pygame
        iniciar_lobby_pygame(self)

    def iniciar_arena(self):
        """Inicia directamente la vista de la Arena en Pygame."""
        self._cerrar_ventana_actual()
        from Cliente.Interfaz.arena_view import iniciar_arena_pygame
        iniciar_arena_pygame(self)

    def cerrar_aplicacion(self):
        self._cerrar_ventana_actual()
        try:
            pygame.mixer.quit()
            pygame.quit()
        except Exception:
            pass
        sys.exit(0)
