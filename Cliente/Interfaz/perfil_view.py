"""
Ventana de Perfil de Jugador.
Muestra datos basicos y aviso de modulo en mantenimiento.
"""
import customtkinter as ctk
from pathlib import Path
from PIL import Image
from Cliente.Interfaz.Components.ui_helpers import (
    COLOR_PANEL, COLOR_SECUNDARIO, COLOR_SECUNDARIO_HOVER, COLOR_TEXTO,
    adaptar_ventana_ctk,
)


# =============================================================================
# Documentacion de Clase: PerfilView
# Proposito:
#   Mostrar la ficha informativa del jugador autenticado (nombre de usuario,
#   rango inicial y nivel) junto con el aviso de que las estadisticas historicas
#   de partidas se sincronizaran con el repositorio del servidor.
# Contenido:
#   - Atributos principales: controller (AppController).
#   - Metodos: __init__ (construccion de la tarjeta de perfil y boton de retorno).
# =============================================================================
class PerfilView(ctk.CTk):
    def __init__(self, controller):
        """
        Descripcion:
            Inicializa la ventana de Perfil adaptada a la pantalla del computador,
            mostrando el nombre del piloto activo y el aviso de sincronizacion de estadisticas.
        Entradas:
            controller (AppController): Instancia del controlador maestro de la aplicacion.
        Salidas:
            None: Renderiza los widgets informativos de PerfilView.
        Restricciones:
            controller debe tener definido el atributo usuario_actual.
        """
        super().__init__()
        self.controller = controller

        self.title("Battle Arena - Perfil")
        adaptar_ventana_ctk(self, porcentaje_w=0.38, porcentaje_h=0.64, min_w=480, min_h=520)
        self.resizable(True, True)
        ctk.set_appearance_mode("dark")

        # Barra superior con boton Regresar
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=25, pady=(15, 0))

        ctk.CTkButton(
            top_bar,
            text="< Menu Principal",
            width=120,
            height=30,
            fg_color=COLOR_SECUNDARIO,
            hover_color=COLOR_SECUNDARIO_HOVER,
            command=self.controller.mostrar_hub,
        ).pack(side="left")

        frame = ctk.CTkFrame(self, fg_color=COLOR_PANEL, corner_radius=12)
        frame.pack(padx=25, pady=15, fill="both", expand=True)

        ctk.CTkLabel(
            frame,
            text="PERFIL DE JUGADOR",
            font=("Segoe UI", 18, "bold"),
            text_color=COLOR_TEXTO,
        ).pack(pady=(25, 15))

        # Insignia y Tarjeta de Datos del Piloto con Sprite
        ruta_marco = Path(__file__).resolve().parent.parent / "Recursos" / "Sprites" / "UI" / "card_perfil_marco.png"
        if ruta_marco.exists():
            try:
                pil_m = Image.open(str(ruta_marco))
                self.img_marco = ctk.CTkImage(light_image=pil_m, dark_image=pil_m, size=(320, 100))
                ctk.CTkLabel(frame, image=self.img_marco, text="").pack(pady=(5, 10))
            except Exception:
                self.img_marco = None
        else:
            self.img_marco = None

        card = ctk.CTkFrame(frame, fg_color="#181A20", corner_radius=8)
        card.pack(padx=30, pady=6, fill="x")

        ctk.CTkLabel(
            card,
            text=f"Piloto Autenticado: {self.controller.usuario_actual}",
            font=("Segoe UI", 13, "bold"),
        ).pack(pady=(12, 4))

        ctk.CTkLabel(
            card,
            text="Rango: Cadete | Nivel: 1",
            font=("Segoe UI", 11),
            text_color="#8E9AA8",
        ).pack(pady=(0, 12))

        # Recuadro informativo de sincronizacion con el servidor
        aviso = ctk.CTkFrame(frame, fg_color="#2D2A1F", corner_radius=8, border_width=1, border_color="#DDAA33")
        aviso.pack(padx=30, pady=25, fill="x")

        ctk.CTkLabel(
            aviso,
            text="MODULO EN MANTENIMIENTO",
            font=("Segoe UI", 12, "bold"),
            text_color="#E9C46A",
        ).pack(pady=(12, 4))

        ctk.CTkLabel(
            aviso,
            text="Las estadisticas detalladas y el historial de partidas\nse habilitaran al completar la sincronizacion con el servidor.",
            font=("Segoe UI", 11),
            text_color="#C8C8C8",
            justify="center",
        ).pack(pady=(0, 12))
