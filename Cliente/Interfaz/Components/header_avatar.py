"""
Componente de cabecera con el avatar activo y nombre de usuario.
Cumple con el criterio de aceptacion CA-06.5 exigido en la especificacion.
"""
import customtkinter as ctk
from Cliente.Interfaz.Components.ui_helpers import COLOR_TEXTO, COLOR_PANEL


# =============================================================================
# Documentacion de Clase: HeaderAvatar
# Proposito:
#   Renderizar una barra superior persistente en las vistas administrativas que
#   muestra el recuadro con el color activo de la hitbox del piloto, su nombre
#   de usuario y un boton opcional para cerrar la sesion activa.
# Contenido:
#   - Atributos principales: avatar_box (CTkFrame), lbl_usuario (CTkLabel),
#     btn_logout (CTkButton opcional).
#   - Metodos: __init__ (constructor de interfaz) y actualizar (refresca nombre y color).
# =============================================================================
class HeaderAvatar(ctk.CTkFrame):
    def __init__(self, master, usuario: str, color_avatar: str, on_logout=None, **kwargs):
        """
        Descripcion:
            Inicializa la barra de cabecera con el indicador de color del avatar, el nombre
            del piloto autenticado y el boton de cierre de sesion.
        Entradas:
            master (ctk.CTk | ctk.CTkFrame): Contenedor padre donde se empaquetara la cabecera.
            usuario (str): Nombre del piloto autenticado actualmente.
            color_avatar (str): Codigo hexadecimal (#RRGGBB) del color seleccionado para la hitbox.
            on_logout (callable | None): Funcion callback ejecutada al presionar 'Cerrar Sesion'.
            **kwargs (dict): Argumentos adicionales pasados al constructor de CTkFrame.
        Salidas:
            None: Construye e inserta los widgets dentro del contenedor padre.
        Restricciones:
            color_avatar debe ser un color hexadecimal valido soportado por CustomTkinter.
        """
        super().__init__(master, height=50, fg_color=COLOR_PANEL, corner_radius=0, **kwargs)
        # Se desactiva pack_propagate para mantener una altura fija de 50 px en cualquier resolucion
        self.pack_propagate(False)

        # Recuadro del color de Avatar activo (representa la hitbox funcional del jugador)
        self.avatar_box = ctk.CTkFrame(self, width=30, height=30, fg_color=color_avatar, corner_radius=4)
        self.avatar_box.pack(side="left", padx=(15, 10), pady=10)
        self.avatar_box.pack_propagate(False)

        # Etiqueta con el nombre del jugador autenticado
        self.lbl_usuario = ctk.CTkLabel(
            self,
            text=f"Piloto: {usuario}",
            font=("Segoe UI", 13, "bold"),
            text_color=COLOR_TEXTO,
        )
        self.lbl_usuario.pack(side="left", pady=10)

        # Solo se renderiza el boton de cierre de sesion si la vista proporciona un callback
        if on_logout:
            self.btn_logout = ctk.CTkButton(
                self,
                text="Cerrar Sesion",
                width=100,
                height=28,
                fg_color="#2B2D42",
                hover_color="#3B3E5B",
                font=("Segoe UI", 11),
                command=on_logout,
            )
            self.btn_logout.pack(side="right", padx=15)

    def actualizar(self, usuario: str, color_avatar: str) -> None:
        """
        Descripcion:
            Actualiza dinamicamente el texto del nombre de usuario y el color del recuadro
            del avatar sin necesidad de reconstruir la cabecera.
        Entradas:
            usuario (str): Nuevo nombre de usuario a mostrar en la etiqueta.
            color_avatar (str): Nuevo color hexadecimal (#RRGGBB) para el recuadro del avatar.
        Salidas:
            None: Modifica las propiedades visuales de los widgets existentes.
        Restricciones:
            Los widgets lbl_usuario y avatar_box deben seguir activos en la ventana.
        """
        self.lbl_usuario.configure(text=f"Piloto: {usuario}")
        self.avatar_box.configure(fg_color=color_avatar)
