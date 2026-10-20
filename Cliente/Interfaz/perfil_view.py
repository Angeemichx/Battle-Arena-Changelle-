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

        base_ui = Path(__file__).resolve().parent.parent / "Recursos" / "Sprites" / "UI"

        # Fondo ambiental de estacion nuclear
        ruta_bg = base_ui / "bg_nuclear_station.png"
        if ruta_bg.exists():
            try:
                pil_bg = Image.open(str(ruta_bg))
                self.bg_img = ctk.CTkImage(light_image=pil_bg, dark_image=pil_bg, size=(900, 750))
                self.lbl_bg = ctk.CTkLabel(self, image=self.bg_img, text="")
                self.lbl_bg.place(x=0, y=0, relwidth=1, relheight=1)
            except Exception:
                pass

        def _cargar_img(nombre, size):
            p = base_ui / nombre
            if p.exists():
                try:
                    pil_i = Image.open(str(p))
                    return ctk.CTkImage(light_image=pil_i, dark_image=pil_i, size=size)
                except Exception:
                    pass
            return None

        self.ic_maint = _cargar_img("icon_maintenance.png", (56, 56))
        self.ic_bar = _cargar_img("hazard_stripe_bar.png", (340, 8))

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

        frame = ctk.CTkFrame(self, fg_color=("#141822", "#141822"), border_width=2, border_color="#2A354D", corner_radius=12)
        frame.pack(padx=25, pady=15, fill="both", expand=True)

        ctk.CTkLabel(
            frame,
            text="PERFIL DE JUGADOR",
            font=("Segoe UI", 18, "bold"),
            text_color=COLOR_TEXTO,
        ).pack(pady=(20, 10))

        if self.ic_bar:
            ctk.CTkLabel(frame, image=self.ic_bar, text="").pack(pady=(0, 15))

        # Recuadro central de Modulo en Mantenimiento
        maint_box = ctk.CTkFrame(
            frame,
            fg_color="#181C26",
            border_width=2,
            border_color="#E9C46A",
            corner_radius=10,
        )
        maint_box.pack(padx=30, pady=10, fill="both", expand=True)

        if self.ic_maint:
            ctk.CTkLabel(maint_box, image=self.ic_maint, text="").pack(pady=(25, 10))

        ctk.CTkLabel(
            maint_box,
            text="MODULO EN MANTENIMIENTO",
            font=("Segoe UI", 16, "bold"),
            text_color="#E9C46A",
        ).pack(pady=(5, 8))

        ctk.CTkLabel(
            maint_box,
            text=f"Piloto Activo: {self.controller.usuario_actual}",
            font=("Segoe UI", 12, "bold"),
            text_color="#39FF14",
        ).pack(pady=(0, 10))

        ctk.CTkLabel(
            maint_box,
            text="Las estadisticas avanzadas, historial de combates\ny expedientes de tripulacion se habilitaran tras la\nsincronizacion con el servidor central en el proximo Sprint.",
            font=("Segoe UI", 11),
            text_color="#8E9AA8",
            justify="center",
        ).pack(padx=20, pady=(0, 25))

        if self.ic_bar:
            ctk.CTkLabel(frame, image=self.ic_bar, text="").pack(pady=(10, 15))
