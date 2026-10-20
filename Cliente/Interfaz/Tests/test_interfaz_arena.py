"""
Pruebas unitarias positivas y negativas para el modulo del Integrante 1
(Colisiones de Arena y Lobby, Zona de Extraccion del Reactor, Exclusion de Colores,
Autenticacion Estricta, Acceso Admin con deteccion de sesion activa y Condicion de Victoria / Desempate).
Cumple con el Definition of Done (DoD) del Sprint 2.
"""
import pytest
import pygame

from Cliente.Interfaz.arena_collisions import (
    REACTOR_CENTER,
    REACTOR_EXTRACTION_RADIUS,
    SPAWN_POINTS,
    WORLD_HEIGHT,
    WORLD_WIDTH,
    esta_en_zona_extraccion,
    mover_con_colisiones,
    obtener_colisiones_lobby,
    obtener_hitbox_reactor,
    obtener_muros_arena,
)
from Cliente.Interfaz.arena_view import evaluar_condicion_victoria
from Cliente.Interfaz.auth_adapter import ClienteAuthAdapter
from Cliente.Interfaz.Components.ui_helpers import COLORES_AVATAR
from Cliente.Interfaz.root import AppController


# ---------- Pruebas Positivas ----------

def test_cinco_colores_avatar_obligatorios():
    """
    Descripcion:
        Verifica que el diccionario COLORES_AVATAR contenga al menos los 5 colores base
        obligatorios especificados en US-06 (CA-06.2).
    Entradas:
        Ninguna.
    Salidas:
        None: Ejecuta aserciones de existencia sobre COLORES_AVATAR.
    Restricciones:
        Falla si falta cualquiera de los colores Rojo, Azul, Verde, Amarillo o Morado.
    """
    assert len(COLORES_AVATAR) >= 5
    for nombre in ("Rojo", "Azul", "Verde", "Amarillo", "Morado"):
        assert nombre in COLORES_AVATAR


def test_dimensiones_y_spawns_arena():
    """
    Descripcion:
        Comprueba que el mapa ampliado tenga dimensiones de 3600x2600 px, el Reactor
        Central en (1800, 1300) y las 4 plataformas de Spawn configuradas (US-07).
    Entradas:
        Ninguna.
    Salidas:
        None: Ejecuta aserciones sobre constantes y muros de la Arena.
    Restricciones:
        Ninguna.
    """
    assert WORLD_WIDTH == 3600
    assert WORLD_HEIGHT == 2600
    assert REACTOR_CENTER == (1800, 1300)
    assert len(SPAWN_POINTS) == 4
    muros = obtener_muros_arena("Estacion Estandar")
    assert len(muros) >= 8


def test_movimiento_libre_sin_obstaculos():
    """
    Descripcion:
        Prueba positiva que valida que un avatar pueda desplazarse libremente cuando
        no existen muros en su trayectoria.
    Entradas:
        Ninguna.
    Salidas:
        None: Verifica que las nuevas coordenadas X e Y sumen el desplazamiento (10, 15).
    Restricciones:
        Ninguna.
    """
    jugador = pygame.Rect(1000, 200, 48, 48)
    nuevo = mover_con_colisiones(jugador, 10, 15, [])
    assert nuevo.x == 1010
    assert nuevo.y == 215


def test_deteccion_positiva_zona_extraccion_reactor():
    """
    Descripcion:
        Prueba positiva que comprueba que un jugador posicionado dentro del radio de
        extraccion del Reactor Central sea detectado correctamente.
    Entradas:
        Ninguna.
    Salidas:
        None: Verifica que esta_en_zona_extraccion retorne True.
    Restricciones:
        La distancia al centro (1800, 1300) debe ser menor o igual a REACTOR_EXTRACTION_RADIUS.
    """
    rx, ry = REACTOR_CENTER
    jugador_cerca = pygame.Rect(rx + 80, ry - 24, 48, 48)
    assert esta_en_zona_extraccion(jugador_cerca) is True


