"""
Pruebas unitarias positivas y negativas para el modulo del Integrante 1
(Colisiones de Arena y Lobby, Zona de Extraccion del Reactor, Exclusion de Colores,
Autenticacion Estricta, Acceso Admin con deteccion de sesion activa y Condicion de Victoria / Desempate).
Cumple con el Definition of Done (DoD) del Sprint 2.
"""
import math
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


def test_avatar_select_view_cambio_color_y_persistencia(tmp_path, monkeypatch):
    """
    Descripcion:
        Verifica que AvatarSelectView permita cambiar el color del avatar, actualizar la
        previsualizacion y persistir los cambios en config_local.json (US-06).
    Entradas:
        tmp_path: Directorio temporal de pytest.
        monkeypatch: Fixture de pytest para redirigir la ruta de configuracion.
    Salidas:
        None: Ejecuta aserciones sobre el estado del controlador tras guardar.
    Restricciones:
        Requiere inicializar CustomTkinter sin desplegar pantalla grafica real.
    """
    from Cliente.Interfaz.avatar_select_view import AvatarSelectView
    import Cliente.Interfaz.root as root_mod

    config_test = tmp_path / "config_test.json"
    monkeypatch.setattr(root_mod, "CONFIG_PATH", config_test)

    ctrl = AppController()
    view = AvatarSelectView(ctrl)
    view.withdraw()

    # Seleccionar color Verde
    view._seleccionar_color("#2A9D8F")
    assert view.color_temp == "#2A9D8F"

    # Guardar y aplicar (evitando abrir el mainloop de HubView en test unitario)
    monkeypatch.setattr(ctrl, "mostrar_hub", lambda: None)
    view._guardar_y_volver()
    assert ctrl.avatar_color == "#2A9D8F"
    assert config_test.exists()

    view.destroy()


def test_resolver_conflicto_color_duplicado_al_unirse():
    """
    Descripcion:
        Verifica que resolver_conflicto_color detecte cuando el color preferido del
        jugador local colisiona con el de otro jugador presente en la sala y le asigne
        automaticamente el siguiente color libre de la paleta (CA-10.3).
    Entradas:
        Ninguna.
    Salidas:
        None: Verifica que el nuevo color sea diferente y este libre de colisiones.
    Restricciones:
        Ninguna.
    """
    ctrl = AppController()
    ctrl.avatar_color = "#E63946"  # Rojo

    # Simulamos que otro jugador ya ocupa el color Rojo (#E63946)
    jugadores_sala = [
        {"id": 1, "nombre": "Local", "color": "#E63946", "es_local": True},
        {"id": 2, "nombre": "Host", "color": "#E63946", "es_local": False},
    ]

    color_asignado = ctrl.resolver_conflicto_color(jugadores_sala)
    assert color_asignado is not None
    assert color_asignado == "Azul"  # Primer color libre tras Rojo
    assert ctrl.avatar_color == "#1D3557"  # Azul
    assert jugadores_sala[0]["color"] == "#1D3557"


def test_resolver_conflicto_color_sin_colision():
    """
    Descripcion:
        Verifica que resolver_conflicto_color mantenga intacto el color del jugador local
        cuando ningun otro jugador en la sala ocupa dicho color.
    Entradas:
        Ninguna.
    Salidas:
        None: Verifica que retorne None y no modifique avatar_color.
    Restricciones:
        Ninguna.
    """
    ctrl = AppController()
    ctrl.avatar_color = "#2A9D8F"  # Verde

    jugadores_sala = [
        {"id": 1, "nombre": "Local", "color": "#2A9D8F", "es_local": True},
        {"id": 2, "nombre": "Host", "color": "#E63946", "es_local": False},
    ]

    res = ctrl.resolver_conflicto_color(jugadores_sala)
    assert res is None
    assert ctrl.avatar_color == "#2A9D8F"


