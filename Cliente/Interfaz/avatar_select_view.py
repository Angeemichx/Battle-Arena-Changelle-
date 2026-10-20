"""
Ventana de Seleccion y Configuracion del Avatar (US-06).
Construida en CustomTkinter con estetica espacial moderna en modo oscuro.
Permite elegir entre los 5 colores obligatorios de hitbox o cargar una imagen desde disco.
"""
from __future__ import annotations
import os
from pathlib import Path
import customtkinter as ctk
from PIL import Image

from Cliente.Interfaz.Components.ui_helpers import (
    COLOR_EXITO, COLOR_EXITO_HOVER,
    COLOR_PANEL, COLOR_PRIMARIO, COLOR_PRIMARIO_HOVER,
    COLOR_SECUNDARIO, COLOR_SECUNDARIO_HOVER,
    COLOR_TEXTO, COLORES_AVATAR,
    adaptar_ventana_ctk,
)


# =============================================================================
# Documentacion de Clase: AvatarSelectView
# Proposito:
#   Implementar la ventana en CustomTkinter para la seleccion del color del
#   traje Hazmat y hitbox oficial del jugador entre los 5 colores obligatorios.
# Contenido:
#   - Atributos principales: controller (AppController), color_temp (str),
#     preview_box (CTkFrame) y lbl_info (CTkLabel).
#   - Metodos: __init__, _actualizar_previsualizacion, _seleccionar_color y _guardar_y_volver.
# =============================================================================
class AvatarSelectView(ctk.CTk):
    def __init__(self, controller):
        """
        Descripcion:
            Inicializa la ventana de seleccion de avatar adaptada a la resolucion de pantalla,
            mostrando la previsualizacion en vivo del operador Hazmat y la paleta de 5 colores oficiales.
        Entradas:
            controller (AppController): Instancia del controlador maestro de la aplicacion.
        Salidas:
            None: Construye y despliega los widgets de la interfaz grafica.
        Restricciones:
            controller debe contar con el atributo avatar_color.
        """
        super().__init__()
        self.controller = controller
        self.color_temp = controller.avatar_color
        self.imagen_temp = getattr(controller, "avatar_imagen", None)

        self.title("Battle Arena - Seleccion de Avatar")
        adaptar_ventana_ctk(self, porcentaje_w=0.42, porcentaje_h=0.74, min_w=500, min_h=600)
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

        # Barra superior con boton Regresar
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=25, pady=(15, 0))

        ctk.CTkButton(
            top_bar,
            text="< Menu Principal",
            width=130,
            height=30,
            fg_color=COLOR_SECUNDARIO,
            hover_color=COLOR_SECUNDARIO_HOVER,
            command=self.controller.mostrar_hub,
        ).pack(side="left")

        # Marco principal contenedor con estilo de estacion nuclear
        frame = ctk.CTkFrame(self, fg_color=("#141822", "#141822"), border_width=2, border_color="#2A354D", corner_radius=12)
        frame.pack(padx=25, pady=15, fill="both", expand=True)

        ctk.CTkLabel(
            frame,
            text="CONFIGURACION DE AVATAR",
            font=("Segoe UI", 18, "bold"),
            text_color=COLOR_TEXTO,
        ).pack(pady=(16, 6))

        ctk.CTkLabel(
            frame,
            text="Selecciona el color de tu traje Hazmat de contencion radiactiva.",
            font=("Segoe UI", 11),
            text_color="#8E9AA8",
        ).pack(pady=(0, 14))

        # 1. Caja de Previsualizacion en Vivo con Operador Hazmat
        self.preview_box = ctk.CTkFrame(
            frame,
            width=130,
            height=130,
            fg_color="#181C26",
            corner_radius=10,
            border_width=3,
            border_color=self.color_temp,
        )
        self.preview_box.pack(pady=12)
        self.preview_box.pack_propagate(False)

        self.lbl_preview_img = ctk.CTkLabel(self.preview_box, text="")
        self.lbl_preview_img.pack(expand=True, fill="both")

        self.lbl_info = ctk.CTkLabel(
            frame,
            text=f"Operador Hazmat: {self.controller.obtener_nombre_color(self.color_temp)}",
            font=("Segoe UI", 13, "bold"),
            text_color="#E9C46A",
        )
        self.lbl_info.pack(pady=6)

        # 2. Paleta de los 5 colores base con iconos de personajes
        palette_frame = ctk.CTkFrame(frame, fg_color="transparent")
        palette_frame.pack(pady=16)

        self._mini_icons = {}
        for nombre, hex_c in COLORES_AVATAR.items():
            ruta_mini = (
                Path(__file__).resolve().parent.parent
                / "Recursos"
                / "Sprites"
                / "Personajes"
                / f"char_{nombre.lower()}_down.png"
            )
            img_mini = None
            if ruta_mini.exists():
                try:
                    pil_mini = Image.open(str(ruta_mini)).resize((22, 22), Image.Resampling.NEAREST)
                    img_mini = ctk.CTkImage(light_image=pil_mini, dark_image=pil_mini, size=(22, 22))
                    self._mini_icons[nombre] = img_mini
                except Exception:
                    pass

            btn = ctk.CTkButton(
                palette_frame,
                text=f" {nombre}",
                image=img_mini,
                compound="left",
                width=80,
                height=36,
                fg_color=hex_c,
                hover_color=hex_c,
                text_color="#FFFFFF" if nombre != "Amarillo" else "#1A1A1A",
                font=("Segoe UI", 11, "bold"),
                command=lambda col=hex_c: self._seleccionar_color(col),
            )
            btn.pack(side="left", padx=4)

        # 3. Opcion de Carga desde Disco (CA-06.3)
        actions_frame = ctk.CTkFrame(frame, fg_color="#181A20", corner_radius=8)
        actions_frame.pack(padx=25, pady=8, fill="x")

        box_btns = ctk.CTkFrame(actions_frame, fg_color="transparent")
        box_btns.pack(pady=8)

        ctk.CTkButton(
            box_btns,
            text="Cargar Avatar desde Disco (.png, .jpg)",
            width=220,
            height=32,
            font=("Segoe UI", 11, "bold"),
            fg_color=COLOR_PRIMARIO,
            hover_color=COLOR_PRIMARIO_HOVER,
            command=self._cargar_imagen_disco,
        ).pack(side="left", padx=4)

        self.btn_quitar_img = ctk.CTkButton(
            box_btns,
            text="Usar Traje Hazmat Oficial",
            width=180,
            height=32,
            font=("Segoe UI", 11),
            fg_color="#2B2D42",
            hover_color="#3B3E5B",
            command=self._quitar_imagen_disco,
        )
        self.btn_quitar_img.pack(side="left", padx=4)

        # 4. Boton Guardar y Aplicar
        ctk.CTkButton(
            frame,
            text="GUARDAR Y APLICAR",
            width=240,
            height=40,
            font=("Segoe UI", 13, "bold"),
            fg_color=COLOR_EXITO,
            hover_color=COLOR_EXITO_HOVER,
            command=self._guardar_y_volver,
        ).pack(pady=(12, 10))

        # Sincronizar visual inicial
        self._actualizar_previsualizacion()

    def _actualizar_previsualizacion(self) -> None:
        """
        Descripcion:
            Refresca el cuadro de previsualizacion con la imagen de disco (CA-06.3)
            o con el personaje Hazmat oficial correspondiente al color activo.
        Entradas:
            Ninguna.
        Salidas:
            None: Modifica los componentes visuales de preview_box y lbl_info.
        Restricciones:
            Requiere Pillow para renderizar imagenes en CustomTkinter.
        """
        nombre_color = self.controller.obtener_nombre_color(self.color_temp)

        # Caso A: Si existe imagen de disco personalizada cargada (CA-06.3)
        if self.imagen_temp and os.path.exists(self.imagen_temp):
            try:
                pil_img = Image.open(self.imagen_temp).resize((110, 110))
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(110, 110))
                self.lbl_preview_img.configure(image=ctk_img, text="")
                self.preview_box.configure(fg_color="#181A20", border_color=self.color_temp)
                self.lbl_info.configure(
                    text=f"Avatar Personalizado: {os.path.basename(self.imagen_temp)} | Color: {nombre_color}"
                )
                return
            except Exception as e:
                print(f"[AVATAR_SELECT] No se pudo cargar imagen previa: {e}")

        # Caso B: Sprite oficial del Operador Hazmat segun el color elegido
        ruta_char = (
            Path(__file__).resolve().parent.parent
            / "Recursos"
            / "Sprites"
            / "Personajes"
            / f"char_{nombre_color.lower()}_down.png"
        )
        if ruta_char.exists():
            try:
                pil_char = Image.open(str(ruta_char)).resize((110, 110), Image.Resampling.NEAREST)
                ctk_char = ctk.CTkImage(light_image=pil_char, dark_image=pil_char, size=(110, 110))
                self.lbl_preview_img.configure(image=ctk_char, text="")
                self.preview_box.configure(fg_color="#181C26", border_color=self.color_temp)
                self.lbl_info.configure(text=f"Operador Hazmat Activo: {nombre_color} ({self.color_temp})")
                return
            except Exception as e:
                print(f"[AVATAR_SELECT] Error cargando sprite de operador: {e}")

        # Respaldo con color plano si no se encuentra el asset
        self.lbl_preview_img.configure(image=None, text="")
        self.preview_box.configure(fg_color=self.color_temp, border_color="#FFFFFF")
        self.lbl_info.configure(text=f"Hitbox activa: {nombre_color} ({self.color_temp})")

    def _cargar_imagen_disco(self) -> None:
        """
        Descripcion:
            Abre el cuadro de dialogo del sistema operativo para seleccionar una imagen de avatar (CA-06.3).
        Entradas:
            Ninguna.
        Salidas:
            None: Actualiza imagen_temp si el usuario elige un archivo valido.
        Restricciones:
            Solo admite formatos de imagen .png, .jpg, .jpeg y .bmp.
        """
        import tkinter.filedialog as filedialog
        ruta = filedialog.askopenfilename(
            title="Seleccionar Imagen de Avatar (CA-06.3)",
            filetypes=[("Imagenes", "*.png;*.jpg;*.jpeg;*.bmp")],
        )
        if ruta:
            self.imagen_temp = ruta
            self._actualizar_previsualizacion()

    def _quitar_imagen_disco(self) -> None:
        """
        Descripcion:
            Elimina la asociacion a la imagen de disco para volver a usar exclusivamente el traje Hazmat oficial.
        Entradas:
            Ninguna.
        Salidas:
            None: Restablece imagen_temp a None y refresca la vista.
        Restricciones:
            Ninguna.
        """
        self.imagen_temp = None
        self._actualizar_previsualizacion()

    def _seleccionar_color(self, hex_color: str) -> None:
        """
        Descripcion:
            Actualiza el color temporal de la hitbox al presionar uno de los 5 botones de la paleta.
        Entradas:
            hex_color (str): Codigo hexadecimal del color seleccionado (#RRGGBB).
        Salidas:
            None: Actualiza el estado local y redibuja la previsualizacion.
        Restricciones:
            hex_color debe ser un string hexadecimal valido.
        """
        self.color_temp = hex_color
        self._actualizar_previsualizacion()

    def _guardar_y_volver(self) -> None:
        """
        Descripcion:
            Persiste la seleccion del avatar en la sesion y en config_local.json (CA-06.4),
            retornando de inmediato al Menu Principal (HubView).
        Entradas:
            Ninguna.
        Salidas:
            None: Transfiere el flujo de ejecucion a controller.mostrar_hub().
        Restricciones:
            controller debe tener implementado guardar_config_local().
        """
        self.controller.avatar_color = self.color_temp
        self.controller.avatar_imagen = self.imagen_temp
        self.controller.guardar_config_local()
        self.controller.mostrar_hub()
