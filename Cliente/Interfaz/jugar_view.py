"""
Ventana de Salas de Partida (JUGAR).
Permite crear partida (Anfitrion) o unirse a una existente por IP y Puerto.
"""
import customtkinter as ctk
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

        # Marco principal
        frame = ctk.CTkFrame(self, fg_color=COLOR_PANEL, corner_radius=12)
        frame.pack(padx=25, pady=15, fill="both", expand=True)

        ctk.CTkLabel(
            frame,
            text="SELECCION DE PARTIDA",
            font=("Segoe UI", 18, "bold"),
            text_color=COLOR_TEXTO,
        ).pack(pady=(20, 15))

        # SECCION A: CREAR SALA (HOST)
        box_host = ctk.CTkFrame(frame, fg_color="#181A20", corner_radius=8)
        box_host.pack(padx=20, pady=8, fill="x")

        ctk.CTkLabel(
            box_host,
            text="CREAR SALA (ANFITRION)",
            font=("Segoe UI", 12, "bold"),
            text_color=COLOR_EXITO,
        ).pack(pady=(10, 2))

        ip_detectada = self.controller.ip_servidor
        ctk.CTkLabel(
            box_host,
            text=f"Direccion IP asignada: {ip_detectada} : {self.controller.puerto_servidor}",
            font=("Segoe UI", 11),
            text_color="#E9C46A",
        ).pack(pady=2)

        ctk.CTkButton(
            box_host,
            text="CREAR SALA",
            width=240,
            height=36,
            font=("Segoe UI", 12, "bold"),
            fg_color=COLOR_EXITO,
            hover_color=COLOR_EXITO_HOVER,
            command=self._crear_sala,
        ).pack(pady=(6, 12))

        # SECCION B: UNIRSE A SALA EXISTENTE
        box_join = ctk.CTkFrame(frame, fg_color="#181A20", corner_radius=8)
        box_join.pack(padx=20, pady=8, fill="x")

        ctk.CTkLabel(
            box_join,
            text="UNIRSE A PARTIDA",
            font=("Segoe UI", 12, "bold"),
            text_color="#4A90E2",
        ).pack(pady=(10, 2))

        self.txt_ip = ctk.CTkEntry(box_join, placeholder_text="IP del Host", width=240, height=34)
        self.txt_ip.insert(0, "127.0.0.1")
        self.txt_ip.pack(pady=4)

        self.txt_puerto = ctk.CTkEntry(box_join, placeholder_text="Puerto", width=240, height=34)
        self.txt_puerto.insert(0, str(self.controller.puerto_servidor))
        self.txt_puerto.pack(pady=4)

        ctk.CTkButton(
            box_join,
            text="CONECTAR A SALA",
            width=240,
            height=36,
            font=("Segoe UI", 12, "bold"),
            fg_color=COLOR_PRIMARIO,
            hover_color=COLOR_PRIMARIO_HOVER,
            command=self._unirse_sala,
        ).pack(pady=(6, 12))

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