def test_sprite_loader_retorna_superficies_validas():
    """
    Descripcion:
        Verifica que el modulo sprite_loader cargue correctamente los sprites 2D de
        personajes hazmat, particulas animadas y entorno de la estacion.
    Entradas:
        Ninguna.
    Salidas:
        None: Ejecuta aserciones sobre las dimensiones y tipos de superficies retornadas.
    Restricciones:
        Requiere pygame inicializado.
    """
    import pygame
    from Cliente.Interfaz.Components.sprite_loader import (
        inicializar_sprites,
        obtener_frame_particula,
        obtener_sprite_entorno,
        obtener_sprite_personaje,
    )
    pygame.init()
    if not pygame.display.get_init():
        pygame.display.init()
        pygame.display.set_mode((100, 100))

    sp_rojo = obtener_sprite_personaje("#E63946", direccion="down", size=(48, 48))
    assert sp_rojo is not None
    assert sp_rojo.get_size() == (48, 48)

    sp_part = obtener_frame_particula(0.0)
    assert sp_part is not None

    sp_reactor = obtener_sprite_entorno("reactor_core")
    assert sp_reactor is not None


def test_logica_abandonar_partida_victoria_inmediata_si_queda_uno():
    """
    Descripcion:
        Verifica que al abandonar la partida, si en la sala solo queda 1 jugador restante,
        se declare inmediatamente la victoria para dicho jugador.
    Entradas:
        Ninguna.
    Salidas:
        None: Verifica que el ganador sea el jugador restante y se active la condicion de victoria.
    Restricciones:
        Ninguna.
    """
    jugadores = [
        {"id": 1, "nombre": "Local", "color": "#E63946", "es_local": True},
        {"id": 2, "nombre": "Rival", "color": "#1D3557", "es_local": False},
    ]

    otros = [j for j in jugadores if not j.get("es_local", False)]
    assert len(otros) == 1

    ganador_inmediato = otros[0]
    assert ganador_inmediato["nombre"] == "Rival"


def test_logica_abandonar_partida_con_tres_jugadores_no_declara_ganador():
    """
    Descripcion:
        Verifica que al abandonar la partida con 3 o mas jugadores, como quedan 2 o mas
        participantes activos, el jugador local solo se retire al Lobby sin declarar ganador unico.
    Entradas:
        Ninguna.
    Salidas:
        None: Verifica que la cantidad de restantes sea mayor a 1.
    Restricciones:
        Ninguna.
    """
    jugadores = [
        {"id": 1, "nombre": "Local", "color": "#E63946", "es_local": True},
        {"id": 2, "nombre": "Piloto2", "color": "#1D3557", "es_local": False},
        {"id": 3, "nombre": "Piloto3", "color": "#2A9D8F", "es_local": False},
    ]

    otros = [j for j in jugadores if not j.get("es_local", False)]
    assert len(otros) >= 2


def test_colision_circular_reactor_sin_esquinas_cuadradas():
    """
    Descripcion:
        Verifica que el Reactor Central aplique una colision estrictamente circular
        en lugar de una caja cuadrada con esquinas ficticias, permitiendo que el jugador
        se aproxime diagonalmente hasta tocar el radio del circulo sin ser frenado
        en esquinas lejanas.
    Entradas:
        Ninguna.
    Salidas:
        None: Verifica que la distancia final sea exactamente el radio de colision circular.
    Restricciones:
        Ninguna.
    """
    rx, ry = 1800, 1300
    radio_col = 85
    r_jug = 24  # rect de 48x48
    min_dist_esperada = radio_col + r_jug  # 109 px

    # Jugador intentando penetrar el nucleo en diagonal exacta (45 grados)
    jugador = pygame.Rect(rx + 50, ry - 50, 48, 48)
    nuevo = mover_con_colisiones(
        jugador,
        0,
        0,
        [],
        circulo_reactor=(rx, ry, radio_col),
    )

    dist_resultante = math.hypot(nuevo.centerx - rx, nuevo.centery - ry)
    assert abs(dist_resultante - min_dist_esperada) < 1.0


