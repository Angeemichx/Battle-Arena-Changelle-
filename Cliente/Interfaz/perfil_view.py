"""
Ventana de Perfil de Jugador.
Muestra datos basicos y aviso de modulo en mantenimiento.
"""
import customtkinter as ctk
from Cliente.Interfaz.components.ui_helpers import (
    COLOR_PANEL, COLOR_SECUNDARIO, COLOR_SECUNDARIO_HOVER, COLOR_TEXTO,
    adaptar_ventana_ctk
)

class PerfilView(ctk.CTk):
    def __init__(self, controller):
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
            command=self.controller.mostrar_hub
        ).pack(side="left")
        
        frame = ctk.CTkFrame(self, fg_color=COLOR_PANEL, corner_radius=12)
        frame.pack(padx=25, pady=15, fill="both", expand=True)
        
        ctk.CTkLabel(
            frame, 
            text="PERFIL DE JUGADOR", 
            font=("Segoe UI", 18, "bold"), 
            text_color=COLOR_TEXTO
        ).pack(pady=(25, 15))
        
        # Tarjeta de Datos
        card = ctk.CTkFrame(frame, fg_color="#181A20", corner_radius=8)
        card.pack(padx=30, pady=10, fill="x")
        
        ctk.CTkLabel(
            card, 
            text=f"Usuario: {self.controller.usuario_actual}", 
            font=("Segoe UI", 13, "bold")
        ).pack(pady=(12, 4))
        
        ctk.CTkLabel(
            card, 
            text="Rango: Cadete | Nivel: 1", 
            font=("Segoe UI", 11), 
            text_color="#8E9AA8"
        ).pack(pady=(0, 12))
        
        # Recuadro En Mantenimiento
        aviso = ctk.CTkFrame(frame, fg_color="#2D2A1F", corner_radius=8, border_width=1, border_color="#DDAA33")
        aviso.pack(padx=30, pady=25, fill="x")
        
        ctk.CTkLabel(
            aviso, 
            text="MODULO EN MANTENIMIENTO", 
            font=("Segoe UI", 12, "bold"), 
            text_color="#E9C46A"
        ).pack(pady=(12, 4))
        
        ctk.CTkLabel(
            aviso, 
            text="Las estadisticas detalladas y el historial de partidas\nse habilitaran al completar la sincronizacion con el servidor.",
            font=("Segoe UI", 11), 
            text_color="#C8C8C8", 
            justify="center"
        ).pack(pady=(0, 12))
