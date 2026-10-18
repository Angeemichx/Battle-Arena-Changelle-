"""
Controlador Maestro de la Aplicacion (root).
Se mantiene vivo en segundo plano coordinando la navegacion,
el audio continuo y los datos de sesion/red sin duplicar ventanas.
"""
import sys
import socket
import pygame

class AppController:
    def __init__(self):
        # 1. Sesion del Jugador
        self.usuario_actual = "Piloto"
        self.avatar_color = "#E63946"  # Color base por defecto (Rojo)
        self.avatar_imagen = None
        self.es_creador = False
        
        # 2. Parametros de Red (Sockets TCP)
        self.ip_servidor = self._obtener_ip_local()
        self.puerto_servidor = 5555
        self.socket_cliente = None
        
        # 3. Audio Persistente en Segundo Plano
        self.volumen_musica = 50
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

    def _iniciar_subsistema_audio(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.set_volume(self.volumen_musica / 100.0)
        except Exception as e:
            print(f"[AUDIO] Subsistema de audio no disponible: {e}")

    def actualizar_volumen_audio(self):
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.set_volume(self.volumen_musica / 100.0)
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
        """Prepara el paso a Pygame (Lobby caminable)."""
        self._cerrar_ventana_actual()
        # Por ahora, si aun no hemos disenado el Lobby de Pygame,
        # dejamos lista la invocacion
        try:
            from Cliente.Interfaz.lobby_view import iniciar_lobby_pygame
            iniciar_lobby_pygame(self)
        except (ImportError, AttributeError):
            print("[INFO] El Lobby de Pygame se implementara en el siguiente paso.")
            # Si todavia no existe el archivo del lobby, regresamos al menu para que no se quede colgado
            self.mostrar_hub()

    def cerrar_aplicacion(self):
        self._cerrar_ventana_actual()
        try:
            pygame.mixer.quit()
            pygame.quit()
        except Exception:
            pass
        sys.exit(0)