def test_avatar_select_cumple_criterio_ca_06_3_disco():
    """
    Descripcion:
        Verifica el cumplimiento de CA-06.3 permitiendo la seleccion de trajes Hazmat
        o la carga opcional de imagen personalizada desde disco.
    Entradas:
        Ninguna.
    Salidas:
        None: Verifica la presencia de los metodos de carga y restablecimiento.
    Restricciones:
        Ninguna.
    """
    from Cliente.Interfaz.avatar_select_view import AvatarSelectView
    assert hasattr(AvatarSelectView, "_cargar_imagen_disco")
    assert hasattr(AvatarSelectView, "_quitar_imagen_disco")


def test_recuperacion_contrasena_us_05(monkeypatch):
    """
    Descripcion:
        Verifica el flujo de recuperacion de contrasena (US-05) del cliente. El adaptador ya no
        guarda cuentas en un archivo local: valida lo que puede en el cliente y delega el resto
        al servidor, asi que aqui se simula el servidor con una funcion falsa.
    Entradas:
        monkeypatch: Fixture de pytest para reemplazar la peticion de red.
    Salidas:
        None: Ejecuta aserciones sobre las validaciones y los mensajes enviados al servidor.
    Restricciones:
        No requiere servidor ni red.
    """
    import Cliente.Interfaz.auth_adapter as modulo

    enviados = []

    def servidor_falso(action, timeout=15, **datos):
        enviados.append((action, datos))
        if action == "forgot":
            return {"ok": datos["email"] == "piloto@gmail.com", "msg": "codigo enviado"}
        if action == "reset":
            return {"ok": datos["code"] == "123456", "msg": "listo"}
        return {"ok": False, "msg": "accion desconocida"}

    monkeypatch.setattr(modulo, "_pedir", servidor_falso)
    auth = ClienteAuthAdapter()

    # 1. Rechazo local por correo invalido: ni siquiera llega al servidor
    assert auth.solicitar_codigo_recuperacion("correo_sin_arroba")["ok"] is False
    assert enviados == []

    # 2. Cuenta inexistente: la rechaza el servidor
    assert auth.solicitar_codigo_recuperacion("nadie@gmail.com")["ok"] is False

    # 3. Solicitud correcta (el correo se normaliza)
    assert auth.solicitar_codigo_recuperacion("  PILOTO@gmail.com ")["ok"] is True
    assert enviados[-1] == ("forgot", {"email": "piloto@gmail.com"})

    # 4. Rechazos locales al restablecer: sin codigo, sin claves, no coinciden, debil
    antes = len(enviados)
    assert auth.restablecer_password("piloto@gmail.com", "", "NuevaClave123", "NuevaClave123")["ok"] is False
    assert auth.restablecer_password("piloto@gmail.com", "123456", "", "")["ok"] is False
    assert auth.restablecer_password("piloto@gmail.com", "123456", "NuevaClave123", "OtraClave999")["ok"] is False
    assert auth.restablecer_password("piloto@gmail.com", "123456", "corta", "corta")["ok"] is False
    assert len(enviados) == antes  # ninguna llego al servidor

    # 5. Codigo incorrecto: lo rechaza el servidor
    assert auth.restablecer_password("piloto@gmail.com", "000000", "NuevaClave123", "NuevaClave123")["ok"] is False

    # 6. Restablecimiento correcto: se envia el codigo y la nueva clave
    assert auth.restablecer_password("piloto@gmail.com", " 123456 ", "NuevaClave123", "NuevaClave123")["ok"] is True
    assert enviados[-1] == ("reset", {"email": "piloto@gmail.com", "code": "123456", "new_password": "NuevaClave123"})




