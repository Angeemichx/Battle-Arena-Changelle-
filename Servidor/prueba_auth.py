import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent  
sys.path.insert(0, str(BASE))


from Servidor.adapters.json_repository import JsonRepository
from Servidor.use_cases.auth_service import AuthService

ruta = BASE / "Servidor" / "infraestructure" / "data" / "usuarios_prueba.json"
if ruta.exists():
    ruta.unlink()         
auth = AuthService(JsonRepository(str(ruta)))

print("1. Registro ok:        ", auth.registrar("ana@correo.com", "ana", "clave1234"))
print("2. Correo repetido:    ", auth.registrar("ana@correo.com", "otra", "clave1234"))
print("3. Correo inválido:    ", auth.registrar("mal-correo", "x", "clave1234"))
print("4. Contraseña débil:   ", auth.registrar("a@correo.com", "asd", "corta"))

print("5. Login sin verificar:", auth.login("ana@correo.com", "clave1234"))

codigo = auth.registrar("c@correo.com", "carla", "clave1234")["codigo"]
print("6. Verificar mal:      ", auth.verificar("c@correo.com", "000000"))
print("7. Verificar bien:     ", auth.verificar("c@correo.com", codigo))
print("8. Login correcto:     ", auth.login("c@correo.com", "clave1234"))
print("9. Login clave mala:   ", auth.login("c@correo.com", "incorrecta1"))