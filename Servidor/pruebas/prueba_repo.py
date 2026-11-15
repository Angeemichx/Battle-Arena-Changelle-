#Crea una cuenta de prueba y manda la información a data

import sys
from pathlib import Path
sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from Servidor.adapters.json_repository import JsonRepository
from Servidor.domain.cuenta import Cuenta

ruta = BASE / "Servidor" / "infraestructure" / "data" / "usuarios.json"
print("Ruta usada:", ruta)

repo = JsonRepository(str(ruta))
print("Antes:", repo._email("prueba@correo.com"))

repo.save(Cuenta(email="prueba@correo.com", username="prueba", password_hash="xxx"))
print("Después:", repo._email("prueba@correo.com"))