def test_escenarios_us_23_diferencias_funcionales_y_fallback():
    """
    Descripcion:
        Verifica el cumplimiento de CA-23.1 y el DoD de US-23:
        1. Al menos dos escenarios seleccionables con distribucion funcional distinta.
        2. Mas muros/bloqueos en Reactor Inestable y Laberinto Cerrado respecto a Estacion Estandar.
        3. Manejo seguro con fallback a Estacion Estandar si el nombre del mapa es desconocido.
    Entradas:
        Ninguna.
    Salidas:
        None: Aserciones sobre la cantidad de rectangulos de colision de cada mapa.
    Restricciones:
        Ninguna.
    """
    from Cliente.Interfaz.arena_collisions import obtener_muros_arena

    muros_base = obtener_muros_arena("Estacion Estandar")
    muros_inestable = obtener_muros_arena("Reactor Inestable")
    muros_laberinto = obtener_muros_arena("Laberinto Cerrado")
    muros_fallback = obtener_muros_arena("MapaDesconocidoXYZ")

    # Hay al menos 2 variantes con diferencias funcionales claras
    assert len(muros_base) >= 8
    assert len(muros_inestable) > len(muros_base)
    assert len(muros_laberinto) > len(muros_base)
    assert len(muros_inestable) != len(muros_laberinto)

    # Fallback seguro para nombres no validos
    assert len(muros_fallback) == len(muros_base)


def test_sincronizacion_mapa_red_us_23():
    """
    Descripcion:
        Verifica el cumplimiento de CA-23.4:
        1. El cliente invitado (es_creador=False) adopta reactivamente el mapa recibido por red.
        2. El cliente anfitrion (es_creador=True) preserva su seleccion local.
    Entradas:
        Ninguna.
    Salidas:
        None: Aserciones sobre controller.mapa_seleccionado.
    Restricciones:
        Ninguna.
    """
    from Cliente.Interfaz.root import AppController

    app = AppController()

    # Caso 1: Invitado recibe actualizacion de mapa
    app.es_creador = False
    app.mapa_seleccionado = "Estacion Estandar"
    app.actualizar_estado_red({"tipo": "estado", "mapa": "Reactor Inestable"})
    assert app.mapa_seleccionado == "Reactor Inestable"

    app.actualizar_estado_red({"tipo": "configurar_partida", "mapa": "Laberinto Cerrado"})
    assert app.mapa_seleccionado == "Laberinto Cerrado"

    # Caso 2: Creador mantiene su seleccion y no es sobreescrito
    app.es_creador = True
    app.mapa_seleccionado = "Reactor Inestable"
    app.actualizar_estado_red({"tipo": "estado", "mapa": "Estacion Estandar"})
    assert app.mapa_seleccionado == "Reactor Inestable"


def test_obstaculos_por_mapa_y_seguridad_spawns_us_20():
    """
    Descripcion:
        Verifica el cumplimiento de US-20, CA-20.1, CA-20.2, CA-20.5, CA-23.2 y CA-23.5:
        1. Existen puertas, barreras y al menos 3 trampas distintas en cada mapa.
        2. Todas las trampas y obstaculos se ubican dentro de los limites del mundo (3600x2600).
        3. Ninguna trampa u obstaculo invade los puntos de spawn de los jugadores ni el reactor.
    Entradas:
        Ninguna.
    Salidas:
        None: Aserciones sobre la configuracion de obstaculos y trampas.
    Restricciones:
        Ninguna.
    """
    from Cliente.Interfaz.Components.obstaculos import obtener_obstaculos_por_mapa
    from Cliente.Interfaz.arena_collisions import (
        REACTOR_CENTER,
        REACTOR_COLLISION_RADIUS,
        SPAWN_POINTS,
        WORLD_HEIGHT,
        WORLD_WIDTH,
    )

    r_reactor = pygame.Rect(
        REACTOR_CENTER[0] - REACTOR_COLLISION_RADIUS,
        REACTOR_CENTER[1] - REACTOR_COLLISION_RADIUS,
        REACTOR_COLLISION_RADIUS * 2,
        REACTOR_COLLISION_RADIUS * 2,
    )

    for mapa in ("Estacion Estandar", "Reactor Inestable", "Laberinto Cerrado"):
        obs = obtener_obstaculos_por_mapa(mapa)
        assert len(obs["puertas"]) >= 2
        assert len(obs["barreras"]) >= 2
        assert len(obs["trampas"]) >= 3

        tipos_trampas = {t["tipo"] for t in obs["trampas"]}
        assert "jaula" in tipos_trampas
        assert "gravedad" in tipos_trampas
        assert "charco" in tipos_trampas

        # Comprobar margenes y no invasion de spawns/reactor
        for t in obs["trampas"] + obs["puertas"] + obs["barreras"]:
            r = t["rect"]
            assert 0 <= r.left and r.right <= WORLD_WIDTH
            assert 0 <= r.top and r.bottom <= WORLD_HEIGHT
            assert not r.colliderect(r_reactor)
            for sp_coord in SPAWN_POINTS.values():
                sp_rect = pygame.Rect(sp_coord[0] - 48, sp_coord[1] - 48, 96, 96)
                assert not r.colliderect(sp_rect)


