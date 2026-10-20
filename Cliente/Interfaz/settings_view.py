"""
Ventana de Configuracion de Audio.
Ajusta el volumen de la musica y cuenta con el boton 'Listo'
que regresa exactamente a la pantalla desde donde se abrio (Hub o Lobby).
"""
import customtkinter as ctk
from pathlib import Path
from PIL import Image
from Cliente.Interfaz.Components.ui_helpers import (
    COLOR_PANEL, COLOR_EXITO, COLOR_EXITO_HOVER, COLOR_TEXTO,
    adaptar_ventana_ctk,
)


# =============================================================================
# Documentacion de Clase: SettingsView
# Proposito:
#   Permitir al jugador ajustar en tiempo real el porcentaje de volumen (0% a 100%)
#   de la musica ambiental continua en segundo plano y persistir la preferencia
#   en config_local.json al confirmar con el boton 'LISTO'.
# Contenido:
#   - Atributos principales: controller (AppController), origen (str),
#     lbl_volumen (CTkLabel) y slider (CTkSlider).
#   - Metodos: __init__, _cambiar_volumen y _volver.
# =============================================================================
class SettingsView(ctk.CTk):
    def __init__(self, controller, origen: str = "hub"):
        """
        Descripcion:
            Construye la ventana de Configuracion de Audio escalada al monitor y configura
            el control deslizante (slider) sincronizado con el volumen actual del controlador.
        Entradas:
            controller (AppController): Instancia del controlador maestro de la aplicacion.
            origen (str): Nombre de la vista que invoco la ventana ('hub' o 'lobby').
        Salidas:
            None: Inicializa los controles visuales de SettingsView.
        Restricciones:
            controller.volumen_musica debe ser un entero entre 0 y 100.
        """
        super().__init__()
        self.controller = controller
        self.origen = origen

        self.title("Battle Arena - Configuracion de Audio")
        adaptar_ventana_ctk(self, porcentaje_w=0.38, porcentaje_h=0.66, min_w=460, min_h=520)
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

        # Helper para iconos
        def _cargar_img(nombre, size):
            p = base_ui / nombre
            if p.exists():
                try:
                    pil_i = Image.open(str(p))
                    return ctk.CTkImage(light_image=pil_i, dark_image=pil_i, size=size)
                except Exception:
                    pass
            return None

        self.ic_rad = _cargar_img("icon_radioactive.png", (40, 40))
        self.ic_bar = _cargar_img("hazard_stripe_bar.png", (340, 8))
        self.btn_guardar_img = _cargar_img("btn_nuclear_guardar.png", (220, 42))

        # Marco principal contenedor
        frame = ctk.CTkFrame(self, fg_color=("#141822", "#141822"), border_width=2, border_color="#2A354D", corner_radius=12)
        frame.pack(padx=25, pady=25, fill="both", expand=True)

        # Encabezado con icono radiactivo
        header_box = ctk.CTkFrame(frame, fg_color="transparent")
        header_box.pack(pady=(18, 10))

        if self.ic_rad:
            ctk.CTkLabel(header_box, image=self.ic_rad, text="").pack(side="left", padx=8)

        ctk.CTkLabel(
            header_box,
            text="CONFIGURACION DE AUDIO",
            font=("Segoe UI", 18, "bold"),
            text_color=COLOR_TEXTO,
        ).pack(side="left")

        # Barra decorativa superior de advertencia radiactiva
        if self.ic_bar:
            ctk.CTkLabel(frame, image=self.ic_bar, text="").pack(pady=(0, 10))

        # Caja central de modificacion de volumen con borde tematico radiactivo
        vol_box = ctk.CTkFrame(
            frame,
            fg_color="#181C26",
            border_width=2,
            border_color="#E9C46A",
            corner_radius=10,
        )
        vol_box.pack(padx=25, pady=8, fill="x")

        ctk.CTkLabel(
            vol_box,
            text="CONTROL DE ALARMAS Y MUSICA AMBIENTAL",
            font=("Segoe UI", 11, "bold"),
            text_color="#E9C46A",
        ).pack(pady=(12, 2))

        self.lbl_volumen = ctk.CTkLabel(
            vol_box,
            text=f"{self.controller.volumen_musica}%",
            font=("Segoe UI", 22, "bold"),
            text_color="#39FF14",
        )
        self.lbl_volumen.pack(pady=2)

        self.slider = ctk.CTkSlider(
            vol_box,
            from_=0,
            to=100,
            number_of_steps=100,
            width=280,
            progress_color="#39FF14",
            button_color="#E9C46A",
            button_hover_color="#F4A261",
            command=self._cambiar_volumen,
        )
        self.slider.set(self.controller.volumen_musica)
        self.slider.pack(pady=10)

        ctk.CTkLabel(
            vol_box,
            text="[ 0% SILENCIO DE BUNKER  ---  100% ALARMA CRITICA ]",
            font=("Segoe UI", 10),
            text_color="#8E9AA8",
        ).pack(pady=(0, 12))

        # Barra decorativa inferior de advertencia
        if self.ic_bar:
            ctk.CTkLabel(frame, image=self.ic_bar, text="").pack(pady=(10, 0))

        # Boton Listo que regresa a la ventana anterior (Hub o Lobby)
        if self.btn_guardar_img:
            ctk.CTkButton(
                frame,
                image=self.btn_guardar_img,
                text="",
                width=220,
                height=42,
                fg_color="transparent",
                hover_color="#1F2A3E",
                command=self._volver,
            ).pack(pady=(18, 12))
        else:
            ctk.CTkButton(
                frame,
                text="LISTO",
                width=200,
                height=40,
                font=("Segoe UI", 13, "bold"),
                fg_color=COLOR_EXITO,
                hover_color=COLOR_EXITO_HOVER,
                command=self._volver,
            ).pack(pady=(20, 12))

    def _cambiar_volumen(self, val: float) -> None:
        """
        Descripcion:
            Callback ejecutado al desplazar el control deslizante; actualiza el porcentaje
            en pantalla y aplica inmediatamente el volumen al subsistema de audio.
        Entradas:
            val (float): Valor numerico entregado por el CTkSlider en el rango [0.0, 100.0].
        Salidas:
            None: Modifica controller.volumen_musica y actualiza pygame.mixer.
        Restricciones:
            Convierte el valor flotante a entero antes de aplicarlo.
        """
        nuevo_vol = int(val)
        self.controller.volumen_musica = nuevo_vol
        self.lbl_volumen.configure(text=f"{nuevo_vol}%")
        self.controller.actualizar_volumen_audio()

    def _volver(self) -> None:
        """
        Descripcion:
            Cierra la ventana de ajustes y solicita al controlador regresar a la vista
            de origen ('hub' o 'lobby').
        Entradas:
            Ninguna.
        Salidas:
            None: Invoca controller.volver_de_settings(self.origen).
        Restricciones:
            Ninguna.
        """
        self.controller.volver_de_settings(self.origen)

    def _cambiar_volumen(self, val: float) -> None:
        """
        Descripcion:
            Callback ejecutado al desplazar el control deslizante; actualiza el porcentaje
            en pantalla y aplica inmediatamente el volumen al subsistema de audio.
        Entradas:
            val (float): Valor numerico entregado por el CTkSlider en el rango [0.0, 100.0].
        Salidas:
            None: Modifica controller.volumen_musica y actualiza pygame.mixer.
        Restricciones:
            Convierte el valor flotante a entero antes de aplicarlo.
        """
        nuevo_vol = int(val)
        self.controller.volumen_musica = nuevo_vol
        self.lbl_volumen.configure(text=f"{nuevo_vol}%")
        self.controller.actualizar_volumen_audio()

    def _volver(self) -> None:
        """
        Descripcion:
            Cierra la ventana de ajustes y solicita al controlador regresar a la vista
            de origen ('hub' o 'lobby').
        Entradas:
            Ninguna.
        Salidas:
            None: Invoca controller.volver_de_settings(self.origen).
        Restricciones:
            Ninguna.
        """
        self.controller.volver_de_settings(self.origen)
