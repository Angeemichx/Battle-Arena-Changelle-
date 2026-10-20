"""
Ventana de Salas de Partida (JUGAR).
Permite crear partida (Anfitrion) o unirse a una existente por IP y Puerto.
"""
import customtkinter as ctk
from pathlib import Path
from PIL import Image
from Cliente.Interfaz.Components.ui_helpers import (
    COLOR_PANEL, COLOR_PRIMARIO, COLOR_PRIMARIO_HOVER,
    COLOR_SECUNDARIO, COLOR_SECUNDARIO_HOVER,
    COLOR_EXITO, COLOR_EXITO_HOVER, COLOR_TEXTO,
    adaptar_ventana_ctk,
)


# =============================================================================
# Documentacion de Clase: JugarView
# Proposito:
#   Permitir al jugador elegir entre crear una nueva sala como Anfitrion (Host)
#   mostrando su direccion IP local y puerto asignado, o unirse como Invitado
#   a una sala existente ingresando la IP y el puerto del servidor.
# Contenido:
#   - Atributos principales: controller (AppController), txt_ip (CTkEntry) y
#     txt_puerto (CTkEntry).
#   - Metodos: __init__, _crear_sala y _unirse_sala.
# =============================================================================
class JugarView(ctk.CTk):
    def __init__(self, controller):
        """
        Descripcion:
            Inicializa la ventana de seleccion de sala adaptada a la resolucion del monitor,
            mostrando los paneles para Crear Sala (Anfitrion) o Unirse a Partida (Invitado).
        Entradas:
            controller (AppController): Instancia del controlador maestro de la aplicacion.
        Salidas:
            None: Construye y empaqueta los controles visuales de JugarView.
        Restricciones:
            controller debe tener inicializados ip_servidor y puerto_servidor.
        """
        super().__init__()
        self.controller = controller

        self.title("Battle Arena - Salas de Partida")
        adaptar_ventana_ctk(self, porcentaje_w=0.40, porcentaje_h=0.68, min_w=480, min_h=560)
        self.resizable(True, True)
        ctk.set_appearance_mode("dark")

        base_ui = Path(__file__).resolve().parent.parent / "Recursos" / "Sprites" / "UI"

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

        def _cargar_img(nombre, size):
            p = base_ui / nombre
            if p.exists():
                try:
                    pil_i = Image.open(str(p))
                    return ctk.CTkImage(light_image=pil_i, dark_image=pil_i, size=size)
                except Exception:
                    pass
            return None

        self.ic_bar = _cargar_img("hazard_stripe_bar.png", (360, 8))
        self.ic_host = _cargar_img("icon_terminal_host.png", (28, 28))
        self.ic_join = _cargar_img("icon_terminal_join.png", (28, 28))

        # Barra superior con boton Regresar
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=25, pady=(15, 0))

        ctk.CTkButton(
            top_bar,
            text="< Menu Principal",
            width=120,
            height=30,
            fg_color=COLOR_SECUNDARIO,
            hover_color=COLOR_SECUNDARIO_HOVER,
            command=self.controller.mostrar_hub,
        ).pack(side="left")

        # Marco principal con estetica de estacion nuclear
        frame = ctk.CTkFrame(self, fg_color=("#141822", "#141822"), border_width=2, border_color="#2A354D", corner_radius=12)
        frame.pack(padx=25, pady=15, fill="both", expand=True)

        ctk.CTkLabel(
            frame,
            text="SELECCION DE PARTIDA",
            font=("Segoe UI", 18, "bold"),
            text_color=COLOR_TEXTO,
        ).pack(pady=(16, 6))

        if self.ic_bar:
            ctk.CTkLabel(frame, image=self.ic_bar, text="").pack(pady=(0, 10))

        # SECCION A: CREAR SALA (HOST) CON BORDE TEMATICO Y SPRITES
        box_host = ctk.CTkFrame(
            frame,
            fg_color="#181C26",
            border_width=2,
            border_color="#2A9D8F",
            corner_radius=10,
        )
        box_host.pack(padx=20, pady=6, fill="x")

        header_host = ctk.CTkFrame(box_host, fg_color="transparent")
        header_host.pack(pady=(8, 2))

        if self.ic_host:
            ctk.CTkLabel(header_host, image=self.ic_host, text="").pack(side="left", padx=6)

        ctk.CTkLabel(
            header_host,
            text="CREAR SALA (ANFITRION)",
            font=("Segoe UI", 12, "bold"),
            text_color="#2A9D8F",
        ).pack(side="left")

        ip_detectada = self.controller.ip_servidor
        ctk.CTkLabel(
            box_host,
            text=f"Direccion IP de transmision: {ip_detectada} : {self.controller.puerto_servidor}",
            font=("Segoe UI", 11, "bold"),
            text_color="#E9C46A",
        ).pack(pady=2)

        ctk.CTkButton(
            box_host,
            text="CREAR SALA LOCAL",
            width=240,
            height=36,
            font=("Segoe UI", 12, "bold"),
            fg_color=COLOR_EXITO,
            hover_color=COLOR_EXITO_HOVER,
            command=self._crear_sala,
        ).pack(pady=(6, 10))

        # SECCION B: UNIRSE A SALA EXISTENTE CON BORDE TEMATICO Y SPRITES
        box_join = ctk.CTkFrame(
            frame,
            fg_color="#181C26",
            border_width=2,
            border_color="#4A90E2",
            corner_radius=10,
        )
        box_join.pack(padx=20, pady=8, fill="x")

        header_join = ctk.CTkFrame(box_join, fg_color="transparent")
        header_join.pack(pady=(8, 2))

        if self.ic_join:
            ctk.CTkLabel(header_join, image=self.ic_join, text="").pack(side="left", padx=6)

        ctk.CTkLabel(
            header_join,
            text="UNIRSE A PARTIDA (CLIENTE)",
            font=("Segoe UI", 12, "bold"),
            text_color="#4A90E2",
        ).pack(side="left")

        self.txt_ip = ctk.CTkEntry(box_join, placeholder_text="IP del Host", width=240, height=34)
        self.txt_ip.insert(0, "127.0.0.1")
        self.txt_ip.pack(pady=3)

        self.txt_puerto = ctk.CTkEntry(box_join, placeholder_text="Puerto", width=240, height=34)
        self.txt_puerto.insert(0, str(self.controller.puerto_servidor))
        self.txt_puerto.pack(pady=3)

        ctk.CTkButton(
            box_join,
            text="CONECTAR A SALA",
            width=240,
            height=36,
            font=("Segoe UI", 12, "bold"),
            fg_color=COLOR_PRIMARIO,
            hover_color=COLOR_PRIMARIO_HOVER,
            command=self._unirse_sala,
        ).pack(pady=(6, 10))

        if self.ic_bar:
            ctk.CTkLabel(frame, image=self.ic_bar, text="").pack(pady=(6, 8))

    def _crear_sala(self) -> None:
        """
        Descripcion:
            Asigna al jugador local el rol de Anfitrion (es_creador = True) y realiza
            la transicion hacia el Lobby Caminable en Pygame.
        Entradas:
            Ninguna.
        Salidas:
            None: Transfiere la ejecucion a controller.entrar_al_lobby().
        Restricciones:
            Como Anfitrion, tendra permisos exclusivos para modificar el mapa y parametros.
        """
        self.controller.es_creador = True
        self.controller.entrar_al_lobby()

    def _unirse_sala(self) -> None:
        """
        Descripcion:
            Asigna al jugador local el rol de Invitado (es_creador = False), lee y valida
            la direccion IP y el puerto ingresados, y abre el Lobby Caminable.
        Entradas:
            Ninguna.
        Salidas:
            None: Actualiza ip_servidor y puerto_servidor y lanza el Lobby Caminable.
        Restricciones:
            Si el puerto escrito no es un entero valido, utiliza por defecto el puerto 5555.
        """
        self.controller.es_creador = False
        ip = self.txt_ip.get().strip() or "127.0.0.1"
        try:
            puerto = int(self.txt_puerto.get().strip() or "5555")
        except ValueError:
            puerto = 5555
        self.controller.ip_servidor = ip
        self.controller.puerto_servidor = puerto
        self.controller.entrar_al_lobby()
