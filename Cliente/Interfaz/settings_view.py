"""
Ventana de Configuracion de Audio.
Ajusta el volumen de la musica y cuenta con el boton 'Listo'
que regresa exactamente a la pantalla desde donde se abrio (Hub o Lobby).
"""
import customtkinter as ctk
from Cliente.Interfaz.components.ui_helpers import (
    COLOR_PANEL, COLOR_EXITO, COLOR_EXITO_HOVER, COLOR_TEXTO,
    adaptar_ventana_ctk
)

class SettingsView(ctk.CTk):
    def __init__(self, controller, origen="hub"):
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
            text_color=COLOR_TEXTO
        ).pack(pady=(25, 20))
        
        ctk.CTkLabel(frame, text="Volumen de Musica", font=("Segoe UI", 13)).pack(pady=(10, 5))
        
        self.lbl_volumen = ctk.CTkLabel(
            frame, 
            text=f"{self.controller.volumen_musica}%", 
            font=("Segoe UI", 14, "bold"), 
            text_color="#4A90E2"
        )
        self.lbl_volumen.pack()
        
        def cambiar_volumen(val):
            nuevo_vol = int(val)
            self.controller.volumen_musica = nuevo_vol
            self.lbl_volumen.configure(text=f"{nuevo_vol}%")
            self.controller.actualizar_volumen_audio()
            
        self.slider = ctk.CTkSlider(
            frame, 
            from_=0, 
            to=100, 
            number_of_steps=100, 
            width=280,
            command=cambiar_volumen
        )
        self.slider.set(self.controller.volumen_musica)
        self.slider.pack(pady=15)
        
        ctk.CTkLabel(
            frame, 
            text="Reproduccion continua en segundo plano", 
            font=("Segoe UI", 11), 
            text_color="#8E9AA8"
        ).pack(pady=10)
        
        # Boton Listo que regresa a la ventana anterior
        ctk.CTkButton(
            frame, 
            text="LISTO", 
            width=200, 
            height=40, 
            font=("Segoe UI", 13, "bold"),
            fg_color=COLOR_EXITO, 
            hover_color=COLOR_EXITO_HOVER,
            command=self._volver
        ).pack(pady=(35, 15))

    def _volver(self):
        self.controller.volver_de_settings(self.origen)
