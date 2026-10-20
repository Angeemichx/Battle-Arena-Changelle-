"""
Ventana de Login (Inicio de Sesion) - US-03.
Valida credenciales contra usuarios.json mediante ClienteAuthAdapter.
Incluye un unico boton 'ACCESO ADMIN' que lleva a una ventana de autorizacion
donde se solicita la contrasena (oculta) y se elige entre Admin 1 o Admin 2,
verificando si alguno ya esta conectado en otro ordenador.
"""
import customtkinter as ctk
from pathlib import Path
from PIL import Image
from Cliente.Interfaz.Components.ui_helpers import (
    COLOR_PANEL, COLOR_PRIMARIO, COLOR_PRIMARIO_HOVER,
    COLOR_SECUNDARIO, COLOR_TEXTO, COLOR_PELIGRO,
    adaptar_ventana_ctk,
)


# =============================================================================
# Documentacion de Clase: LoginView
# Proposito:
#   Renderizar la ventana principal de Inicio de Sesion para usuarios registrados,
#   mostrar mensajes notorios de rechazo cuando la cuenta no existe o las credenciales
#   son invalidas, y ofrecer navegacion hacia el registro (Sign Up) o hacia la
#   ventana de autorizacion de Administrador (AdminAccessView).
# Contenido:
#   - Atributos principales: controller (AppController), txt_usuario (CTkEntry),
#     txt_password (CTkEntry), btn_ver (CTkButton), alerta_box (CTkFrame),
#     lbl_error (CTkLabel), btn_login (CTkButton), btn_signup (CTkButton) y
#     btn_admin (CTkButton).
#   - Metodos: __init__, _toggle_ver, _mostrar_rechazo y _ejecutar_login.
# =============================================================================
class LoginView(ctk.CTk):
    def __init__(self, controller):
        """
        Descripcion:
            Construye la interfaz grafica de Inicio de Sesion adaptada a las dimensiones
            del monitor y enlaza los controles con el controlador maestro.
        Entradas:
            controller (AppController): Instancia del controlador maestro de la aplicacion.
        Salidas:
            None: Inicializa los widgets de la ventana LoginView.
        Restricciones:
            controller debe poseer una instancia valida de auth_adapter.
        """
        super().__init__()
        self.controller = controller

        self.title("Battle Arena - Iniciar Sesion")
        adaptar_ventana_ctk(self, porcentaje_w=0.39, porcentaje_h=0.74, min_w=460, min_h=580)
        self.resizable(True, True)
        ctk.set_appearance_mode("dark")

        # Fondo ambiental de estacion nuclear
        ruta_bg = Path(__file__).resolve().parent.parent / "Recursos" / "Sprites" / "UI" / "bg_nuclear_station.png"
        if ruta_bg.exists():
            try:
                pil_bg = Image.open(str(ruta_bg))
                self.bg_img = ctk.CTkImage(light_image=pil_bg, dark_image=pil_bg, size=(900, 750))
                self.lbl_bg = ctk.CTkLabel(self, image=self.bg_img, text="")
                self.lbl_bg.place(x=0, y=0, relwidth=1, relheight=1)
            except Exception:
                pass

        # Contenedor central del formulario con estetica de estacion de reactor
        self.frame = ctk.CTkFrame(self, fg_color=("#141822", "#141822"), border_width=2, border_color="#2A354D", corner_radius=12)
        self.frame.pack(padx=30, pady=24, fill="both", expand=True)

        # Logotipo oficial del juego: letras puras transparentes sin caja de fondo
        ruta_logo = Path(__file__).resolve().parent.parent / "Recursos" / "Sprites" / "UI" / "logo_letras_puras.png"
        if ruta_logo.exists():
            try:
                pil_logo = Image.open(str(ruta_logo))
                self.img_logo = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(300, 58))
                ctk.CTkLabel(self.frame, image=self.img_logo, text="").pack(pady=(16, 12))
            except Exception:
                self.img_logo = None
        else:
            self.img_logo = None

        if not self.img_logo:
            ctk.CTkLabel(
                self.frame,
                text="BATTLE ARENA",
                font=("Segoe UI", 24, "bold"),
                text_color=COLOR_TEXTO,
            ).pack(pady=(20, 4))
            ctk.CTkLabel(
                self.frame,
                text="Control del Reactor",
                font=("Segoe UI", 13),
                text_color="#8E9AA8",
            ).pack(pady=(0, 16))

        # Campo Usuario
        ctk.CTkLabel(self.frame, text="Usuario o Correo Registrado", font=("Segoe UI", 12)).pack(
            anchor="w", padx=45, pady=(4, 0)
        )
        self.txt_usuario = ctk.CTkEntry(
            self.frame,
            placeholder_text="Ingrese su usuario o correo",
            width=320,
            height=38,
        )
        self.txt_usuario.pack(pady=(2, 10))

        # Campo Contrasena
        ctk.CTkLabel(self.frame, text="Contrasena", font=("Segoe UI", 12)).pack(anchor="w", padx=45, pady=(4, 0))

        pwd_box = ctk.CTkFrame(self.frame, fg_color="transparent")
        pwd_box.pack(pady=(2, 10))

        self.txt_password = ctk.CTkEntry(
            pwd_box,
            placeholder_text="Ingrese contrasena",
            show="*",
            width=260,
            height=38,
        )
        self.txt_password.pack(side="left")

        self.btn_ver = ctk.CTkButton(
            pwd_box,
            text="Ver",
            width=55,
            height=38,
            fg_color=COLOR_SECUNDARIO,
            command=self._toggle_ver,
        )
        self.btn_ver.pack(side="left", padx=(5, 0))
        self.pwd_oculta = True

        # Recuadro notorio de rechazo / alerta (permanece oculto hasta que ocurra un fallo)
        self.alerta_box = ctk.CTkFrame(
            self.frame,
            fg_color="#3B181E",
            corner_radius=8,
            border_width=2,
            border_color=COLOR_PELIGRO,
        )
        self.lbl_error = ctk.CTkLabel(
            self.alerta_box,
            text="",
            text_color="#FF858D",
            font=("Segoe UI", 12, "bold"),
            wraplength=290,
            justify="center",
        )
        self.lbl_error.pack(padx=12, pady=10)

        # Boton Iniciar Sesion
        self.btn_login = ctk.CTkButton(
            self.frame,
            text="INICIAR SESION",
            width=320,
            height=42,
            font=("Segoe UI", 13, "bold"),
            fg_color=COLOR_PRIMARIO,
            hover_color=COLOR_PRIMARIO_HOVER,
            command=self._ejecutar_login,
        )
        self.btn_login.pack(pady=(12, 8))

        # Enlace a Sign Up
        self.btn_signup = ctk.CTkButton(
            self.frame,
            text="¿No tiene cuenta? Crear Cuenta Nueva (Sign Up)",
            fg_color="transparent",
            text_color="#4A90E2",
            hover=False,
            font=("Segoe UI", 12, "underline"),
            command=self.controller.mostrar_signup,
        )
        self.btn_signup.pack(pady=(2, 12))

        # Unico boton que redirige a la ventana independiente de Acceso Admin con icono
        ruta_badge = Path(__file__).resolve().parent.parent / "Recursos" / "Sprites" / "UI" / "badge_admin.png"
        self.ic_badge = None
        if ruta_badge.exists():
            try:
                pil_badge = Image.open(str(ruta_badge))
                self.ic_badge = ctk.CTkImage(light_image=pil_badge, dark_image=pil_badge, size=(20, 20))
            except Exception:
                pass

        self.btn_admin = ctk.CTkButton(
            self.frame,
            text="  ACCESO ADMIN",
            image=self.ic_badge,
            compound="left",
            width=200,
            height=36,
            font=("Segoe UI", 12, "bold"),
            fg_color=COLOR_SECUNDARIO,
            hover_color="#3B4254",
            command=self.controller.mostrar_admin_login,
        )
        self.btn_admin.pack(pady=(6, 10))

    def _toggle_ver(self) -> None:
        """
        Descripcion:
            Alterna la visibilidad del campo de contrasena entre texto plano y asteriscos ('*').
        Entradas:
            Ninguna.
        Salidas:
            None: Actualiza la propiedad show de txt_password y el texto de btn_ver.
        Restricciones:
            Ninguna.
        """
        self.pwd_oculta = not self.pwd_oculta
        self.txt_password.configure(show="" if not self.pwd_oculta else "*")
        self.btn_ver.configure(text="Ocultar" if not self.pwd_oculta else "Ver")

    def _mostrar_rechazo(self, mensaje: str) -> None:
        """
        Descripcion:
            Empaqueta y hace visible el recuadro rojo de rechazo notorio justo encima del
            boton de inicio de sesion.
        Entradas:
            mensaje (str): Explicacion detallada del motivo por el cual se rechazo el acceso.
        Salidas:
            None: Modifica el texto de lbl_error y muestra alerta_box.
        Restricciones:
            mensaje no debe ser una cadena vacia.
        """
        self.lbl_error.configure(text=mensaje)
        self.alerta_box.pack(padx=40, pady=(4, 6), fill="x", before=self.btn_login)

    def _ejecutar_login(self) -> None:
        """
        Descripcion:
            Extrae las credenciales ingresadas, las valida a traves de ClienteAuthAdapter
            y, si son correctas, inicia la sesion del piloto y abre el Menu Principal (HubView).
        Entradas:
            Ninguna.
        Salidas:
            None: Redirige al Hub o despliega un mensaje de rechazo notorio.
        Restricciones:
            Bloquea el ingreso si el usuario no existe en usuarios.json, si la contrasena
            no coincide o si la cuenta ya esta conectada en otro ordenador.
        """
        identificador = self.txt_usuario.get().strip()
        pwd = self.txt_password.get().strip()

        resultado = self.controller.auth_adapter.iniciar_sesion(identificador, pwd, controller=self.controller)
        if not resultado.get("ok"):
            self._mostrar_rechazo(resultado.get("msg", "Error de autenticacion."))
            return

        self.controller.usuario_actual = resultado["username"]
        self.controller.email_actual = resultado["email"]
        self.controller.mostrar_hub()


