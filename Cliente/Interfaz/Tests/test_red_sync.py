"""Sincronizacion de jugadores remotos: se identifica por id, nunca por posicion en la lista."""
from types import SimpleNamespace

import pytest

from Cliente.Interfaz.red_sync import aplicar_estado_remoto, asignar_spawns


def rect(x=0, y=0):
    return SimpleNamespace(topleft=(x, y))


def casillas():
    """Lista local de la arena: [yo, rival]."""
    return [
        {"nombre": "Yo", "es_local": True, "rect": rect(10, 10), "puntos": 0, "color": "#E63946", "color_nombre": "Rojo"},
        {"nombre": "Piloto_2", "es_local": False, "rect": rect(99, 99), "puntos": 0, "color": "#1D3557", "color_nombre": "Azul"},
    ]


ANA = {"id": 1, "nombre": "Ana", "x": 500, "y": 200, "puntaje": 70}
BETO = {"id": 2, "nombre": "Beto", "x": 1500, "y": 900, "puntaje": 30}


# ---------- el error original: el jugador 2 no veia al jugador 1 ----------
def test_jugador_1_ve_al_jugador_2():
    js = casillas()
    aplicar_estado_remoto(js, [ANA, BETO], mi_id=1, acciones_remotas={}, ahora=0)
    assert (js[1]["nombre"], js[1]["rect"].topleft, js[1]["puntos"]) == ("Beto", (1500, 900), 30)


def test_jugador_2_ve_al_jugador_1_y_no_a_si_mismo():
    js = casillas()
    aplicar_estado_remoto(js, [ANA, BETO], mi_id=2, acciones_remotas={}, ahora=0)
    assert (js[1]["nombre"], js[1]["rect"].topleft, js[1]["puntos"]) == ("Ana", (500, 200), 70)


def test_el_jugador_local_nunca_se_modifica():
    js = casillas()
    aplicar_estado_remoto(js, [ANA, BETO], mi_id=2, acciones_remotas={}, ahora=0)
    assert (js[0]["nombre"], js[0]["rect"].topleft, js[0]["puntos"]) == ("Yo", (10, 10), 0)


def test_el_orden_de_la_lista_del_servidor_no_importa():
    js = casillas()
    aplicar_estado_remoto(js, [BETO, ANA], mi_id=2, acciones_remotas={}, ahora=0)
    assert js[1]["nombre"] == "Ana"


# ---------- casos limite / negativos ----------
def test_sin_id_propio_no_toca_nada():
    js = casillas()
    assert aplicar_estado_remoto(js, [ANA, BETO], mi_id=None, acciones_remotas={}, ahora=0) == 0
    assert js[1]["nombre"] == "Piloto_2"


def test_si_estoy_solo_no_hay_rival_que_actualizar():
    js = casillas()
    assert aplicar_estado_remoto(js, [ANA], mi_id=1, acciones_remotas={}, ahora=0) == 0
    assert js[1]["nombre"] == "Piloto_2"


def test_rival_que_no_se_ha_movido_conserva_su_punto_de_salida():
    js = casillas()
    aplicar_estado_remoto(js, [ANA, {"id": 2, "nombre": "Beto", "x": 0, "y": 0, "puntaje": 0}], 1, {}, 0)
    assert js[1]["rect"].topleft == (99, 99)


@pytest.mark.parametrize("basura", [
    {"id": 2, "x": "abc", "y": None, "puntaje": "mucho"},
    {"id": 2, "x": True, "y": False, "puntaje": -5},
    {"id": 2},
])
def test_datos_invalidos_del_servidor_no_rompen(basura):
    js = casillas()
    aplicar_estado_remoto(js, [ANA, basura], 1, {}, 0)
    assert js[1]["rect"].topleft == (99, 99) and js[1]["puntos"] == 0


def test_entradas_que_no_son_jugadores_se_ignoran():
    js = casillas()
    aplicar_estado_remoto(js, ["x", None, 5, ANA, BETO], 1, {}, 0)
    assert js[1]["nombre"] == "Beto"


def test_accion_remota_vigente_y_vencida():
    js = casillas()
    aplicar_estado_remoto(js, [ANA, BETO], 1, {2: 105.0}, ahora=100.0)
    assert js[1]["extrayendo"] is True
    aplicar_estado_remoto(js, [ANA, BETO], 1, {2: 105.0}, ahora=110.0)
    assert js[1]["extrayendo"] is False


# ---------- color del rival ----------
def test_color_del_rival_se_aplica_con_su_nombre():
    js = casillas()
    aplicar_estado_remoto(js, [ANA, {**BETO, "color": "#2A9D8F"}], 1, {}, 0, nombre_color=lambda c: "Verde")
    assert (js[1]["color"], js[1]["color_nombre"]) == ("#2A9D8F", "Verde")


def test_color_igual_al_mio_se_ignora_para_no_repetir():
    js = casillas()
    aplicar_estado_remoto(js, [ANA, {**BETO, "color": "#e63946"}], 1, {}, 0)
    assert js[1]["color"] == "#1D3557"


@pytest.mark.parametrize("color", ["rojo", "#12", "#GGGGGG", 123, None])
def test_color_invalido_se_ignora(color):
    js = casillas()
    aplicar_estado_remoto(js, [ANA, {**BETO, "color": color}], 1, {}, 0)
    assert js[1]["color"] == "#1D3557"


# ---------- puntos de salida ----------
def test_cada_cliente_coloca_a_cada_jugador_en_el_mismo_lugar():
    # Ana (id 1) -> salida 0; Beto (id 2) -> salida 1, vista desde cualquiera de los dos
    assert asignar_spawns([ANA, BETO], 1) == [0, 1]
    assert asignar_spawns([ANA, BETO], 2) == [1, 0]


def test_spawns_con_ids_no_consecutivos():
    assert asignar_spawns([{"id": 7}, {"id": 3}], 7) == [1, 0]


@pytest.mark.parametrize("estado,mi_id", [([], 1), ([ANA], None), ([ANA], 2), (["x"], 1)])
def test_spawns_sin_identificar_devuelve_none(estado, mi_id):
    assert asignar_spawns(estado, mi_id) is None
