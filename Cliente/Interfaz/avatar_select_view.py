"""
Ventana de Seleccion y Configuracion del Avatar (US-06).
Construida en CustomTkinter con estetica espacial moderna en modo oscuro.
Permite elegir entre los 5 colores obligatorios de hitbox o cargar una imagen desde disco.
"""
from __future__ import annotations
import os
import tkinter.filedialog as filedialog
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
#   Implementar la ventana en CustomTkinter exigida en la especificacion tecnica
#   para la historia US-06, permitiendo seleccionar uno de los 5 colores base de
#   la hitbox del avatar o cargar una imagen personalizada desde el almacenamiento local.
# Contenido:
#   - Atributos principales: controller (AppController), color_temp (str),
#     imagen_temp (str | None), preview_frame (CTkFrame) y lbl_info (CTkLabel).
#   - Metodos: __init__, _actualizar_previsualizacion, _seleccionar_color,
#     _cargar_imagen_disco, _quitar_imagen_disco y _guardar_y_volver.
# =============================================================================
class AvatarSelectView(ctk.CTk):
    def __init__(self, controller):
        """
        Descripcion:
            Inicializa la ventana de seleccion de avatar adaptada a la resolucion de pantalla,
            mostrando la previsualizacion en vivo, la paleta de 5 colores y el boton de carga desde disco.
        Entradas:
            controller (AppController): Instancia del controlador maestro de la aplicacion.
        Salidas:
            None: Construye y despliega los widgets de la interfaz grafica.
        Restricciones:
            controller debe contar con los atributos avatar_color y avatar_imagen.
        """
        super().__init__()
        self.controller = controller
        self.color_temp = controller.avatar_color
        self.imagen_temp = controller.avatar_imagen

        self.title("Battle Arena - Seleccion de Avatar")
        adaptar_ventana_ctk(self, porcentaje_w=0.42, porcentaje_h=0.74, min_w=500, min_h=600)
        self.resizable(True, True)
        ctk.set_appearance_mode("dark")

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

        # Marco principal contenedor
        frame = ctk.CTkFrame(self, fg_color=COLOR_PANEL, corner_radius=12)
        frame.pack(padx=25, pady=15, fill="both", expand=True)

        ctk.CTkLabel(
            frame,
            text="CONFIGURACION DE AVATAR (US-06)",
            font=("Segoe UI", 18, "bold"),
            text_color=COLOR_TEXTO,
        ).pack(pady=(18, 10))

        ctk.CTkLabel(
            frame,
            text="Elige tu color de hitbox espacial o carga una imagen personalizada.",
            font=("Segoe UI", 11),
            text_color="#8E9AA8",
        ).pack(pady=(0, 15))

        # 1. Caja de Previsualizacion en Vivo
        self.preview_box = ctk.CTkFrame(
            frame,
            width=90,
            height=90,
            fg_color=self.color_temp,
            corner_radius=8,
            border_width=3,
            border_color="#FFFFFF",
        )
        self.preview_box.pack(pady=10)
        self.preview_box.pack_propagate(False)

        self.lbl_preview_img = ctk.CTkLabel(self.preview_box, text="")
        self.lbl_preview_img.pack(expand=True, fill="both")

        self.lbl_info = ctk.CTkLabel(
            frame,
            text=f"Color seleccionado: {self.controller.obtener_nombre_color(self.color_temp)}",
            font=("Segoe UI", 12, "bold"),
            text_color="#E9C46A",
        )
        self.lbl_info.pack(pady=5)

        # 2. Paleta de los 5 colores base obligatorios (CA-06.1 y CA-06.2)
        palette_frame = ctk.CTkFrame(frame, fg_color="transparent")
        palette_frame.pack(pady=12)

        for nombre, hex_c in COLORES_AVATAR.items():
            btn = ctk.CTkButton(
                palette_frame,
                text=nombre,
                width=75,
                height=34,
                fg_color=hex_c,
                hover_color=hex_c,
                text_color="#FFFFFF" if nombre != "Amarillo" else "#1A1A1A",
                font=("Segoe UI", 11, "bold"),
                command=lambda col=hex_c: self._seleccionar_color(col),
            )
            btn.pack(side="left", padx=5)

        # 3. Carga desde Disco (CA-06.3)
        actions_frame = ctk.CTkFrame(frame, fg_color="#181A20", corner_radius=8)
        actions_frame.pack(padx=30, pady=12, fill="x")

        ctk.CTkButton(
            actions_frame,
            text="Cargar Avatar desde Disco (.png, .jpg)",
            width=260,
            height=34,
            font=("Segoe UI", 11, "bold"),
            fg_color=COLOR_PRIMARIO,
            hover_color=COLOR_PRIMARIO_HOVER,
            command=self._cargar_imagen_disco,
        ).pack(pady=(12, 6))

        self.btn_quitar_img = ctk.CTkButton(
            actions_frame,
            text="Usar Solo Hitbox de Color",
            width=200,
            height=28,
            font=("Segoe UI", 10),
            fg_color="#2B2D42",
            hover_color="#3B3E5B",
            command=self._quitar_imagen_disco,
        )
        self.btn_quitar_img.pack(pady=(0, 12))

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
        ).pack(pady=(15, 10))

        # Sincronizar visual inicial
        self._actualizar_previsualizacion()

    def _actualizar_previsualizacion(self) -> None:
        """
        Descripcion:
            Refresca el cuadro de previsualizacion con la imagen cargada o con el color de la hitbox.
        Entradas:
            Ninguna.
        Salidas:
            None: Modifica los componentes visuales de preview_box y lbl_info.
        Restricciones:
            Requiere Pillow para renderizar imagenes en CustomTkinter.
        """
        nombre_color = self.controller.obtener_nombre_color(self.color_temp)
        if self.imagen_temp and os.path.exists(self.imagen_temp):
            try:
                pil_img = Image.open(self.imagen_temp).resize((84, 84))
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(84, 84))
                self.lbl_preview_img.configure(image=ctk_img, text="")
                self.preview_box.configure(fg_color="#181A20")
                self.lbl_info.configure(
                    text=f"Color base: {nombre_color} | Imagen: {os.path.basename(self.imagen_temp)}"
                )
                return
            except Exception as e:
                print(f"[AVATAR_SELECT] No se pudo cargar imagen previa: {e}")

        # Sin imagen de disco: se muestra el color solido de la hitbox
        self.lbl_preview_img.configure(image=None, text="")
        self.preview_box.configure(fg_color=self.color_temp)
        self.lbl_info.configure(text=f"Hitbox activa: {nombre_color} ({self.color_temp})")

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
        ruta = filedialog.askopenfilename(
            title="Seleccionar Imagen de Avatar",
            filetypes=[("Imagenes", "*.png;*.jpg;*.jpeg;*.bmp")],
        )
        if ruta:
            self.imagen_temp = ruta
            self._actualizar_previsualizacion()

    def _quitar_imagen_disco(self) -> None:
        """
        Descripcion:
            Elimina la asociacion a la imagen de disco para volver a usar exclusivamente la hitbox de color.
        Entradas:
            Ninguna.
        Salidas:
            None: Restablece imagen_temp a None y refresca la vista.
        Restricciones:
            Ninguna.
        """
        self.imagen_temp = None
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
