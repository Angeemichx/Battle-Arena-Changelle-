"""
Battle Arena Challenge - Punto de Entrada Principal (Cliente).
Inicializa la ruta base del proyecto y lanza el Controlador Maestro (AppController).
"""
import sys
from pathlib import Path

# Se inserta el directorio raiz en sys.path para garantizar que las importaciones absolutas
# del paquete Cliente funcionen independientemente del directorio de trabajo actual.
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from Cliente.Interfaz.root import AppController


def iniciar_programa() -> None:
    """
    Descripcion:
        Instancia el controlador maestro de la aplicacion y arranca el ciclo principal
        de la interfaz grafica en la ventana de inicio de sesion.
    Entradas:
        Ninguna.
    Salidas:
        None: No retorna valor; mantiene activo el bucle de eventos de la ventana.
    Restricciones:
        Requiere que las dependencias CustomTkinter y Pygame esten instaladas en el entorno.
    """
    app = AppController()
    app.ejecutar()


if __name__ == "__main__":
    iniciar_programa()
