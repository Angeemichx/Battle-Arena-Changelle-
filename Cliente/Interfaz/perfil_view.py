"""
Ventana de Perfil de Jugador (US-04).
Muestra los datos basicos de la cuenta: nombre de usuario, correo electronico,
estado de verificacion de correo, previsualizacion del avatar/traje Hazmat seleccionado,
y opcion de navegacion de retorno al Menu Principal (CA-05.1 y CA-05.2).
"""
from pathlib import Path
from PIL import Image
import customtkinter as ctk

from Cliente.Interfaz.Components.ui_helpers import (
    COLOR_PANEL, COLOR_PRIMARIO, COLOR_PRIMARIO_HOVER,
    COLOR_SECUNDARIO, COLOR_SECUNDARIO_HOVER,
    COLOR_EXITO, COLOR_TEXTO,
    adaptar_ventana_ctk,
)


# =============================================================================
# Documentacion de Clase: PerfilView
# Proposito:
#   Presentar el expediente de servicio y perfil del piloto autenticado (US-04),
#   mostrando su avatar actual, nombre, correo, estado de verificacion y rango.
# Contenido:
#   - Atributos principales: controller (AppController), bg_img (CTkImage),
#     lbl_bg (CTkLabel), img_avatar (CTkImage).
#   - Metodos: __init__.
# =============================================================================
class PerfilView(ctk.CTk):
    def __init__(self, controller):
        """
        Descripcion:
            Inicializa la ventana de Perfil adaptada a la pantalla del computador,
            desplegando los datos de la cuenta activa y su avatar (CA-05.1 y CA-05.2).
        Entradas:
            controller (AppController): Instancia del controlador maestro.
        Salidas:
            None: Renderiza la tarjeta de perfil.
        Restricciones:
            controller debe tener inicializado usuario_actual y avatar_color.
        """
        super().__init__()
        self.controller = controller

        self.title("Battle Arena - Perfil de Jugador")
        adaptar_ventana_ctk(self, porcentaje_w=0.42, porcentaje_h=0.78, min_w=500, min_h=620)
        self.resizable(True, True)
        ctk.set_appearance_mode("dark")

        base_ui = Path(__file__).resolve().parent.parent / "Recursos" / "Sprites" / "UI"
        base_chars = Path(__file__).resolve().parent.parent / "Recursos" / "Sprites" / "Personajes"

        # Fondo ambiental de estacion nuclear
        ruta_bg = base_ui / "bg_nuclear_station.png"
        if ruta_bg.exists():
            try:
                pil_bg = Image.open(str(ruta_bg))
                self.bg_img = ctk.CTkImage(light_image=pil_bg, dark_image=pil_bg, size=(900, 750))
                self.lbl_bg = ctk.CTkLabel(self, image=self.bg_img, text="")
                self.lbl_bg.place(x=0, y=0, relwidth=1, relheight=1)
            except Exception:
                pass

        # Barra superior con boton Regresar (CA-05.2)
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=25, pady=(15, 0))

        ctk.CTkButton(
            top_bar,
            text="< Menú Principal",
            width=130,
            height=30,
            fg_color=COLOR_SECUNDARIO,
            hover_color=COLOR_SECUNDARIO_HOVER,
            command=self.controller.mostrar_hub,
        ).pack(side="left")

        # Contenedor principal estilo terminal nuclear
        frame = ctk.CTkFrame(
            self,
            fg_color=("#141822", "#141822"),
            border_width=2,
            border_color="#2A354D",
            corner_radius=12,
        )
        frame.pack(padx=25, pady=15, fill="both", expand=True)

        ctk.CTkLabel(
            frame,
            text="EXPEDIENTE DE PILOTO (PERFIL)",
            font=("Segoe UI", 18, "bold"),
            text_color=COLOR_TEXTO,
        ).pack(pady=(16, 10))

        # Consultar datos reales de la cuenta desde el repositorio de cuentas
        email_usuario = getattr(self.controller, "email_actual", "") or "piloto@battlearena.local"
        usuario_nom = getattr(self.controller, "usuario_actual", "Piloto")
        fecha_creacion = "Activo en esta sesión"
        esta_verificado = True

        if hasattr(self.controller, "auth_adapter") and self.controller.auth_adapter:
            try:
                c = self.controller.auth_adapter.repo.get_by_username_or_email(usuario_nom)
                if c:
                    email_usuario = c.email
                    esta_verificado = c.verified
                    if c.created_at:
                        fecha_creacion = c.created_at.split("T")[0]
            except Exception:
                pass

        # 1. Marco con Previsualizacion del Avatar / Traje Hazmat Activo (CA-05.1)
        color_avatar = getattr(self.controller, "avatar_color", "#E63946")
        nom_color = self.controller.obtener_nombre_color(color_avatar)

        avatar_box = ctk.CTkFrame(
            frame,
            width=110,
            height=110,
            fg_color="#181C26",
            border_width=3,
            border_color=color_avatar,
            corner_radius=12,
        )
        avatar_box.pack(pady=(4, 6))
        avatar_box.pack_propagate(False)

        # Cargar sprite correspondiente al color actual
        ruta_sprite = base_chars / f"char_{nom_color.lower()}_down.png"
        self.img_avatar = None
        if ruta_sprite.exists():
            try:
                pil_sprite = Image.open(str(ruta_sprite)).resize((80, 80), Image.Resampling.NEAREST)
                self.img_avatar = ctk.CTkImage(light_image=pil_sprite, dark_image=pil_sprite, size=(80, 80))
            except Exception:
                pass

        if self.img_avatar:
            lbl_av = ctk.CTkLabel(avatar_box, image=self.img_avatar, text="")
        else:
            lbl_av = ctk.CTkLabel(avatar_box, text=nom_color, text_color=color_avatar, font=("Segoe UI", 14, "bold"))
        lbl_av.pack(expand=True, fill="both")

        ctk.CTkLabel(
            frame,
            text=f"Traje Hazmat: Operador {nom_color}",
            font=("Segoe UI", 11, "bold"),
            text_color="#E9C46A",
        ).pack(pady=(0, 10))

        # 2. Informacion de Cuenta y Piloto (CA-05.1)
        card_info = ctk.CTkFrame(
            frame,
            fg_color="#181C26",
            border_width=1,
            border_color="#2A354D",
            corner_radius=10,
        )
        card_info.pack(padx=30, pady=6, fill="x")

        def _fila(label: str, valor: str, color_val: str = "#E0E6ED", badge: bool = False):
            row = ctk.CTkFrame(card_info, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=6)
            ctk.CTkLabel(
                row,
                text=label,
                font=("Segoe UI", 12, "bold"),
                text_color="#8E9AA8",
                width=140,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                row,
                text=valor,
                font=("Segoe UI", 12, "bold" if badge else "normal"),
                text_color=color_val,
                anchor="w",
            ).pack(side="left", padx=5)

        _fila("Nombre de Usuario:", usuario_nom, "#39FF14")
        _fila("Correo Electrónico:", email_usuario, "#7CE8D8")

        estado_texto = "✔ Correo Verificado (Habilitado)" if esta_verificado else "⚠ Verificación Pendiente"
        estado_color = COLOR_EXITO if esta_verificado else "#E76F51"
        _fila("Estado de Correo:", estado_texto, estado_color, badge=True)

        _fila("Rango de Tripulación:", "Piloto Certificado de Arena (Reactor Guard)", "#E9C46A")
        _fila("Fecha de Registro:", fecha_creacion, "#A8B4C4")

        # 3. Boton de Retorno al Menu Principal
        ctk.CTkButton(
            frame,
            text="Regresar al Menú Principal",
            width=220,
            height=38,
            font=("Segoe UI", 12, "bold"),
            fg_color=COLOR_PRIMARIO,
            hover_color=COLOR_PRIMARIO_HOVER,
            command=self.controller.mostrar_hub,
        ).pack(pady=(16, 14))
