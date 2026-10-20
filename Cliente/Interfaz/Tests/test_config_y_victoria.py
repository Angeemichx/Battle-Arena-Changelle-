"""Pruebas de US-08 (parametros en el lobby / modos de fin) y US-17 (pantalla de victoria). Sin ventana."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from Cliente.Interfaz.arena_view import evaluar_condicion_victoria
from Cliente.Interfaz.lobby_view import aplicar_opcion_configuracion
from Cliente.Interfaz.victoria_view import (
    calcular_ranking, mensaje_felicitacion, sintetizar_fanfarria,
)


class FakeController:
    """Solo los atributos que toca el lobby al configurar la partida."""
    def __init__(self, es_creador=True, en_curso=False, guarda=True):
        self.es_creador, self.partida_en_curso = es_creador, en_curso
        self.tiempo_partida_min, self.puntos_meta = 3, 500
        self.modo_fin, self.tiempo_congelado_seg = "tiempo", 5
        self.guardados, self._guarda = 0, guarda

    def configuracion_editable(self): return not self.partida_en_curso
    def guardar_configuracion_partida(self):
        self.guardados += 1
        return self._guarda


# ---------- US-08: parametros del lobby ----------
def test_cicla_duracion_y_guarda():
    c = FakeController()
    aplicar_opcion_configuracion(c, 3)
    assert c.tiempo_partida_min == 5 and c.guardados == 1


def test_cicla_meta_de_puntos():
    c = FakeController()
    aplicar_opcion_configuracion(c, 4)
    assert c.puntos_meta == 800


def test_alterna_modo_de_fin_y_vuelve():
    c = FakeController()
    aplicar_opcion_configuracion(c, 5)
    assert c.modo_fin == "puntos"
    aplicar_opcion_configuracion(c, 5)
    assert c.modo_fin == "tiempo"


def test_cicla_congelamiento():
    c = FakeController()
    aplicar_opcion_configuracion(c, 6)
    assert c.tiempo_congelado_seg == 10


def test_valor_cargado_fuera_de_las_opciones_no_revienta():
    c = FakeController()
    c.tiempo_partida_min = 17  # venia de un archivo guardado a mano
    aplicar_opcion_configuracion(c, 3)
    assert c.tiempo_partida_min == 1


@pytest.mark.parametrize("op", [3, 4, 5, 6])
def test_quien_no_es_creador_no_puede_cambiar(op):
    c = FakeController(es_creador=False)
    assert "BLOQUEADO" in aplicar_opcion_configuracion(c, op)
    assert (c.tiempo_partida_min, c.puntos_meta, c.modo_fin, c.tiempo_congelado_seg) == (3, 500, "tiempo", 5)
    assert c.guardados == 0


@pytest.mark.parametrize("op", [3, 4, 5, 6])
def test_con_partida_en_curso_no_se_puede_cambiar(op):
    c = FakeController(en_curso=True)
    assert "BLOQUEADO" in aplicar_opcion_configuracion(c, op)
    assert (c.tiempo_partida_min, c.puntos_meta, c.modo_fin, c.tiempo_congelado_seg) == (3, 500, "tiempo", 5)


def test_opcion_desconocida_no_hace_nada():
    c = FakeController()
    assert aplicar_opcion_configuracion(c, 99) == "" and c.guardados == 0


def test_avisa_si_no_se_pudo_guardar():
    assert "no se pudo guardar" in aplicar_opcion_configuracion(FakeController(guarda=False), 3)


# ---------- US-08: modos de fin en la arena ----------
J = lambda *pts: [{"nombre": f"P{i}", "puntos": p} for i, p in enumerate(pts)]


def test_modo_tiempo_ignora_la_meta_de_puntos():
    assert evaluar_condicion_victoria(J(900, 10), 30.0, 500, "tiempo")[0] is False


def test_modo_tiempo_termina_al_agotarse_el_reloj():
    terminada, ganador, _, _ = evaluar_condicion_victoria(J(900, 10), 0.0, 500, "tiempo")
    assert terminada and ganador["nombre"] == "P0"


def test_modo_puntos_ignora_el_reloj():
    assert evaluar_condicion_victoria(J(10, 20), 0.0, 500, "puntos")[0] is False


def test_modo_puntos_termina_al_llegar_a_la_meta():
    terminada, ganador, _, _ = evaluar_condicion_victoria(J(500, 20), 12.0, 500, "puntos")
    assert terminada and ganador["nombre"] == "P0"


def test_modo_puntos_empate_no_agrega_tiempo():
    terminada, _, desempate, t = evaluar_condicion_victoria(J(500, 500), 42.0, 500, "puntos")
    assert not terminada and desempate and t == 42.0


def test_modo_tiempo_empate_agrega_dos_minutos():
    _, _, desempate, t = evaluar_condicion_victoria(J(50, 50), 0.0, 500, "tiempo")
    assert desempate and t == 120.0


def test_sin_modo_se_comporta_como_antes():
    assert evaluar_condicion_victoria(J(500, 1), 99.0, 500)[0] is True
    assert evaluar_condicion_victoria(J(5, 1), 0.0, 500)[0] is True


# ---------- US-17: pantalla de victoria ----------
def test_ranking_ordena_de_mayor_a_menor():
    r = calcular_ranking(J(10, 90, 40))
    assert [j["nombre"] for j in r] == ["P1", "P2", "P0"]
    assert [j["puesto"] for j in r] == [1, 2, 3]


def test_ranking_empatados_comparten_puesto():
    assert [j["puesto"] for j in calcular_ranking(J(50, 50, 10))] == [1, 1, 3]


def test_ranking_no_modifica_la_entrada():
    original = J(1, 2)
    calcular_ranking(original)
    assert "puesto" not in original[0] and original[0]["nombre"] == "P0"


def test_ranking_lista_vacia():
    assert calcular_ranking([]) == []


def test_felicitacion_incluye_el_nombre():
    assert "ANA" in mensaje_felicitacion({"nombre": "Ana"})
    assert "PILOTO" in mensaje_felicitacion({})


def test_fanfarria_tiene_audio_valido():
    datos = sintetizar_fanfarria(22050, 2)
    assert len(datos) > 22050 * 2 * 2 and len(datos) % 4 == 0 and any(datos)


def test_fanfarria_mono_es_la_mitad():
    assert len(sintetizar_fanfarria(8000, 1)) * 2 == len(sintetizar_fanfarria(8000, 2))


@pytest.mark.parametrize("fs,ch", [(0, 2), (-1, 2), (44100, 3)])
def test_fanfarria_rechaza_formato_invalido(fs, ch):
    with pytest.raises(ValueError):
        sintetizar_fanfarria(fs, ch)