def test_color_disponible_cuando_nadie_lo_usa():
    """
    Descripcion:
        Prueba positiva que valida que el jugador local pueda seleccionar un color
        que no esta siendo ocupado por ningun otro jugador en la sala.
    Entradas:
        Ninguna.
    Salidas:
        None: Verifica que validar_color_disponible retorne True.
    Restricciones:
        Ninguna.
    """
    ctrl = AppController()
    jugadores_sala = [
        {"id": 1, "nombre": "Local", "color": "#E63946", "es_local": True},
        {"id": 2, "nombre": "Remoto", "color": "#1D3557", "es_local": False},
    ]
    assert ctrl.validar_color_disponible("#2A9D8F", jugadores_sala) is True


def test_sincronizacion_estado_red():
    """
    Descripcion:
        Prueba positiva que comprueba que actualizar_estado_red almacene de forma
        segura el diccionario de jugadores enviado por el servidor TCP.
    Entradas:
        Ninguna.
    Salidas:
        None: Verifica la cantidad de jugadores y puntaje sincronizado.
    Restricciones:
        Ninguna.
    """
    ctrl = AppController()
    paquete_servidor = {
        "tipo": "estado",
        "jugadores": [
            {"id": 1, "nombre": "Piloto1", "x": 250, "y": 300, "puntaje": 12},
            {"id": 2, "nombre": "Piloto2", "x": 450, "y": 500, "puntaje": 8},
        ],
        "activa": True,
        "ganador": None,
    }
    ctrl.actualizar_estado_red(paquete_servidor)
    assert len(ctrl.estado_partida_red["jugadores"]) == 2
    assert ctrl.estado_partida_red["jugadores"][0]["puntaje"] == 12


def test_victoria_al_alcanzar_meta_puntos():
    """
    Descripcion:
        Prueba positiva (US-16) que verifica la declaracion inmediata de victoria cuando
        un jugador alcanza la meta de 500 puntos sin empate.
    Entradas:
        Ninguna.
    Salidas:
        None: Verifica que evaluar_condicion_victoria retorne terminada=True y el ganador esperado.
    Restricciones:
        Ninguna.
    """
    jugadores = [
        {"id": 1, "nombre": "Piloto1", "puntos": 500},
        {"id": 2, "nombre": "Piloto2", "puntos": 120},
    ]
    terminada, ganador, desempate, t_rest = evaluar_condicion_victoria(jugadores, 90.0, 500)
    assert terminada is True
    assert ganador["nombre"] == "Piloto1"
    assert desempate is False


def test_desempate_automatico_suma_dos_minutos():
    """
    Descripcion:
        Prueba positiva (CA-16.4) que comprueba que cuando el tiempo llega a 0.0 con un
        empate en el primer lugar, se sumen automaticamente 120 segundos (+2 minutos).
    Entradas:
        Ninguna.
    Salidas:
        None: Verifica que desempate sea True y t_rest sea igual a 120.0.
    Restricciones:
        Ninguna.
    """
    jugadores = [
        {"id": 1, "nombre": "Piloto1", "puntos": 150},
        {"id": 2, "nombre": "Piloto2", "puntos": 150},
    ]
    terminada, ganador, desempate, t_rest = evaluar_condicion_victoria(jugadores, 0.0, 500)
    assert terminada is False
    assert ganador is None
    assert desempate is True
    assert t_rest == 120.0


# ---------- Pruebas Negativas ----------

def test_colision_bloquea_atravesar_muro():
    """
    Descripcion:
        Prueba negativa que verifica que un avatar sea detenido en el borde izquierdo
        de un muro solido al intentar atravesarlo horizontalmente.
    Entradas:
        Ninguna.
    Salidas:
        None: Comprueba que nuevo.right coincida exactamente con muro.left.
    Restricciones:
        Ninguna.
    """
    muro = pygame.Rect(200, 100, 50, 200)
    jugador = pygame.Rect(150, 150, 48, 48)  # Borde derecho en x=198
    nuevo = mover_con_colisiones(jugador, 25, 0, [muro])
    assert nuevo.right == muro.left


def test_jugador_no_puede_salir_de_limites_arena():
    """
    Descripcion:
        Prueba negativa (CA-09.1) que garantiza que el jugador no pueda salirse de los
        limites exteriores del mapa (0, 0, WORLD_WIDTH, WORLD_HEIGHT).
    Entradas:
        Ninguna.
    Salidas:
        None: Comprueba que left y top nunca sean menores a 0.
    Restricciones:
        Ninguna.
    """
    limites = pygame.Rect(0, 0, WORLD_WIDTH, WORLD_HEIGHT)
    jugador = pygame.Rect(5, 5, 48, 48)
    nuevo = mover_con_colisiones(jugador, -50, -50, [], limites)
    assert nuevo.left >= 0
    assert nuevo.top >= 0


