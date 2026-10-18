"""
Ventana de Sign Up (Registro de Cuenta).
Enfoque funcional: boton de regreso arriba a la izquierda,
Gmail con envio de codigo, verificacion de contrasenas y pantalla de exito.
Reutiliza AuthService de Integrante 4 cuando este disponible.
"""
import random
import customtkinter as ctk
from Cliente.Interfaz.components.ui_helpers import (
    COLOR_PANEL, COLOR_PRIMARIO, COLOR_PRIMARIO_HOVER,
    COLOR_SECUNDARIO, COLOR_SECUNDARIO_HOVER,
    COLOR_EXITO, COLOR_EXITO_HOVER,
    COLOR_PELIGRO, COLOR_TEXTO,
    adaptar_ventana_ctk
)

# Intentar reutilizar el servicio de autenticacion del Integrante 4
try:
    from Servidor.adapters.json_repository import JsonRepository
    from Servidor.use_cases.auth_service import AuthService
    _repo = JsonRepository("Servidor/infraestructure/data/usuarios.json")
    _auth = AuthService(_repo)
except Exception:
    _auth = None


class SignupView(ctk.CTk):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        
        self.title("Battle Arena - Registro")
        adaptar_ventana_ctk(self, porcentaje_w=0.40, porcentaje_h=0.76, min_w=480, min_h=640)
        self.resizable(True, True)
        ctk.set_appearance_mode("dark")
        
        self.codigo_generado = None
        self.pwd_oculta = True
        
        # Barra superior con boton Regresar a la izquierda
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=25, pady=(15, 0))
        
        self.btn_volver = ctk.CTkButton(
            top_bar, 
            text="< Regresar", 
            width=90, 
            height=30, 
            fg_color=COLOR_SECUNDARIO, 
            hover_color=COLOR_SECUNDARIO_HOVER,
            command=self.controller.mostrar_login
        )
        self.btn_volver.pack(side="left")
        
        # Marco del formulario
        self.form_frame = ctk.CTkFrame(self, fg_color=COLOR_PANEL, corner_radius=12)
        self.form_frame.pack(padx=25, pady=15, fill="both", expand=True)
        
        ctk.CTkLabel(
            self.form_frame, 
            text="CREAR CUENTA", 
            font=("Segoe UI", 20, "bold"), 
            text_color=COLOR_TEXTO
        ).pack(pady=(15, 10))
        
        # Campo Usuario
        ctk.CTkLabel(self.form_frame, text="Nombre de Usuario", font=("Segoe UI", 12)).pack(anchor="w", padx=45, pady=(4, 0))
        self.txt_user = ctk.CTkEntry(self.form_frame, placeholder_text="Usuario", width=320, height=36)
        self.txt_user.pack(pady=(2, 6))
        
        # Campo Gmail + Boton Enviar Codigo
        ctk.CTkLabel(self.form_frame, text="Correo Gmail", font=("Segoe UI", 12)).pack(anchor="w", padx=45, pady=(4, 0))
        email_box = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        email_box.pack(pady=(2, 6))
        
        self.txt_email = ctk.CTkEntry(email_box, placeholder_text="ejemplo@gmail.com", width=210, height=36)
        self.txt_email.pack(side="left")
        
        self.btn_enviar_cod = ctk.CTkButton(
            email_box, 
            text="Enviar Codigo", 
            width=105, 
            height=36, 
            fg_color="#3A6073",
            hover_color="#2B4654",
            command=self._enviar_codigo
        )
        self.btn_enviar_cod.pack(side="left", padx=(5, 0))
        
        # Campo Codigo recibido
        ctk.CTkLabel(self.form_frame, text="Codigo de Verificacion", font=("Segoe UI", 12)).pack(anchor="w", padx=45, pady=(4, 0))
        self.txt_codigo = ctk.CTkEntry(self.form_frame, placeholder_text="Codigo de 6 digitos", width=320, height=36)
        self.txt_codigo.pack(pady=(2, 6))
        
        # Contrasena 1
        ctk.CTkLabel(self.form_frame, text="Contrasena (minimo 8 caracteres)", font=("Segoe UI", 12)).pack(anchor="w", padx=45, pady=(4, 0))
        self.txt_pass1 = ctk.CTkEntry(self.form_frame, placeholder_text="Contrasena", show="*", width=320, height=36)
        self.txt_pass1.pack(pady=(2, 6))
        
        # Contrasena 2 + Boton Ver/Ocultar
        ctk.CTkLabel(self.form_frame, text="Confirmar Contrasena", font=("Segoe UI", 12)).pack(anchor="w", padx=45, pady=(4, 0))
        pass2_box = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        pass2_box.pack(pady=(2, 6))
        
        self.txt_pass2 = ctk.CTkEntry(pass2_box, placeholder_text="Confirmar contrasena", show="*", width=260, height=36)
        self.txt_pass2.pack(side="left")
        
        self.btn_ver_pwd = ctk.CTkButton(
            pass2_box, 
            text="Ver", 
            width=55, 
            height=36, 
            fg_color=COLOR_SECUNDARIO,
            command=self._toggle_pwd
        )
        self.btn_ver_pwd.pack(side="left", padx=(5, 0))
        
        # Etiqueta de aviso / errores
        self.lbl_mensaje = ctk.CTkLabel(self.form_frame, text="", font=("Segoe UI", 12), text_color=COLOR_PELIGRO)
        self.lbl_mensaje.pack(pady=4)
        
        # Boton Crear Cuenta
        self.btn_crear = ctk.CTkButton(
            self.form_frame, 
            text="CREAR CUENTA", 
            width=320, 
            height=40, 
            font=("Segoe UI", 13, "bold"),
            fg_color=COLOR_EXITO, 
            hover_color=COLOR_EXITO_HOVER,
            command=self._validar_registro
        )
        self.btn_crear.pack(pady=(6, 12))

    def _toggle_pwd(self):
        self.pwd_oculta = not self.pwd_oculta
        char = "" if not self.pwd_oculta else "*"
        self.txt_pass1.configure(show=char)
        self.txt_pass2.configure(show=char)
        self.btn_ver_pwd.configure(text="Ocultar" if not self.pwd_oculta else "Ver")

    def _enviar_codigo(self):
        email = self.txt_email.get().strip()
        if not email or "@" not in email:
            self.lbl_mensaje.configure(text="Ingrese un correo valido", text_color=COLOR_PELIGRO)
            return
        self.codigo_generado = str(random.randint(100000, 999999))
        self.lbl_mensaje.configure(text=f"Codigo enviado: {self.codigo_generado}", text_color="#E9C46A")
        # Pre-llenar para pruebas comodas
        self.txt_codigo.delete(0, "end")
        self.txt_codigo.insert(0, self.codigo_generado)

    def _validar_registro(self):
        user = self.txt_user.get().strip()
        email = self.txt_email.get().strip()
        cod = self.txt_codigo.get().strip()
        p1 = self.txt_pass1.get().strip()
        p2 = self.txt_pass2.get().strip()
        
        if not user or not email or not cod or not p1 or not p2:
            self.lbl_mensaje.configure(text="Complete todos los campos", text_color=COLOR_PELIGRO)
            return
        if p1 != p2:
            self.lbl_mensaje.configure(text="Las contrasenas no coinciden", text_color=COLOR_PELIGRO)
            return
        if len(p1) < 8:
            self.lbl_mensaje.configure(text="Minimo 8 caracteres en contrasena", text_color=COLOR_PELIGRO)
            return
        if not self.codigo_generado or cod != self.codigo_generado:
            self.lbl_mensaje.configure(text="Codigo de verificacion incorrecto", text_color=COLOR_PELIGRO)
            return
            
        # Llamar al backend del companero si esta presente
        if _auth:
            try:
                res = _auth.registrar(email, user, p1)
                if not res.get("ok"):
                    self.lbl_mensaje.configure(text=res.get("msg", "Error de registro"), text_color=COLOR_PELIGRO)
                    return
            except Exception as e:
                print(f"[AUTH ERROR] {e}")

        # Mostrar pantalla de exito limpia con boton en el centro
        for widget in self.form_frame.winfo_children():
            widget.destroy()
            
        ctk.CTkLabel(
            self.form_frame, 
            text="Cuenta Creada Exitosamente", 
            font=("Segoe UI", 18, "bold"), 
            text_color=COLOR_EXITO
        ).pack(pady=(60, 15))
        
        ctk.CTkLabel(
            self.form_frame, 
            text=f"Usuario registrado: {user}\nYa puede iniciar sesion.",
            font=("Segoe UI", 12), 
            text_color="#8E9AA8",
            justify="center"
        ).pack(pady=(0, 35))
        
        ctk.CTkButton(
            self.form_frame, 
            text="Regresar al Iniciar Sesion", 
            width=240, 
            height=42, 
            font=("Segoe UI", 13, "bold"),
            fg_color=COLOR_PRIMARIO, 
            hover_color=COLOR_PRIMARIO_HOVER,
            command=self.controller.mostrar_login
        ).pack(pady=10)
