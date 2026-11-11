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


# ---------- suavizado y orientacion del rival ----------
from Cliente.Interfaz.red_sync import direccion_de, otros_jugadores, suavizar_remotos


def rival(x=0, y=0):
    return {"es_local": False, "rect": rect(x, y), "nombre": "R", "puntos": 0, "color": "#1D3557"}


def test_primera_posicion_del_rival_se_aplica_de_inmediato():
    js = [casillas()[0], rival()]
    aplicar_estado_remoto(js, [ANA, BETO], 1, {}, 0)
    assert js[1]["rect"].topleft == (1500, 900)


def test_el_rival_se_desliza_hacia_la_nueva_posicion_sin_saltar():
    js = [casillas()[0], rival()]
    aplicar_estado_remoto(js, [ANA, BETO], 1, {}, 0)
    aplicar_estado_remoto(js, [ANA, {**BETO, "x": 1600}], 1, {}, 0)
    suavizar_remotos(js, 1 / 60)
    x = js[1]["rect"].topleft[0]
    assert 1500 < x < 1600  # avanzo, pero no llego de golpe


def test_el_rival_termina_exactamente_en_la_posicion_recibida():
    js = [casillas()[0], rival()]
    aplicar_estado_remoto(js, [ANA, BETO], 1, {}, 0)
    aplicar_estado_remoto(js, [ANA, {**BETO, "x": 1600, "y": 950}], 1, {}, 0)
    for _ in range(120):
        suavizar_remotos(js, 1 / 60)
    assert js[1]["rect"].topleft == (1600, 950)


def test_salto_muy_grande_se_aplica_de_golpe():
    js = [casillas()[0], rival()]
    aplicar_estado_remoto(js, [ANA, BETO], 1, {}, 0)
    aplicar_estado_remoto(js, [ANA, {**BETO, "x": 100, "y": 100}], 1, {}, 0)
    suavizar_remotos(js, 1 / 60)
    assert js[1]["rect"].topleft == (100, 100)


def test_el_rival_mira_hacia_donde_se_mueve():
    js = [casillas()[0], rival()]
    aplicar_estado_remoto(js, [ANA, BETO], 1, {}, 0)
    aplicar_estado_remoto(js, [ANA, {**BETO, "x": 1400}], 1, {}, 0)
    suavizar_remotos(js, 1 / 60)
    assert js[1]["direccion"] == "left"


@pytest.mark.parametrize("dx,dy,esperado", [(5, 0, "right"), (-5, 0, "left"), (0, 5, "down"), (0, -5, "up"), (3, -9, "up")])
def test_direccion_de(dx, dy, esperado):
    assert direccion_de(dx, dy) == esperado


def test_sin_movimiento_conserva_la_orientacion():
    assert direccion_de(0, 0, "left") == "left"


def test_suavizar_no_toca_al_jugador_local_ni_con_dt_invalido():
    js = casillas()
    antes = js[0]["rect"].topleft
    suavizar_remotos(js, 1 / 60)
    suavizar_remotos(js, 0)
    suavizar_remotos(js, -1)
    assert js[0]["rect"].topleft == antes


def test_rival_sin_posicion_conocida_no_se_mueve():
    js = [casillas()[0], rival(99, 99)]
    suavizar_remotos(js, 1 / 60)
    assert js[1]["rect"].topleft == (99, 99)


# ---------- lobby: quienes son los demas ----------
def test_otros_jugadores_excluye_al_propio_por_id():
    assert [d["id"] for d in otros_jugadores([ANA, BETO], 2)] == [1]
    assert [d["id"] for d in otros_jugadores([BETO, ANA], 1)] == [2]


def test_otros_jugadores_sin_identificar_asume_que_soy_el_primero():
    assert [d["id"] for d in otros_jugadores([ANA, BETO], None)] == [2]
    assert [d["id"] for d in otros_jugadores([ANA, BETO], 99)] == [2]


def test_otros_jugadores_lista_vacia_o_basura():
    assert otros_jugadores([], 1) == []
    assert otros_jugadores(["x", None], 1) == []