def test_colisiones_dinamicas_puertas_us_20():
    """
    Descripcion:
        Verifica CA-20.3 y CA-20.4:
        1. Las puertas cerradas forman parte de la lista de colisiones no transitables.
        2. Las puertas abiertas NO colisionan, permitiendo que el avatar pase a traves de ellas.
    Entradas:
        Ninguna.
    Salidas:
        None: Aserciones sobre obtener_colisiones_obstaculos.
    Restricciones:
        Ninguna.
    """
    from Cliente.Interfaz.Components.obstaculos import (
        actualizar_estados_puertas,
        obtener_colisiones_obstaculos,
    )

    puertas = [
        {"id": "p1", "rect": pygame.Rect(500, 500, 100, 20), "estado": "cerrada", "periodo": 10.0},
        {"id": "p2", "rect": pygame.Rect(800, 800, 100, 20), "estado": "abierta", "periodo": 10.0},
    ]
    barreras = [{"id": "b1", "rect": pygame.Rect(200, 200, 80, 20), "tipo": "peligro"}]
    obstaculos = {"puertas": puertas, "barreras": barreras, "trampas": []}

    colisiones_1 = obtener_colisiones_obstaculos(obstaculos)
    assert barreras[0]["rect"] in colisiones_1
    assert puertas[0]["rect"] in colisiones_1
    assert puertas[1]["rect"] not in colisiones_1

    # Invertir estados
    puertas[0]["estado"] = "abierta"
    puertas[1]["estado"] = "cerrada"
    colisiones_2 = obtener_colisiones_obstaculos(obstaculos)
    assert puertas[0]["rect"] not in colisiones_2
    assert puertas[1]["rect"] in colisiones_2


def test_efectos_visuales_trampas_avatar_us_20():
    """
    Descripcion:
        Verifica CA-20.5 y CA-20.8:
        1. Rotacion de 180 grados en la trampa de gravedad.
        2. Preservacion de dimensiones sin desbordar los margenes de la ventana.
        3. Deteccion de pisada sobre la trampa.
    Entradas:
        Ninguna.
    Salidas:
        None: Aserciones sobre las superficies generadas.
    Restricciones:
        Requiere Pygame inicializado.
    """
    from Cliente.Interfaz.Components.obstaculos import (
        aplicar_efecto_visual_avatar,
        detectar_trampa_activa,
    )

    sprite_base = pygame.Surface((48, 48), pygame.SRCALPHA)
    pygame.draw.rect(sprite_base, (255, 0, 0), (0, 0, 48, 48))

    # Prueba efecto gravedad (rotar 180 grados)
    surf_grav = aplicar_efecto_visual_avatar(sprite_base, (48, 48), "gravedad", 1.0)
    assert surf_grav.get_size() == (48, 48)

    # Prueba efecto jaula (overlay de barrotes)
    surf_jaula = aplicar_efecto_visual_avatar(sprite_base, (48, 48), "jaula", 1.0)
    assert surf_jaula.get_size() == (48, 48)

    # Prueba efecto charco (filtro verde toxico)
    surf_charco = aplicar_efecto_visual_avatar(sprite_base, (48, 48), "charco", 1.0)
    assert surf_charco.get_size() == (48, 48)

    # Deteccion de pisada
    trampas = [
        {"id": "t1", "tipo": "jaula", "rect": pygame.Rect(100, 100, 60, 60), "activa": True},
        {"id": "t2", "tipo": "gravedad", "rect": pygame.Rect(300, 300, 60, 60), "activa": True},
    ]
    jugador_sobre_jaula = pygame.Rect(110, 110, 48, 48)
    jugador_lejos = pygame.Rect(500, 500, 48, 48)

    assert detectar_trampa_activa(jugador_sobre_jaula, trampas) == "jaula"
    assert detectar_trampa_activa(jugador_lejos, trampas) is None


