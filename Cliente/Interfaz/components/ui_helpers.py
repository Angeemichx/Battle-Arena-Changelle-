"""
Constantes de color, estilos y adaptacion de dimensiones de pantalla
para la interfaz grafica. Enfoque limpio y funcional (esqueleto).
"""

# Paleta base
COLOR_FONDO = "#181A20"
COLOR_PANEL = "#22252F"
COLOR_PRIMARIO = "#1F538D"
COLOR_PRIMARIO_HOVER = "#17406E"
COLOR_SECUNDARIO = "#2B2D42"
COLOR_SECUNDARIO_HOVER = "#3B3E5B"
COLOR_EXITO = "#2A9D8F"
COLOR_EXITO_HOVER = "#217C71"
COLOR_PELIGRO = "#E63946"
COLOR_PELIGRO_HOVER = "#B82E38"
COLOR_TEXTO = "#FFFFFF"
COLOR_TEXTO_SECUNDARIO = "#A0AAB8"

# 5 Colores base de avatar obligatorios por guia
COLORES_AVATAR = {
    "Rojo": "#E63946",
    "Azul": "#1D3557",
    "Verde": "#2A9D8F",
    "Amarillo": "#E9C46A",
    "Morado": "#7209B7",
}


def adaptar_ventana_ctk(
    ventana,
    porcentaje_w: float = 0.40,
    porcentaje_h: float = 0.72,
    min_w: int = 480,
    min_h: int = 560,
) -> tuple[int, int]:
    """
    Consulta las dimensiones del monitor que esta ejecutando el programa
    y adapta el tamano y centrado de la ventana proporcionalmente.
    """
    try:
        screen_w = ventana.winfo_screenwidth()
        screen_h = ventana.winfo_screenheight()
    except Exception:
        screen_w, screen_h = 1280, 720

    win_w = max(min_w, int(screen_w * porcentaje_w))
    win_h = max(min_h, int(screen_h * porcentaje_h))
    pos_x = max(0, (screen_w - win_w) // 2)
    pos_y = max(0, (screen_h - win_h) // 2 - 20)

    ventana.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
    ventana.minsize(min_w, min_h)
    return win_w, win_h
