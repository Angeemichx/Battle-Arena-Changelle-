"""
Ventana de Configuracion de Audio.
Ajusta el volumen de la musica y cuenta con el boton 'Listo'
que regresa exactamente a la pantalla desde donde se abrio (Hub o Lobby).
"""
import customtkinter as ctk
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
        adaptar_ventana_ctk(self, porcentaje_w=0.36, porcentaje_h=0.60, min_w=450, min_h=480)
        self.resizable(True, True)
        ctk.set_appearance_mode("dark")

        frame = ctk.CTkFrame(self, fg_color=COLOR_PANEL, corner_radius=12)
        frame.pack(padx=30, pady=35, fill="both", expand=True)

        ctk.CTkLabel(
            frame,
            text="CONFIGURACION DE AUDIO",
            font=("Segoe UI", 18, "bold"),
            text_color=COLOR_TEXTO,
        ).pack(pady=(25, 20))

        ctk.CTkLabel(frame, text="Volumen de Musica", font=("Segoe UI", 13)).pack(pady=(10, 5))

        self.lbl_volumen = ctk.CTkLabel(
            frame,
            text=f"{self.controller.volumen_musica}%",
            font=("Segoe UI", 14, "bold"),
            text_color="#4A90E2",
        )
        self.lbl_volumen.pack()

        self.slider = ctk.CTkSlider(
            frame,
            from_=0,
            to=100,
            number_of_steps=100,
            width=280,
            command=self._cambiar_volumen,
        )
        self.slider.set(self.controller.volumen_musica)
        self.slider.pack(pady=15)

        ctk.CTkLabel(
            frame,
            text="Reproduccion continua en segundo plano",
            font=("Segoe UI", 11),
            text_color="#8E9AA8",
        ).pack(pady=10)

        # Boton Listo que regresa a la ventana anterior (Hub o Lobby)
        ctk.CTkButton(
            frame,
            text="LISTO",
            width=200,
            height=40,
            font=("Segoe UI", 13, "bold"),
            fg_color=COLOR_EXITO,
            hover_color=COLOR_EXITO_HOVER,
            command=self._volver,
        ).pack(pady=(35, 15))

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