def test_deteccion_negativa_fuera_de_zona_extraccion():
    """
    Descripcion:
        Prueba negativa que comprueba que un jugador alejado del Reactor Central no
        active la extraccion de energia.
    Entradas:
        Ninguna.
    Salidas:
        None: Verifica que esta_en_zona_extraccion retorne False.
    Restricciones:
        Ninguna.
    """
    jugador_lejos = pygame.Rect(200, 200, 48, 48)
    assert esta_en_zona_extraccion(jugador_lejos) is False


def test_color_bloqueado_si_otro_jugador_lo_ocupa():
    """
    Descripcion:
        Prueba negativa (CA-10.3) que verifica que validar_color_disponible rechace
        la seleccion de un color que ya pertenece a otro jugador en la sala.
    Entradas:
        Ninguna.
    Salidas:
        None: Verifica que validar_color_disponible retorne False.
    Restricciones:
        Ninguna.
    """
    ctrl = AppController()
    jugadores_sala = [
        {"id": 1, "nombre": "Local", "color": "#E63946", "es_local": True},
        {"id": 2, "nombre": "Remoto", "color": "#1D3557", "es_local": False},
    ]
    assert ctrl.validar_color_disponible("#1D3557", jugadores_sala) is False


def test_rechazo_inicio_sesion_cuenta_inexistente(tmp_path):
    """
    Descripcion:
        Prueba negativa (US-03) que comprueba el rechazo notorio de inicio de sesion
        cuando se intenta ingresar con una cuenta no registrada en usuarios.json.
    Entradas:
        tmp_path (Path): Fixture de pytest que provee un directorio temporal aislado.
    Salidas:
        None: Verifica que ok sea False y el mensaje contenga 'ACCESO RECHAZADO'.
    Restricciones:
        Ninguna.
    """
    archivo_temp = tmp_path / "usuarios_test.json"
    auth = ClienteAuthAdapter(json_path=str(archivo_temp))
    res = auth.iniciar_sesion("usuario_fantasma", "ClaveSegura123")
    assert res["ok"] is False
    assert "ACCESO RECHAZADO" in res["msg"]


def test_acceso_rapido_admin_1_y_admin_2(tmp_path):
    """
    Descripcion:
        Comprueba que los perfiles de prueba 'Admin 1' y 'Admin 2' permitan el acceso
        al proporcionar la contrasena correcta, rechacen claves invalidas sin revelar
        la contrasena y bloqueen el acceso si otro ordenador ya usa ese perfil Admin.
    Entradas:
        tmp_path (Path): Fixture de pytest con directorio temporal.
    Salidas:
        None: Ejecuta aserciones positivas y negativas sobre iniciar_sesion.
    Restricciones:
        Ninguna.
    """
    archivo_temp = tmp_path / "usuarios_test.json"
    auth = ClienteAuthAdapter(json_path=str(archivo_temp))
    ctrl = AppController()

    r1 = auth.iniciar_sesion("Admin 1", "1234", controller=ctrl)
    assert r1["ok"] is True
    assert r1["username"] == "Admin 1"

    r2 = auth.iniciar_sesion("Admin 2", "1234", controller=ctrl)
    assert r2["ok"] is True
    assert r2["username"] == "Admin 2"

    r_fail = auth.iniciar_sesion("Admin 1", "9999", controller=ctrl)
    assert r_fail["ok"] is False
    assert "ACCESO RECHAZADO" in r_fail["msg"]

    # Se simula que otro ordenador ya esta conectado como Admin 1 en el servidor TCP
    ctrl.actualizar_estado_red({
        "tipo": "estado",
        "jugadores": [{"id": 1, "nombre": "Admin 1", "x": 100, "y": 100, "puntaje": 0}],
        "activa": False,
        "ganador": None,
    })
    r_ocupado = auth.iniciar_sesion("Admin 1", "1234", controller=ctrl)
    assert r_ocupado["ok"] is False
    assert "ya se encuentra conectado en otro ordenador" in r_ocupado["msg"]
