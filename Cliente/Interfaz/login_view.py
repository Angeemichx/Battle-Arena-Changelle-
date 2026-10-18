"""
Ventana de Login (Inicio de Sesion).
Construida en CustomTkinter sin decoraciones innecesarias.
"""
import customtkinter as ctk
from Cliente.Interfaz.components.ui_helpers import (
    COLOR_PANEL, COLOR_PRIMARIO, COLOR_PRIMARIO_HOVER, 
    COLOR_SECUNDARIO, COLOR_TEXTO, COLOR_PELIGRO,
    adaptar_ventana_ctk
)

class LoginView(ctk.CTk):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        
        self.title("Battle Arena - Iniciar Sesion")
        adaptar_ventana_ctk(self, porcentaje_w=0.38, porcentaje_h=0.68, min_w=460, min_h=550)
        self.resizable(True, True)
        ctk.set_appearance_mode("dark")
        
        # Contenedor central
        self.frame = ctk.CTkFrame(self, fg_color=COLOR_PANEL, corner_radius=12)
        self.frame.pack(padx=30, pady=35, fill="both", expand=True)
        
        # Titulo funcional
        ctk.CTkLabel(
            self.frame, 
            text="BATTLE ARENA", 
            font=("Segoe UI", 24, "bold"), 
            text_color=COLOR_TEXTO
        ).pack(pady=(25, 4))
        
        ctk.CTkLabel(
            self.frame, 
            text="Control del Reactor", 
            font=("Segoe UI", 13), 
            text_color="#8E9AA8"
        ).pack(pady=(0, 20))
        
        # Campo Usuario
        ctk.CTkLabel(self.frame, text="Usuario o Correo", font=("Segoe UI", 12)).pack(anchor="w", padx=45, pady=(5, 0))
        self.txt_usuario = ctk.CTkEntry(self.frame, placeholder_text="Ingrese su usuario", width=320, height=38)
        self.txt_usuario.pack(pady=(2, 10))
        
        # Campo Contrasena
        ctk.CTkLabel(self.frame, text="Contrasena", font=("Segoe UI", 12)).pack(anchor="w", padx=45, pady=(5, 0))
        
        pwd_box = ctk.CTkFrame(self.frame, fg_color="transparent")
        pwd_box.pack(pady=(2, 12))
        
        self.txt_password = ctk.CTkEntry(pwd_box, placeholder_text="Ingrese contrasena", show="*", width=260, height=38)
        self.txt_password.pack(side="left")
        
        self.btn_ver = ctk.CTkButton(
            pwd_box, 
            text="Ver", 
            width=55, 
            height=38, 
            fg_color=COLOR_SECUNDARIO,
            command=self._toggle_ver
        )
        self.btn_ver.pack(side="left", padx=(5, 0))
        self.pwd_oculta = True
        
        # Mensaje de error
        self.lbl_error = ctk.CTkLabel(self.frame, text="", text_color=COLOR_PELIGRO, font=("Segoe UI", 12))
        self.lbl_error.pack(pady=4)

        # Boton Iniciar Sesion
        self.btn_login = ctk.CTkButton(
            self.frame, 
            text="INICIAR SESION", 
            width=320, 
            height=42, 
            font=("Segoe UI", 13, "bold"),
            fg_color=COLOR_PRIMARIO, 
            hover_color=COLOR_PRIMARIO_HOVER,
            command=self._ejecutar_login
        )
        self.btn_login.pack(pady=(10, 15))
        
        # Enlace a Sign Up
        self.btn_signup = ctk.CTkButton(
            self.frame, 
            text="Crear una cuenta nueva (Sign Up)", 
            fg_color="transparent", 
            text_color="#4A90E2", 
            hover=False, 
            font=("Segoe UI", 12, "underline"),
            command=self.controller.mostrar_signup
        )
        self.btn_signup.pack(pady=5)

    def _toggle_ver(self):
        self.pwd_oculta = not self.pwd_oculta
        self.txt_password.configure(show="" if not self.pwd_oculta else "*")
        self.btn_ver.configure(text="Ocultar" if not self.pwd_oculta else "Ver")

    def _ejecutar_login(self):
        usuario = self.txt_usuario.get().strip()
        pwd = self.txt_password.get().strip()
        if not usuario or not pwd:
            self.lbl_error.configure(text="Complete usuario y contrasena")
            return
        self.controller.usuario_actual = usuario
        self.controller.mostrar_hub()
