"""
Ventana de Recuperacion y Restablecimiento de Contrasena (US-05).
Permite al usuario ingresar su correo registrado, recibir un codigo de 6 digitos
por correo electronico y definir una nueva contrasena segura con hash bcrypt.
"""
import customtkinter as ctk
from Cliente.Interfaz.Components.ui_helpers import (
    COLOR_PANEL, COLOR_PRIMARIO, COLOR_PRIMARIO_HOVER,
    COLOR_SECUNDARIO, COLOR_SECUNDARIO_HOVER,
    COLOR_EXITO, COLOR_EXITO_HOVER,
    COLOR_PELIGRO, COLOR_TEXTO,
    adaptar_ventana_ctk,
)


# =============================================================================
# Documentacion de Clase: RecuperarPasswordView
# Proposito:
#   Ofrecer la interfaz grafica para la recuperacion de cuentas olvidadas (US-05),
#   permitiendo solicitar un codigo de seguridad temporal de 6 digitos y restablecer
#   la contrasena de acceso mediante politicas de seguridad y hash bcrypt.
# Contenido:
#   - Atributos principales: controller (AppController), pwd_oculta (bool),
#     top_bar (CTkFrame), btn_volver (CTkButton), form_frame (CTkFrame),
#     txt_email (CTkEntry), btn_enviar_cod (CTkButton), txt_codigo (CTkEntry),
#     txt_pass1 (CTkEntry), txt_pass2 (CTkEntry), btn_ver_pwd (CTkButton),
#     alerta_box (CTkFrame), lbl_mensaje (CTkLabel) y btn_restablecer (CTkButton).
#   - Metodos: __init__, _toggle_pwd, _mostrar_aviso, _solicitar_codigo y
#     _ejecutar_restablecimiento.
# =============================================================================
class RecuperarPasswordView(ctk.CTk):
    def __init__(self, controller):
        """
        Descripcion:
            Inicializa la ventana de recuperacion de contrasena adaptada a la resolucion
            del monitor, configurando los campos de correo, codigo recibido y doble
            confirmacion de la nueva clave (US-05).
        Entradas:
            controller (AppController): Instancia del controlador maestro de la aplicacion.
        Salidas:
            None: Configura e inicializa los widgets de RecuperarPasswordView.
        Restricciones:
            controller debe contar con una instancia valida de auth_adapter.
        """
        super().__init__()
        self.controller = controller

        self.title("Battle Arena - Recuperar Contraseña")
        adaptar_ventana_ctk(self, porcentaje_w=0.42, porcentaje_h=0.80, min_w=490, min_h=660)
        self.resizable(True, True)
        ctk.set_appearance_mode("dark")

        self.pwd_oculta = True

        # Barra superior con boton Regresar
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=25, pady=(15, 0))

        self.btn_volver = ctk.CTkButton(
            top_bar,
            text="< Regresar al Login",
            width=130,
            height=30,
            fg_color=COLOR_SECUNDARIO,
            hover_color=COLOR_SECUNDARIO_HOVER,
            command=self.controller.mostrar_login,
        )
        self.btn_volver.pack(side="left")

        # Marco del formulario
        self.form_frame = ctk.CTkFrame(self, fg_color=COLOR_PANEL, corner_radius=12)
        self.form_frame.pack(padx=25, pady=12, fill="both", expand=True)

        ctk.CTkLabel(
            self.form_frame,
            text="RECUPERAR CONTRASEÑA",
            font=("Segoe UI", 20, "bold"),
            text_color=COLOR_TEXTO,
        ).pack(pady=(14, 4))

        ctk.CTkLabel(
            self.form_frame,
            text="Ingrese su correo registrado para recibir un código de seguridad.",
            font=("Segoe UI", 11),
            text_color="#A8B4C4",
        ).pack(pady=(0, 10))

        # Campo Correo + Boton Enviar Codigo
        ctk.CTkLabel(self.form_frame, text="Correo Electrónico Registrado", font=("Segoe UI", 12)).pack(
            anchor="w", padx=45, pady=(2, 0)
        )
        email_box = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        email_box.pack(pady=(2, 6))

        self.txt_email = ctk.CTkEntry(email_box, placeholder_text="ejemplo@gmail.com", width=215, height=36)
        self.txt_email.pack(side="left")

        self.btn_enviar_cod = ctk.CTkButton(
            email_box,
            text="Enviar Código",
            width=110,
            height=36,
            fg_color="#3A6073",
            hover_color="#2B4654",
            command=self._solicitar_codigo,
        )
        self.btn_enviar_cod.pack(side="left", padx=(5, 0))

        # Campo Codigo de Seguridad
        ctk.CTkLabel(self.form_frame, text="Código de Seguridad (6 dígitos)", font=("Segoe UI", 12)).pack(
            anchor="w", padx=45, pady=(2, 0)
        )
        self.txt_codigo = ctk.CTkEntry(
            self.form_frame, placeholder_text="Ingrese el código enviado a su correo", width=330, height=36
        )
        self.txt_codigo.pack(pady=(2, 6))

        # Nueva Contrasena
        ctk.CTkLabel(
            self.form_frame, text="Nueva Contraseña (min. 8 caracteres, letras y números)", font=("Segoe UI", 12)
        ).pack(anchor="w", padx=45, pady=(2, 0))
        self.txt_pass1 = ctk.CTkEntry(self.form_frame, placeholder_text="Nueva contraseña", show="*", width=330, height=36)
        self.txt_pass1.pack(pady=(2, 6))

        # Confirmar Contrasena + Boton Ver/Ocultar
        ctk.CTkLabel(self.form_frame, text="Confirmar Nueva Contraseña", font=("Segoe UI", 12)).pack(
            anchor="w", padx=45, pady=(2, 0)
        )
        pass2_box = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        pass2_box.pack(pady=(2, 6))

        self.txt_pass2 = ctk.CTkEntry(
            pass2_box, placeholder_text="Repita la nueva contraseña", show="*", width=270, height=36
        )
        self.txt_pass2.pack(side="left")

        self.btn_ver_pwd = ctk.CTkButton(
            pass2_box,
            text="Ver",
            width=55,
            height=36,
            fg_color=COLOR_SECUNDARIO,
            command=self._toggle_pwd,
        )
        self.btn_ver_pwd.pack(side="left", padx=(5, 0))

        # Recuadro notorio de aviso / error
        self.alerta_box = ctk.CTkFrame(
            self.form_frame,
            fg_color="#3B181E",
            corner_radius=8,
            border_width=2,
            border_color=COLOR_PELIGRO,
        )
        self.lbl_mensaje = ctk.CTkLabel(
            self.alerta_box,
            text="",
            font=("Segoe UI", 12, "bold"),
            text_color="#FF858D",
            wraplength=310,
            justify="center",
        )
        self.lbl_mensaje.pack(padx=10, pady=8)

        # Boton Restablecer
        self.btn_restablecer = ctk.CTkButton(
            self.form_frame,
            text="ACTUALIZAR CONTRASEÑA",
            width=330,
            height=42,
            font=("Segoe UI", 13, "bold"),
            fg_color=COLOR_PRIMARIO,
            hover_color=COLOR_PRIMARIO_HOVER,
            command=self._ejecutar_restablecimiento,
        )
        self.btn_restablecer.pack(pady=(10, 12))

    def _toggle_pwd(self) -> None:
        """
        Descripcion:
            Conmuta la visualizacion de los campos de nueva contrasena entre caracteres
            legibles y asteriscos ('*').
        Entradas:
            Ninguna.
        Salidas:
            None: Actualiza el atributo show de txt_pass1 y txt_pass2.
        Restricciones:
            Ninguna.
        """
        self.pwd_oculta = not self.pwd_oculta
        char = "" if not self.pwd_oculta else "*"
        self.txt_pass1.configure(show=char)
        self.txt_pass2.configure(show=char)
        self.btn_ver_pwd.configure(text="Ocultar" if not self.pwd_oculta else "Ver")

    def _mostrar_aviso(self, texto: str, es_error: bool = True) -> None:
        """
        Descripcion:
            Despliega un banner estilizado encima del boton principal; en color rojo para
            errores de validacion o verde para notificaciones de exito.
        Entradas:
            texto (str): Mensaje que se presentara al usuario en pantalla.
            es_error (bool): True para estilo de error (rojo); False para exito (verde).
        Salidas:
            None: Configura y empaqueta el frame alerta_box.
        Restricciones:
            texto no debe ser una cadena vacia.
        """
        if es_error:
            self.alerta_box.configure(fg_color="#3B181E", border_color=COLOR_PELIGRO)
            self.lbl_mensaje.configure(text=texto, text_color="#FF858D")
        else:
            self.alerta_box.configure(fg_color="#18362F", border_color=COLOR_EXITO)
            self.lbl_mensaje.configure(text=texto, text_color="#7CE8D8")
        self.alerta_box.pack(padx=40, pady=(4, 4), fill="x", before=self.btn_restablecer)

    def _solicitar_codigo(self) -> None:
        """
        Descripcion:
            Solicita a ClienteAuthAdapter la generacion y despacho del codigo de seguridad
            de 6 digitos al correo ingresado por el usuario.
        Entradas:
            Ninguna.
        Salidas:
            None: Muestra el aviso informativo o de error en alerta_box.
        Restricciones:
            Rechaza la solicitud si el correo es invalido o si no existe en usuarios.json.
        """
        email = self.txt_email.get().strip()
        res = self.controller.auth_adapter.solicitar_codigo_recuperacion(email)
        if not res.get("ok"):
            self._mostrar_aviso(res.get("msg", "Error al enviar código."), es_error=True)
            return
        self._mostrar_aviso(res.get("msg", "Código enviado a su correo."), es_error=False)

    def _ejecutar_restablecimiento(self) -> None:
        """
        Descripcion:
            Recopila los datos ingresados, valida el codigo de seguridad y las politicas
            de contrasena, y actualiza la clave en usuarios.json a traves del adaptador.
        Entradas:
            Ninguna.
        Salidas:
            None: Despliega la pantalla de confirmacion exitosa o notifica el error ocurrido.
        Restricciones:
            Requiere coincidencia exacta del codigo de 6 digitos no expirado y contrasena valida.
        """
        email = self.txt_email.get().strip()
        codigo = self.txt_codigo.get().strip()
        p1 = self.txt_pass1.get().strip()
        p2 = self.txt_pass2.get().strip()

        res = self.controller.auth_adapter.restablecer_password(email, codigo, p1, p2)
        if not res.get("ok"):
            self._mostrar_aviso(res.get("msg", "Error al restablecer contraseña."), es_error=True)
            return

        # Confirmacion visual de restablecimiento exitoso
        for widget in self.form_frame.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.form_frame,
            text="¡Contraseña Actualizada!",
            font=("Segoe UI", 20, "bold"),
            text_color=COLOR_EXITO,
        ).pack(pady=(70, 12))

        ctk.CTkLabel(
            self.form_frame,
            text=(
                f"Cuenta: {email.lower()}\n\n"
                "Su contraseña ha sido actualizada con éxito.\n"
                "Ahora puede iniciar sesión con su nueva clave."
            ),
            font=("Segoe UI", 13),
            text_color="#A8B4C4",
            justify="center",
        ).pack(pady=(0, 35))

        ctk.CTkButton(
            self.form_frame,
            text="Iniciar Sesión",
            width=250,
            height=44,
            font=("Segoe UI", 13, "bold"),
            fg_color=COLOR_PRIMARIO,
            hover_color=COLOR_PRIMARIO_HOVER,
            command=self.controller.mostrar_login,
        ).pack(pady=10)