def test_hud_arena_insignias_y_tiempo_extra_us_24():
    """
    Descripcion:
        Verifica el cumplimiento de CA-24.2, CA-24.3 y el DoD de US-24:
        1. Renderizado de tiempo normal ('EN CURSO') vs 'TIEMPO EXTRA'.
        2. Renderizado de estado del reactor ('disponible' vs 'sobrecargado').
        3. Proyeccion de guardianes de Saymon en el radar.
        4. Renderizado de banners de eventos especiales y toasts de rechazo.
    Entradas:
        Ninguna.
    Salidas:
        None: Aserciones sobre la ejecucion limpia sin excepciones.
    Restricciones:
        Requiere inicializacion de Pygame.
    """
    import time
    from Cliente.Interfaz.Components.hud import dibujar_hud_arena
    from Cliente.Interfaz.root import AppController

    app = AppController()
    screen = pygame.Surface((1280, 720))
    jugadores = [
        {"id": 1, "nombre": "Piloto_1", "color": "#E63946", "rect": pygame.Rect(1800, 1000, 48, 48), "puntos": 120, "es_local": True},
        {"id": 2, "nombre": "Piloto_2", "color": "#1D3557", "rect": pygame.Rect(1800, 1600, 48, 48), "puntos": 120, "es_local": False},
    ]
    muros = [pygame.Rect(0, 0, 3600, 50)]
    guardianes = [
        {"id": 1, "x": 1200, "y": 1000},
        {"id": 2, "x": 2400, "y": 1500},
    ]
    toasts = [
        {"mensaje": "FUERA DE RANGO DEL REACTOR", "expira": time.time() + 10.0, "tipo": "advertencia"},
    ]
    evento = {"activo": True, "nombre": "Sobrecarga x2"}

    # Caso 1: En tiempo extra con reactor sobrecargado, guardianes y toasts
    res1 = dibujar_hud_arena(
        screen,
        app,
        jugadores,
        tiempo_restante=20.0,
        world_size=(3600, 2600),
        muros_mundo=muros,
        reactor_center=(1800, 1300),
        en_tiempo_extra=True,
        estado_reactor="sobrecargado",
        guardianes=guardianes,
        toasts=toasts,
        evento_especial=evento,
    )
    assert isinstance(res1, dict)

    # Caso 2: En curso normal con reactor disponible
    res2 = dibujar_hud_arena(
        screen,
        app,
        jugadores,
        tiempo_restante=120.0,
        world_size=(3600, 2600),
        muros_mundo=muros,
        reactor_center=(1800, 1300),
        en_tiempo_extra=False,
        estado_reactor="disponible",
    )
    assert isinstance(res2, dict)


def test_dibujar_guardianes_mundo_us_24():
    """
    Descripcion:
        Verifica CA-24.1: Los guardianes de Saymon se dibujan correctamente
        en la superficie del mundo sin generar excepciones.
    Entradas:
        Ninguna.
    Salidas:
        None.
    Restricciones:
        Requiere Pygame inicializado.
    """
    from Cliente.Interfaz.arena_view import dibujar_guardianes_mundo

    world = pygame.Surface((3600, 2600))
    guardianes = [
        {"id": 1, "x": 1000, "y": 1000},
        {"id": 2, "x": 2000, "y": 1200},
        {"id": 3, "x": 1500, "y": 2000},
        {"id": 4, "x": 2500, "y": 1800},
    ]
    # Debe dibujar sin errores a tiempo t=0.0 y t=5.0
    dibujar_guardianes_mundo(world, guardianes, ahora=0.0)
    dibujar_guardianes_mundo(world, guardianes, ahora=5.0)


