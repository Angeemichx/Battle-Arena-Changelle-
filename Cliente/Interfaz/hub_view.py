"""
UI Intermedia (Menu Principal / Hub).
Punto de encuentro tras iniciar sesion.
Contiene: Jugar, Perfil, Configuracion y Salir.
"""
import customtkinter as ctk
from pathlib import Path
from PIL import Image
from Cliente.Interfaz.Components.header_avatar import HeaderAvatar
from Cliente.Interfaz.Components.ui_helpers import (
    COLOR_PANEL, COLOR_PRIMARIO, COLOR_PRIMARIO_HOVER,
    COLOR_SECUNDARIO, COLOR_SECUNDARIO_HOVER,
    COLOR_PELIGRO, COLOR_PELIGRO_HOVER, COLOR_TEXTO,
    adaptar_ventana_ctk,
)


# =============================================================================
# Documentacion de Clase: HubView
# Proposito:
#   Representar el Menu Principal (Centro de Operaciones) posterior al inicio de
#   sesion, mostrando la cabecera persistente con el avatar/nombre del piloto y
#   los accesos directos hacia Jugar, Perfil, Configuracion de Audio y Salida.
# Contenido:
#   - Atributos principales: controller (AppController), header (HeaderAvatar)
#     y menu_frame (CTkFrame).
#   - Metodos: __init__ (construccion y disposicion de los botones principales).
# =============================================================================
class HubView(ctk.CTk):
    def __init__(self, controller):
        """
        Descripcion:
            Inicializa la ventana del Menu Principal adaptada a la pantalla del ordenador,
            inserta la barra superior con el avatar del usuario y los 4 botones de navegacion.
        Entradas:
            controller (AppController): Instancia del controlador maestro de la aplicacion.
        Salidas:
            None: Despliega los controles visuales del Menu Principal.
        Restricciones:
            controller debe tener definidos usuario_actual y avatar_color.
        """
        super().__init__()
        self.controller = controller

        # Helper para cargar iconos de UI en CustomTkinter
        def _get_ui_icon(nombre_archivo, size=(24, 24)):
            p = Path(__file__).resolve().parent.parent / "Recursos" / "Sprites" / "UI" / nombre_archivo
            if p.exists():
                try:
                    pil_img = Image.open(str(p))
                    return ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
                except Exception:
                    pass
            return None

        self.img_logo = _get_ui_icon("logo_letras_puras.png", size=(300, 58))
        self.btn_img_jugar = _get_ui_icon("btn_nuclear_jugar.png", size=(280, 46))
        self.btn_img_avatar = _get_ui_icon("btn_nuclear_avatar.png", size=(280, 46))
        self.btn_img_perfil = _get_ui_icon("btn_nuclear_perfil.png", size=(280, 46))
        self.btn_img_audio = _get_ui_icon("btn_nuclear_audio.png", size=(280, 46))
        self.btn_img_salir = _get_ui_icon("btn_nuclear_salir.png", size=(280, 46))

        self.ic_jugar = _get_ui_icon("icon_jugar.png", size=(24, 24))
        self.ic_avatar = _get_ui_icon("icon_avatar.png", size=(24, 24))
        self.ic_perfil = _get_ui_icon("icon_perfil.png", size=(24, 24))
        self.ic_audio = _get_ui_icon("icon_audio.png", size=(24, 24))
        self.ic_salir = _get_ui_icon("icon_salir.png", size=(22, 22))

        self.title("Battle Arena - Menu Principal")
        adaptar_ventana_ctk(self, porcentaje_w=0.40, porcentaje_h=0.72, min_w=480, min_h=580)
        self.resizable(True, True)
        ctk.set_appearance_mode("dark")

        # Fondo ambiental de estacion nuclear
        ruta_bg = Path(__file__).resolve().parent.parent / "Recursos" / "Sprites" / "UI" / "bg_nuclear_station.png"
        if ruta_bg.exists():
            try:
                pil_bg = Image.open(str(ruta_bg))
                self.bg_img = ctk.CTkImage(light_image=pil_bg, dark_image=pil_bg, size=(900, 750))
                self.lbl_bg = ctk.CTkLabel(self, image=self.bg_img, text="")
                self.lbl_bg.place(x=0, y=0, relwidth=1, relheight=1)
            except Exception:
                pass

        # Barra superior con Avatar y Usuario (cumple el criterio CA-06.5)
        self.header = HeaderAvatar(
            self,
            usuario=self.controller.usuario_actual,
            color_avatar=self.controller.avatar_color,
            on_logout=self.controller.mostrar_login,
        )
        self.header.pack(fill="x", side="top")

        # Panel central de opciones con estetica de estacion nuclear
        self.menu_frame = ctk.CTkFrame(self, fg_color=("#141822", "#141822"), border_width=2, border_color="#2A354D", corner_radius=12)
        self.menu_frame.pack(padx=35, pady=25, fill="both", expand=True)

        # Logotipo oficial del juego: letras puras transparentes sin caja de fondo
        if self.img_logo:
            ctk.CTkLabel(self.menu_frame, image=self.img_logo, text="").pack(pady=(16, 12))
        else:
            ctk.CTkLabel(
                self.menu_frame,
                text="CENTRO DE OPERACIONES",
                font=("Segoe UI", 18, "bold"),
                text_color=COLOR_TEXTO,
            ).pack(pady=(20, 15))

        # 1. Jugar (Operacion Reactor)
        if self.btn_img_jugar:
            ctk.CTkButton(
                self.menu_frame,
                image=self.btn_img_jugar,
                text="",
                width=280,
                height=46,
                fg_color="transparent",
                hover_color="#1F2A3E",
                command=self.controller.mostrar_jugar,
            ).pack(pady=6)
        else:
            ctk.CTkButton(
                self.menu_frame,
                text="  JUGAR",
                image=self.ic_jugar,
                compound="left",
                width=280,
                height=44,
                font=("Segoe UI", 14, "bold"),
                fg_color=COLOR_PRIMARIO,
                hover_color=COLOR_PRIMARIO_HOVER,
                command=self.controller.mostrar_jugar,
            ).pack(pady=6)

        # 2. Seleccionar Avatar (Traje Hazmat)
        if self.btn_img_avatar:
            ctk.CTkButton(
                self.menu_frame,
                image=self.btn_img_avatar,
                text="",
                width=280,
                height=46,
                fg_color="transparent",
                hover_color="#1F2A3E",
                command=self.controller.mostrar_avatar_select,
            ).pack(pady=6)
        else:
            ctk.CTkButton(
                self.menu_frame,
                text="  SELECCIONAR AVATAR",
                image=self.ic_avatar,
                compound="left",
                width=280,
                height=42,
                font=("Segoe UI", 13, "bold"),
                fg_color="#2A9D8F",
                hover_color="#21867A",
                command=self.controller.mostrar_avatar_select,
            ).pack(pady=6)

        # 3. Perfil de Piloto
        if self.btn_img_perfil:
            ctk.CTkButton(
                self.menu_frame,
                image=self.btn_img_perfil,
                text="",
                width=280,
                height=46,
                fg_color="transparent",
                hover_color="#1F2A3E",
                command=self.controller.mostrar_perfil,
            ).pack(pady=6)
        else:
            ctk.CTkButton(
                self.menu_frame,
                text="  PERFIL DE PILOTO",
                image=self.ic_perfil,
                compound="left",
                width=280,
                height=42,
                font=("Segoe UI", 13),
                fg_color=COLOR_SECUNDARIO,
                hover_color=COLOR_SECUNDARIO_HOVER,
                command=self.controller.mostrar_perfil,
            ).pack(pady=6)

        # 4. Settings (Configuracion de Audio y Alarmas)
        if self.btn_img_audio:
            ctk.CTkButton(
                self.menu_frame,
                image=self.btn_img_audio,
                text="",
                width=280,
                height=46,
                fg_color="transparent",
                hover_color="#1F2A3E",
                command=lambda: self.controller.mostrar_settings(origen="hub"),
            ).pack(pady=6)
        else:
            ctk.CTkButton(
                self.menu_frame,
                text="  CONFIGURACION DE AUDIO",
                image=self.ic_audio,
                compound="left",
                width=280,
                height=42,
                font=("Segoe UI", 13),
                fg_color=COLOR_SECUNDARIO,
                hover_color=COLOR_SECUNDARIO_HOVER,
                command=lambda: self.controller.mostrar_settings(origen="hub"),
            ).pack(pady=6)

        # 5. Salir / Evacuar
        if self.btn_img_salir:
            ctk.CTkButton(
                self.menu_frame,
                image=self.btn_img_salir,
                text="",
                width=280,
                height=46,
                fg_color="transparent",
                hover_color="#3B181E",
                command=self.controller.cerrar_aplicacion,
            ).pack(pady=(8, 6))
        else:
            ctk.CTkButton(
                self.menu_frame,
                text="  SALIR DEL JUEGO",
                image=self.ic_salir,
                compound="left",
                width=280,
                height=38,
                font=("Segoe UI", 12),
                fg_color=COLOR_PELIGRO,
                hover_color=COLOR_PELIGRO_HOVER,
                command=self.controller.cerrar_aplicacion,
            ).pack(pady=(20, 10))
