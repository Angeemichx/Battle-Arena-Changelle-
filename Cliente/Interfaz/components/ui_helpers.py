"""
Constantes de color, estilos y adaptacion de dimensiones de pantalla
para la interfaz grafica. Enfoque limpio y funcional (esqueleto).
"""

# Paleta base de colores de interfaz administrativa
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

# 5 Colores base de avatar obligatorios por especificacion (US-06 / CA-06.2)
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
    Descripcion:
        Consulta las dimensiones fisicas del monitor que ejecuta el programa y ajusta
        proporcionalmente el tamano y centrado de una ventana CustomTkinter.
    Entradas:
        ventana (ctk.CTk): Instancia de la ventana principal que sera redimensionada.
        porcentaje_w (float): Fraccion del ancho del monitor que ocupara la ventana (0.0 a 1.0).
        porcentaje_h (float): Fraccion del alto del monitor que ocupara la ventana (0.0 a 1.0).
        min_w (int): Ancho minimo permitido en pixeles para evitar cortes de interfaz.
        min_h (int): Alto minimo permitido en pixeles para evitar cortes de interfaz.
    Salidas:
        tuple[int, int]: Par (win_w, win_h) con el ancho y alto finales aplicados en pixeles.
    Restricciones:
        ventana debe ser una instancia valida de Tkinter/CustomTkinter; si la consulta de
        resolucion falla en sistemas sin monitor, aplica un fallback de 1280x720 px.
    """
    try:
        screen_w = ventana.winfo_screenwidth()
        screen_h = ventana.winfo_screenheight()
    except Exception:
        screen_w, screen_h = 1280, 720

    # Se garantiza que la ventana nunca sea menor que el tamano minimo operativo (min_w, min_h)
    win_w = max(min_w, int(screen_w * porcentaje_w))
    win_h = max(min_h, int(screen_h * porcentaje_h))

    # Calculo de coordenadas para centrar la ventana restando 20 px en Y por la barra de tareas
    pos_x = max(0, (screen_w - win_w) // 2)
    pos_y = max(0, (screen_h - win_h) // 2 - 20)

    ventana.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
    ventana.minsize(min_w, min_h)
    return win_w, win_h