# =============================================================================
# Documentacion de Clase: AdminAccessView
# Proposito:
#   Proporcionar una ventana independiente para el acceso rapido de pruebas como
#   'Admin 1' o 'Admin 2', exigiendo primero digitar la contrasena oculta (sin
#   mostrarla jamas en pantalla) y verificando contra el servidor/sala que ningun
#   otro ordenador este utilizando ya ese perfil de administrador.
# Contenido:
#   - Atributos principales: controller (AppController), txt_pwd_admin (CTkEntry),
#     alerta_box (CTkFrame), lbl_error (CTkLabel), btn_admin1 (CTkButton) y
#     btn_admin2 (CTkButton).
#   - Metodos: __init__, _mostrar_rechazo y _intentar_ingreso_admin.
# =============================================================================
class AdminAccessView(ctk.CTk):
    def __init__(self, controller):
        """
        Descripcion:
            Inicializa la ventana de autorizacion de Administrador, intenta sincronizar el
            estado de red TCP para detectar perfiles ya ocupados y dibuja los controles.
        Entradas:
            controller (AppController): Instancia del controlador maestro de la aplicacion.
        Salidas:
            None: Construye los widgets de AdminAccessView.
        Restricciones:
            Nunca revela la contrasena esperada en etiquetas ni placeholders.
        """
        super().__init__()
        self.controller = controller

        # Se intenta enlazar con el servidor TCP para conocer si otro ordenador ya ocupo Admin 1 o Admin 2
        try:
            self.controller.conectar_servidor_tcp()
        except Exception:
            pass

        self.title("Battle Arena - Acceso de Administrador")
        adaptar_ventana_ctk(self, porcentaje_w=0.38, porcentaje_h=0.68, min_w=450, min_h=500)
        self.resizable(True, True)
        ctk.set_appearance_mode("dark")

        self.frame = ctk.CTkFrame(self, fg_color=COLOR_PANEL, corner_radius=12)
        self.frame.pack(padx=30, pady=24, fill="both", expand=True)

        ctk.CTkLabel(
            self.frame,
            text="ACCESO ADMINISTRADOR",
            font=("Segoe UI", 22, "bold"),
            text_color=COLOR_TEXTO,
        ).pack(pady=(22, 4))

        ctk.CTkLabel(
            self.frame,
            text="Ingrese la contrasena de administrador y seleccione el perfil disponible",
            font=("Segoe UI", 12),
            text_color="#8E9AA8",
            wraplength=340,
            justify="center",
        ).pack(pady=(0, 18))

        ctk.CTkLabel(self.frame, text="Contrasena de Administrador", font=("Segoe UI", 12)).pack(
            anchor="w", padx=45, pady=(4, 0)
        )

        self.txt_pwd_admin = ctk.CTkEntry(
            self.frame,
            placeholder_text="Ingrese contrasena",
            show="*",
            width=310,
            height=40,
        )
        self.txt_pwd_admin.pack(pady=(4, 14))

        # Recuadro de rechazo notorio (clave incorrecta o Admin ya conectado en otro ordenador)
        self.alerta_box = ctk.CTkFrame(
            self.frame,
            fg_color="#3B181E",
            corner_radius=8,
            border_width=2,
            border_color=COLOR_PELIGRO,
        )
        self.lbl_error = ctk.CTkLabel(
            self.alerta_box,
            text="",
            text_color="#FF858D",
            font=("Segoe UI", 12, "bold"),
            wraplength=290,
            justify="center",
        )
        self.lbl_error.pack(padx=12, pady=10)

        self.btns_container = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.btns_container.pack(pady=(10, 14))

        # Verificacion de disponibilidad de cada perfil Admin en la red o sala
        admin1_ocupado = self.controller.auth_adapter.verificar_usuario_en_uso("Admin 1", self.controller)
        admin2_ocupado = self.controller.auth_adapter.verificar_usuario_en_uso("Admin 2", self.controller)

        txt_a1 = "ADMIN 1 (EN USO)" if admin1_ocupado else "ENTRAR COMO ADMIN 1"
        txt_a2 = "ADMIN 2 (EN USO)" if admin2_ocupado else "ENTRAR COMO ADMIN 2"

        self.btn_admin1 = ctk.CTkButton(
            self.btns_container,
            text=txt_a1,
            width=310,
            height=42,
            font=("Segoe UI", 13, "bold"),
            fg_color="#5A2A2E" if admin1_ocupado else "#2A9D8F",
            hover_color="#6E3237" if admin1_ocupado else "#21867A",
            command=lambda: self._intentar_ingreso_admin("Admin 1"),
        )
        self.btn_admin1.pack(pady=(0, 10))

        self.btn_admin2 = ctk.CTkButton(
            self.btns_container,
            text=txt_a2,
            width=310,
            height=42,
            font=("Segoe UI", 13, "bold"),
            fg_color="#5A2A2E" if admin2_ocupado else COLOR_PRIMARIO,
            hover_color="#6E3237" if admin2_ocupado else COLOR_PRIMARIO_HOVER,
            command=lambda: self._intentar_ingreso_admin("Admin 2"),
        )
        self.btn_admin2.pack(pady=(0, 6))

        ctk.CTkButton(
            self.frame,
            text="Volver al Inicio de Sesion",
            width=220,
            height=34,
            fg_color=COLOR_SECUNDARIO,
            command=self.controller.mostrar_login,
        ).pack(pady=(12, 10))

    def _mostrar_rechazo(self, mensaje: str) -> None:
        """
        Descripcion:
            Despliega el recuadro de alerta roja en la ventana de administrador cuando la
            contrasena falla o el perfil elegido ya esta ocupado en otro ordenador.
        Entradas:
            mensaje (str): Texto descriptivo del motivo del rechazo.
        Salidas:
            None: Actualiza lbl_error y empaqueta alerta_box.
        Restricciones:
            Ninguna.
        """
        self.lbl_error.configure(text=mensaje)
        self.alerta_box.pack(padx=40, pady=(4, 8), fill="x", before=self.btns_container)

    def _intentar_ingreso_admin(self, perfil_admin: str) -> None:
        """
        Descripcion:
            Verifica la contrasena digitada y la disponibilidad del perfil seleccionado
            ('Admin 1' o 'Admin 2'); si todo es valido, inicia sesion y abre el Hub.
        Entradas:
            perfil_admin (str): Nombre del perfil seleccionado ('Admin 1' o 'Admin 2').
        Salidas:
            None: Abre HubView o muestra el mensaje de rechazo correspondiente.
        Restricciones:
            Exige haber ingresado la contrasena previamente y que ningun otro ordenador
            este conectado con el mismo perfil Admin.
        """
        pwd = self.txt_pwd_admin.get().strip()
        if not pwd:
            self._mostrar_rechazo("ACCESO RECHAZADO: Debe ingresar la contrasena antes de elegir el perfil Admin.")
            return

        resultado = self.controller.auth_adapter.iniciar_sesion(
            perfil_admin,
            pwd,
            controller=self.controller,
        )
        if not resultado.get("ok"):
            self._mostrar_rechazo(resultado.get("msg", "Error al validar acceso de administrador."))
            return

        self.controller.usuario_actual = resultado["username"]
        self.controller.email_actual = resultado["email"]
        self.controller.mostrar_hub()
