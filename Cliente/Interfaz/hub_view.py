"""
UI Intermedia (Menu Principal / Hub).
Punto de encuentro tras iniciar sesion.
Contiene: Jugar, Perfil, Configuracion y Salir.
"""
import customtkinter as ctk
from Cliente.Interfaz.components.header_avatar import HeaderAvatar
from Cliente.Interfaz.components.ui_helpers import (
    COLOR_PANEL, COLOR_PRIMARIO, COLOR_PRIMARIO_HOVER,
    COLOR_SECUNDARIO, COLOR_SECUNDARIO_HOVER,
    COLOR_PELIGRO, COLOR_PELIGRO_HOVER, COLOR_TEXTO,
    adaptar_ventana_ctk
)

class HubView(ctk.CTk):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        
        self.title("Battle Arena - Menu Principal")
        adaptar_ventana_ctk(self, porcentaje_w=0.40, porcentaje_h=0.70, min_w=480, min_h=580)
        self.resizable(True, True)
        ctk.set_appearance_mode("dark")
        
        # Barra superior con Avatar y Usuario (Requisito CA-06.5)
        self.header = HeaderAvatar(
            self, 
            usuario=self.controller.usuario_actual,
            color_avatar=self.controller.avatar_color,
            on_logout=self.controller.mostrar_login
        )
        self.header.pack(fill="x", side="top")
        
        # Panel central de opciones
        self.menu_frame = ctk.CTkFrame(self, fg_color=COLOR_PANEL, corner_radius=12)
        self.menu_frame.pack(padx=35, pady=30, fill="both", expand=True)
        
        ctk.CTkLabel(
            self.menu_frame, 
            text="CENTRO DE OPERACIONES", 
            font=("Segoe UI", 18, "bold"), 
            text_color=COLOR_TEXTO
        ).pack(pady=(25, 20))
        
        # 1. Jugar
        ctk.CTkButton(
            self.menu_frame, 
            text="JUGAR", 
            width=280, 
            height=44, 
            font=("Segoe UI", 14, "bold"),
            fg_color=COLOR_PRIMARIO, 
            hover_color=COLOR_PRIMARIO_HOVER,
            command=self.controller.mostrar_jugar
        ).pack(pady=10)
        
        # 2. Perfil
        ctk.CTkButton(
            self.menu_frame, 
            text="PERFIL", 
            width=280, 
            height=42, 
            font=("Segoe UI", 13),
            fg_color=COLOR_SECUNDARIO, 
            hover_color=COLOR_SECUNDARIO_HOVER,
            command=self.controller.mostrar_perfil
        ).pack(pady=10)
        
        # 3. Settings (Configuracion de Musica)
        ctk.CTkButton(
            self.menu_frame, 
            text="CONFIGURACION DE AUDIO", 
            width=280, 
            height=42, 
            font=("Segoe UI", 13),
            fg_color=COLOR_SECUNDARIO, 
            hover_color=COLOR_SECUNDARIO_HOVER,
            command=lambda: self.controller.mostrar_settings(origen="hub")
        ).pack(pady=10)
        
        # 4. Salir
        ctk.CTkButton(
            self.menu_frame, 
            text="SALIR DEL JUEGO", 
            width=280, 
            height=38, 
            font=("Segoe UI", 12),
            fg_color=COLOR_PELIGRO, 
            hover_color=COLOR_PELIGRO_HOVER,
            command=self.controller.cerrar_aplicacion
        ).pack(pady=(25, 10))
