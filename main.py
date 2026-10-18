"""
Battle Arena Challenge - Punto de Entrada Principal (Cliente).
Ejecuta el Controlador Maestro ubicado en Cliente/Interfaz/root.py.
"""
import sys
from pathlib import Path

# Asegurar que el directorio raiz este en sys.path para importaciones absolutas limpias
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from Cliente.Interfaz.root import AppController

if __name__ == "__main__":
    app = AppController()
    app.ejecutar()
