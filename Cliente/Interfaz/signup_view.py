"""
Ventana de Sign Up (Registro y Verificacion de Correo) - US-01 y US-02.
Valida formato de correo, unicidad de usuario/correo en usuarios.json,
reglas de contrasena (8+ caracteres, letras y numeros) y verificacion por codigo de 6 digitos.
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
# Documentacion de Clase: SignupView
# Proposito:
#   Presentar el formulario de creacion de cuenta nueva, permitiendo solicitar un
#   codigo de verificacion de 6 digitos para el correo electronico, validar las
#   politicas de seguridad de la contrasena y persistir la cuenta verificada en
#   usuarios.json a traves de ClienteAuthAdapter.
# Contenido:
#   - Atributos principales: controller (AppController), pwd_oculta (bool),
#     txt_user (CTkEntry), txt_email (CTkEntry), txt_codigo (CTkEntry),
#     txt_pass1 (CTkEntry), txt_pass2 (CTkEntry), alerta_box (CTkFrame),
#     lbl_mensaje (CTkLabel) y btn_crear (CTkButton).
#   - Metodos: __init__, _toggle_pwd, _mostrar_aviso, _enviar_codigo y _validar_registro.
# =============================================================================
class SignupView(ctk.CTk):
    def __init__(self, controller):
        """
        Descripcion:
            Inicializa la ventana de registro de cuenta adaptada a las dimensiones del
            monitor y construye los campos de entrada y botones de verificacion.
        Entradas:
            controller (AppController): Instancia del controlador maestro de la aplicacion.
        Salidas:
            None: Configura y empaqueta los widgets de SignupView.
        Restricciones:
            controller debe contar con auth_adapter inicializado.
        """
        super().__init__()
        self.controller = controller

        self.title("Battle Arena - Registro de Cuenta")
        adaptar_ventana_ctk(self, porcentaje_w=0.42, porcentaje_h=0.80, min_w=490, min_h=660)
        self.resizable(True, True)
        ctk.set_appearance_mode("dark")

        self.pwd_oculta = True

        # Barra superior con boton Regresar a la izquierda
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
            text="CREAR CUENTA NUEVA",
            font=("Segoe UI", 20, "bold"),
            text_color=COLOR_TEXTO,
        ).pack(pady=(14, 8))

        # Campo Usuario
        ctk.CTkLabel(self.form_frame, text="Nombre de Usuario (Unico)", font=("Segoe UI", 12)).pack(
            anchor="w", padx=45, pady=(2, 0)
        )
        self.txt_user = ctk.CTkEntry(self.form_frame, placeholder_text="Ej: PilotoAlfa", width=330, height=36)
        self.txt_user.pack(pady=(2, 6))

        # Campo Gmail + Boton Enviar Codigo
        ctk.CTkLabel(self.form_frame, text="Correo Electronico (Gmail)", font=("Segoe UI", 12)).pack(
            anchor="w", padx=45, pady=(2, 0)
        )
        email_box = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        email_box.pack(pady=(2, 6))

        self.txt_email = ctk.CTkEntry(email_box, placeholder_text="usuario@gmail.com", width=215, height=36)
        self.txt_email.pack(side="left")

        self.btn_enviar_cod = ctk.CTkButton(
            email_box,
            text="Enviar Codigo",
            width=110,
            height=36,
            fg_color="#3A6073",
            hover_color="#2B4654",
            command=self._enviar_codigo,
        )
        self.btn_enviar_cod.pack(side="left", padx=(5, 0))

        # Campo Codigo recibido
        ctk.CTkLabel(self.form_frame, text="Codigo de Verificacion (6 digitos)", font=("Segoe UI", 12)).pack(
            anchor="w", padx=45, pady=(2, 0)
        )
        self.txt_codigo = ctk.CTkEntry(
            self.form_frame, placeholder_text="Ingrese el codigo enviado al correo", width=330, height=36
        )
        self.txt_codigo.pack(pady=(2, 6))

        # Contrasena 1
        ctk.CTkLabel(
            self.form_frame, text="Contrasena (min. 8 caracteres, letras y numeros)", font=("Segoe UI", 12)
        ).pack(anchor="w", padx=45, pady=(2, 0))
        self.txt_pass1 = ctk.CTkEntry(self.form_frame, placeholder_text="Contrasena", show="*", width=330, height=36)
        self.txt_pass1.pack(pady=(2, 6))

        # Contrasena 2 + Boton Ver/Ocultar
        ctk.CTkLabel(self.form_frame, text="Confirmar Contrasena", font=("Segoe UI", 12)).pack(
            anchor="w", padx=45, pady=(2, 0)
        )
        pass2_box = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        pass2_box.pack(pady=(2, 6))

        self.txt_pass2 = ctk.CTkEntry(
            pass2_box, placeholder_text="Repita la contrasena", show="*", width=270, height=36
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
            wraplength=300,
            justify="center",
        )
        self.lbl_mensaje.pack(padx=10, pady=8)

        # Boton Crear Cuenta
        self.btn_crear = ctk.CTkButton(
            self.form_frame,
            text="VERIFICAR Y CREAR CUENTA",
            width=330,
            height=42,
            font=("Segoe UI", 13, "bold"),
            fg_color=COLOR_EXITO,
            hover_color=COLOR_EXITO_HOVER,
            command=self._validar_registro,
        )
        self.btn_crear.pack(pady=(8, 12))

    def _toggle_pwd(self) -> None:
        """
        Descripcion:
            Conmuta la visualizacion de ambos campos de contrasena entre asteriscos ('*')
            y caracteres legibles.
        Entradas:
            Ninguna.
        Salidas:
            None: Actualiza txt_pass1, txt_pass2 y el texto de btn_ver_pwd.
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
            Muestra un banner estilizado encima del boton de creacion de cuenta; en color
            rojo si se trata de un rechazo de validacion o en verde si es informativo.
        Entradas:
            texto (str): Mensaje que se mostrara al usuario.
            es_error (bool): True para estilo de error (rojo); False para estilo de exito (verde).
        Salidas:
            None: Configura y empaqueta alerta_box.
        Restricciones:
            Ninguna.
        """
        if es_error:
            self.alerta_box.configure(fg_color="#3B181E", border_color=COLOR_PELIGRO)
            self.lbl_mensaje.configure(text=texto, text_color="#FF858D")
        else:
            self.alerta_box.configure(fg_color="#18362F", border_color=COLOR_EXITO)
            self.lbl_mensaje.configure(text=texto, text_color="#7CE8D8")
        self.alerta_box.pack(padx=40, pady=(4, 4), fill="x", before=self.btn_crear)

    def _enviar_codigo(self) -> None:
        """
        Descripcion:
            Solicita a ClienteAuthAdapter la generacion y envio del codigo de verificacion
            de 6 digitos para el correo y nombre de usuario ingresados.
        Entradas:
            Ninguna.
        Salidas:
            None: Muestra en el banner el resultado de la solicitud del codigo.
        Restricciones:
            Rechaza la operacion si el correo tiene formato invalido o si el usuario/correo
            ya estan registrados en usuarios.json.
        """
        user = self.txt_user.get().strip()
        email = self.txt_email.get().strip()
        res = self.controller.auth_adapter.enviar_codigo_verificacion(email, user)
        if not res.get("ok"):
            self._mostrar_aviso(res.get("msg", "Error al generar codigo."), es_error=True)
            return
        self._mostrar_aviso(res.get("msg", "Codigo enviado."), es_error=False)

    def _validar_registro(self) -> None:
        """
        Descripcion:
            Recopila todos los campos del formulario, valida el codigo de 6 digitos y las
            reglas de contrasena, y si el registro es exitoso muestra la pantalla de
            confirmacion con enlace directo al Login.
        Entradas:
            Ninguna.
        Salidas:
            None: Guarda la cuenta verificada en usuarios.json o muestra un error notorio.
        Restricciones:
            Exige haber solicitado previamente el codigo de verificacion de 6 digitos.
        """
        user = self.txt_user.get().strip()
        email = self.txt_email.get().strip()
        cod = self.txt_codigo.get().strip()
        p1 = self.txt_pass1.get().strip()
        p2 = self.txt_pass2.get().strip()

        res = self.controller.auth_adapter.registrar_y_verificar(email, user, p1, p2, cod)
        if not res.get("ok"):
            self._mostrar_aviso(res.get("msg", "Error en el registro."), es_error=True)
            return

        # Se limpian los widgets del formulario para presentar la confirmacion de cuenta verificada
        for widget in self.form_frame.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.form_frame,
            text="¡Cuenta Creada Exitosamente!",
            font=("Segoe UI", 20, "bold"),
            text_color=COLOR_EXITO,
        ).pack(pady=(65, 12))

        ctk.CTkLabel(
            self.form_frame,
            text=(
                f"Piloto registrado: {user}\n"
                f"Correo verificado: {email.lower()}\n\n"
                "Su cuenta ha sido guardada en el sistema.\n"
                "Ahora puede iniciar sesion con sus credenciales."
            ),
            font=("Segoe UI", 13),
            text_color="#A8B4C4",
            justify="center",
        ).pack(pady=(0, 35))

        ctk.CTkButton(
            self.form_frame,
            text="Regresar a Iniciar Sesion",
            width=250,
            height=44,
            font=("Segoe UI", 13, "bold"),
            fg_color=COLOR_PRIMARIO,
            hover_color=COLOR_PRIMARIO_HOVER,
            command=self.controller.mostrar_login,
        ).pack(pady=10)
