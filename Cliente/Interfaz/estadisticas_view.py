import customtkinter as ctk
from Cliente.Interfaz.Components.ui_helpers import (
    COLOR_PRIMARIO, COLOR_PRIMARIO_HOVER, COLOR_TEXTO, adaptar_ventana_ctk,
)


class EstadisticasView(ctk.CTk):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.title("Battle Arena - Estadísticas")
        adaptar_ventana_ctk(self, porcentaje_w=0.45, porcentaje_h=0.80, min_w=520, min_h=640)
        self.resizable(True, True)
        ctk.set_appearance_mode("dark")

        frame = ctk.CTkFrame(self, fg_color="#141822", border_width=2,
                             border_color="#2A354D", corner_radius=12)
        frame.pack(padx=25, pady=20, fill="both", expand=True)

        ctk.CTkLabel(frame, text="RANKING GLOBAL", font=("Segoe UI", 18, "bold"),
                     text_color=COLOR_TEXTO).pack(pady=(14, 4))
        self.caja_rank = ctk.CTkTextbox(frame, height=180, font=("Consolas", 12))
        self.caja_rank.pack(padx=20, fill="x")

        ctk.CTkLabel(frame, text="MI HISTORIAL", font=("Segoe UI", 18, "bold"),
                     text_color=COLOR_TEXTO).pack(pady=(14, 4))
        self.caja_hist = ctk.CTkTextbox(frame, height=220, font=("Consolas", 12))
        self.caja_hist.pack(padx=20, fill="both", expand=True)

        ctk.CTkButton(frame, text="Regresar", width=200, height=36,
                      fg_color=COLOR_PRIMARIO, hover_color=COLOR_PRIMARIO_HOVER,
                      command=self.controller.mostrar_perfil).pack(pady=14)

        self.after(100, self._cargar)

    def _cargar(self):
        ad = self.controller.auth_adapter
        rk = ad.obtener_ranking()
        hs = ad.obtener_historial(self.controller.usuario_actual)

        if not rk.get("ok"):
            texto = rk.get("msg", "No se pudo cargar el ranking.")
        else:
            filas = [f"{i+1:>2}. {r['nombre']:<16} V:{r['victorias']:<3} "
                     f"P:{r['partidas']:<3} Pts:{r['puntos']}"
                     for i, r in enumerate(rk.get("ranking", []))]
            texto = "\n".join(filas) or "Aún no hay partidas registradas."
        self.caja_rank.insert("1.0", texto)
        self.caja_rank.configure(state="disabled")

        if not hs.get("ok"):
            texto = hs.get("msg", "No se pudo cargar el historial.")
        else:
            filas = [f"{h['fecha'][:16].replace('T', ' ')}  {h['resultado']:<8} "
                     f"{h['puntos']:>4} pts  vs {', '.join(h['rivales']) or '-'}"
                     for h in hs.get("historial", [])]
            texto = "\n".join(filas) or "Aún no has jugado partidas."
        self.caja_hist.insert("1.0", texto)
        self.caja_hist.configure(state="disabled")