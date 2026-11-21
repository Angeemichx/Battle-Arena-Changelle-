"""
Ventana de Estadisticas, Ranking Global e Historial de Partidas.
Decorada con la estetica de estacion nuclear y reutilizable (reciclada) sin reconstruir.
"""
from pathlib import Path
from PIL import Image
import customtkinter as ctk
from Cliente.Interfaz.Components.ui_helpers import (
    COLOR_PRIMARIO, COLOR_PRIMARIO_HOVER,
    COLOR_SECUNDARIO, COLOR_SECUNDARIO_HOVER,
    COLOR_TEXTO, adaptar_ventana_ctk,
)


# =============================================================================
# Documentacion de Clase: EstadisticasView
# Proposito:
#   Desplegar la ventana de Ranking Global e Historial de Partidas del jugador
#   con estetica de estacion nuclear, permitiendo reciclar la instancia visual
#   cuando ya fue creada previamente para evitar reconstrucciones innecesarias.
# Contenido:
#   - Atributos principales: controller (AppController), caja_rank (CTkTextbox),
#     caja_hist (CTkTextbox), bg_img (CTkImage), ic_bar, ic_rad, ic_perf.
#   - Metodos: __init__, _regresar y _cargar.
# =============================================================================
class EstadisticasView(ctk.CTkToplevel):
    def __init__(self, controller, master=None):
        """
        Descripcion:
            Inicializa la ventana de estadisticas decorada con sprites de estacion
            nuclear, construyendo las tarjetas de Ranking Global y Mi Historial.
        Entradas:
            controller (AppController): Instancia del controlador maestro de la aplicacion.
            master (ctk.CTk | None): Ventana padre que contiene el ciclo principal de Tk.
        Salidas:
            None: Construye y empaqueta los controles visuales de EstadisticasView.
        Restricciones:
            controller debe contar con auth_adapter y usuario_actual inicializados.
        """
        super().__init__(master=master)
        self.controller = controller

        self.title("Battle Arena - Estadísticas y Ranking")
        adaptar_ventana_ctk(self, porcentaje_w=0.45, porcentaje_h=0.80, min_w=520, min_h=640)
        self.resizable(True, True)
        ctk.set_appearance_mode("dark")

        # Al pulsar la X, ocultar en lugar de destruir para reciclar la ventana
        self.protocol("WM_DELETE_WINDOW", self._regresar)

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

        self.ic_bar = _cargar_img("hazard_stripe_bar.png", (380, 8))
        self.ic_rad = _cargar_img("icon_radioactive.png", (26, 26))
        self.ic_perf = _cargar_img("icon_perfil.png", (24, 24))

        # Barra superior con boton Regresar
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=25, pady=(14, 0))

        ctk.CTkButton(
            top_bar,
            text="< Regresar",
            width=120,
            height=30,
            fg_color=COLOR_SECUNDARIO,
            hover_color=COLOR_SECUNDARIO_HOVER,
            command=self._regresar,
        ).pack(side="left")

        # Marco principal con estetica de estacion nuclear
        frame = ctk.CTkFrame(
            self,
            fg_color=("#141822", "#141822"),
            border_width=2,
            border_color="#2A354D",
            corner_radius=12,
        )
        frame.pack(padx=25, pady=12, fill="both", expand=True)

        ctk.CTkLabel(
            frame,
            text="ESTADISTICAS DE COMBATE",
            font=("Segoe UI", 18, "bold"),
            text_color=COLOR_TEXTO,
        ).pack(pady=(14, 4))

        if self.ic_bar:
            ctk.CTkLabel(frame, image=self.ic_bar, text="").pack(pady=(0, 8))

        # Seccion A: Ranking Global con borde dorado y sprite radiactivo
        box_rank = ctk.CTkFrame(
            frame,
            fg_color="#181C26",
            border_width=2,
            border_color="#E9C46A",
            corner_radius=10,
        )
        box_rank.pack(padx=18, pady=6, fill="x")

        header_rank = ctk.CTkFrame(box_rank, fg_color="transparent")
        header_rank.pack(pady=(8, 4))
        if self.ic_rad:
            ctk.CTkLabel(header_rank, image=self.ic_rad, text="").pack(side="left", padx=6)
        ctk.CTkLabel(
            header_rank,
            text="RANKING GLOBAL",
            font=("Segoe UI", 14, "bold"),
            text_color="#E9C46A",
        ).pack(side="left")

        self.caja_rank = ctk.CTkTextbox(
            box_rank,
            height=155,
            font=("Consolas", 12),
            fg_color="#10141D",
            border_width=1,
            border_color="#2A354D",
        )
        self.caja_rank.pack(padx=14, pady=(2, 10), fill="x")

        # Seccion B: Mi Historial con borde azul y sprite de piloto
        box_hist = ctk.CTkFrame(
            frame,
            fg_color="#181C26",
            border_width=2,
            border_color="#4A90E2",
            corner_radius=10,
        )
        box_hist.pack(padx=18, pady=6, fill="both", expand=True)

        header_hist = ctk.CTkFrame(box_hist, fg_color="transparent")
        header_hist.pack(pady=(8, 4))
        if self.ic_perf:
            ctk.CTkLabel(header_hist, image=self.ic_perf, text="").pack(side="left", padx=6)
        ctk.CTkLabel(
            header_hist,
            text="MI HISTORIAL",
            font=("Segoe UI", 14, "bold"),
            text_color="#4A90E2",
        ).pack(side="left")

        self.caja_hist = ctk.CTkTextbox(
            box_hist,
            height=175,
            font=("Consolas", 12),
            fg_color="#10141D",
            border_width=1,
            border_color="#2A354D",
        )
        self.caja_hist.pack(padx=14, pady=(2, 10), fill="both", expand=True)

        if self.ic_bar:
            ctk.CTkLabel(frame, image=self.ic_bar, text="").pack(pady=(4, 4))

        ctk.CTkButton(
            frame,
            text="Regresar al Menú Principal",
            width=220,
            height=36,
            font=("Segoe UI", 12, "bold"),
            fg_color=COLOR_PRIMARIO,
            hover_color=COLOR_PRIMARIO_HOVER,
            command=self._regresar,
        ).pack(pady=(4, 12))

        self.after(100, self._cargar)

    def _regresar(self) -> None:
        """
        Descripcion:
            Oculta la ventana de estadisticas con withdraw() para conservarla reciclable
            en memoria y restaura la visibilidad de la ventana padre anterior.
        Entradas:
            Ninguna.
        Salidas:
            None: Oculta EstadisticasView y reactiva la ventana de origen o el Hub.
        Restricciones:
            Si la ventana padre ya no existe, delega la navegacion a controller.mostrar_hub().
        """
        try:
            self.withdraw()
        except Exception:
            pass
        ventana_padre = getattr(self.controller, "ventana_actual", None)
        if ventana_padre is not None:
            try:
                if ventana_padre.winfo_exists():
                    ventana_padre.deiconify()
                    ventana_padre.lift()
                    ventana_padre.focus_force()
                    return
            except Exception:
                pass
        self.controller.mostrar_hub()

    def _cargar(self) -> None:
        """
        Descripcion:
            Consulta a auth_adapter el Ranking Global y el historial del usuario actual,
            limpia los cuadros de texto previos y muestra los datos actualizados.
        Entradas:
            Ninguna.
        Salidas:
            None: Actualiza el contenido de caja_rank y caja_hist en solo lectura.
        Restricciones:
            auth_adapter debe responder diccionarios con la clave booleana 'ok'.
        """
        ad = self.controller.auth_adapter
        rk = ad.obtener_ranking()
        hs = ad.obtener_historial(self.controller.usuario_actual)

        if not rk.get("ok"):
            texto_rk = rk.get("msg", "No se pudo cargar el ranking.")
        else:
            filas = [
                f"{i+1:>2}. {r['nombre']:<16} V:{r['victorias']:<3} "
                f"P:{r['partidas']:<3} Pts:{r['puntos']}"
                for i, r in enumerate(rk.get("ranking", []))
            ]
            texto_rk = "\n".join(filas) or "Aún no hay partidas registradas."

        self.caja_rank.configure(state="normal")
        self.caja_rank.delete("1.0", "end")
        self.caja_rank.insert("1.0", texto_rk)
        self.caja_rank.configure(state="disabled")

        if not hs.get("ok"):
            texto_hs = hs.get("msg", "No se pudo cargar el historial.")
        else:
            filas = [
                f"{h['fecha'][:16].replace('T', ' ')}  {h['resultado']:<8} "
                f"{h['puntos']:>4} pts  vs {', '.join(h['rivales']) or '-'}"
                for h in hs.get("historial", [])
            ]
            texto_hs = "\n".join(filas) or "Aún no has jugado partidas."

        self.caja_hist.configure(state="normal")
        self.caja_hist.delete("1.0", "end")
        self.caja_hist.insert("1.0", texto_hs)
        self.caja_hist.configure(state="disabled")