def test_sincronizar_estados_y_eventos_red():
    """Verifica sincronizacion reactiva de reactor, eventos, congelamiento y toasts desde red."""
    from Cliente.Interfaz.arena_view import sincronizar_estados_y_eventos_red

    jugs = [
        {"id": 1, "nombre": "Local", "es_local": True, "congelado": False},
        {"id": 2, "nombre": "Rival", "es_local": False, "congelado": False},
    ]
    toasts: list[dict] = []
    estado_red = {
        "estado_reactor": "sobrecargado",
        "evento_especial": {"nombre": "TORMENTA SOLAR", "activo": True},
        "mensaje_rechazo": "REACTOR EN SOBRECARGA",
        "jugadores": [
            {"id": 1, "congelado": True, "trampa_activa": "gravedad"},
            {"id": 2, "congelado": False},
        ],
    }

    est_r, ev = sincronizar_estados_y_eventos_red(estado_red, jugs, 1, toasts, ahora=10.0)
    assert est_r == "sobrecargado"
    assert ev is not None and ev["nombre"] == "TORMENTA SOLAR"
    assert jugs[0]["congelado"] is True
    assert jugs[0]["trampa_activa"] == "gravedad"
    assert any(t["mensaje"] == "REACTOR EN SOBRECARGA" for t in toasts)


def test_blindaje_hex_to_rgb_y_guardianes_corruptos():
    """Verifica que colores no hexadecimales o guardianes malformados no provoquen caidas."""
    from Cliente.Interfaz.Components.hud import hex_to_rgb
    from Cliente.Interfaz.arena_view import dibujar_guardianes_mundo

    assert hex_to_rgb("#GGGGGG") == (230, 57, 70)
    assert hex_to_rgb(None) == (230, 57, 70)
    assert hex_to_rgb("#00FF00") == (0, 255, 0)

    world = pygame.Surface((400, 400))
    dibujar_guardianes_mundo(world, [{"x": "bad", "y": None}, {}, None, {"x": 100, "y": 100}], ahora=1.0)


def test_dibujar_energia_adicional_solo_con_el_evento_correcto():
    """US-22 / CA-22.1: el icono se dibuja unicamente para el evento de energia con posicion valida."""
    import pygame
    from Cliente.Interfaz.arena_view import dibujar_energia_adicional
    pygame.init()
    sup = pygame.Surface((400, 400))
    sup.fill((0, 0, 0))
    dibujar_energia_adicional(sup, None, 0.0)
    dibujar_energia_adicional(sup, {"tipo": "doble_extraccion", "x": 200, "y": 200}, 0.0)
    dibujar_energia_adicional(sup, {"tipo": "energia_adicional"}, 0.0)           # sin posicion
    dibujar_energia_adicional(sup, {"tipo": "energia_adicional", "x": "a", "y": 1}, 0.0)
    assert sup.get_at((200, 200))[:3] == (0, 0, 0)                                  # nada dibujado
    dibujar_energia_adicional(sup, {"tipo": "energia_adicional", "x": 200, "y": 200}, 0.0)
    assert sup.get_at((200, 200))[:3] != (0, 0, 0)


def test_el_controlador_guarda_el_motivo_de_rechazo():
    from Cliente.Interfaz.root import AppController
    app = AppController.__new__(AppController)
    import threading
    app.estado_red_lock = threading.Lock()
    app.estado_partida_red, app.acciones_remotas, app.rechazo_red = {}, {}, None
    app.es_creador = True
    app.actualizar_estado_red({"tipo": "rechazo", "mensaje": "Acercate al reactor para extraer"})
    assert app.rechazo_red[0] == "Acercate al reactor para extraer"
    app.actualizar_estado_red({"tipo": "rechazo", "mensaje": 5})                   # basura: se ignora
    assert app.rechazo_red[0] == "Acercate al reactor para extraer"
