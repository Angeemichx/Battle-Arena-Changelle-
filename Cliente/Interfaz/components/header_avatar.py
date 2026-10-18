"""
Componente de cabecera con el avatar activo y nombre de usuario.
Cumple con el criterio CA-06.5 exigido en la guia.
"""
import customtkinter as ctk
from Cliente.Interfaz.components.ui_helpers import COLOR_TEXTO, COLOR_PANEL

class HeaderAvatar(ctk.CTkFrame):
    def __init__(self, master, usuario: str, color_avatar: str, on_logout=None, **kwargs):
        super().__init__(master, height=50, fg_color=COLOR_PANEL, corner_radius=0, **kwargs)
        self.pack_propagate(False)

        # Recuadro del color de Avatar activo (hitbox funcional de 32x32)
        self.avatar_box = ctk.CTkFrame(self, width=30, height=30, fg_color=color_avatar, corner_radius=4)
        self.avatar_box.pack(side="left", padx=(15, 10), pady=10)
        self.avatar_box.pack_propagate(False)

        # Nombre del jugador
        self.lbl_usuario = ctk.CTkLabel(
            self, 
            text=f"Piloto: {usuario}", 
            font=("Segoe UI", 13, "bold"),
            text_color=COLOR_TEXTO
        )
        self.lbl_usuario.pack(side="left", pady=10)

        # Boton Cerrar Sesion si se especifica callback
        if on_logout:
            self.btn_logout = ctk.CTkButton(
                self, 
                text="Cerrar Sesion", 
                width=100, 
                height=28,
                fg_color="#2B2D42",
                hover_color="#3B3E5B",
                font=("Segoe UI", 11),
                command=on_logout
            )
            self.btn_logout.pack(side="right", padx=15)

    def actualizar(self, usuario: str, color_avatar: str):
        self.lbl_usuario.configure(text=f"Piloto: {usuario}")
        self.avatar_box.configure(fg_color=color_avatar)
