"""El avatar debe moverse a la misma velocidad en una laptop lenta y en una rapida."""
import pytest

from Cliente.Interfaz.pasos import pasos_de_movimiento


def simular(fps, segundos=2.0):
    """Pasos totales dados en `segundos` si cada cuadro dura 1/fps."""
    total, resto = 0, 0.0
    for _ in range(int(fps * segundos)):
        n, resto = pasos_de_movimiento(1.0 / fps, resto)
        total += n
    return total


def test_a_60_fps_es_un_paso_por_cuadro():
    assert simular(60) == 120


@pytest.mark.parametrize("fps", [20, 25, 30, 40, 45, 50])
def test_laptop_lenta_recorre_lo_mismo_que_una_rapida(fps):
    esperado = 120  # 60 pasos/s durante 2 s
    assert abs(simular(fps) - esperado) <= 2


def test_el_jitter_normal_de_clock_tick_no_hace_temblar_el_movimiento():
    # tick(60) devuelve 16 o 17 ms: siempre debe dar exactamente 1 paso
    for ms in (15, 16, 17, 18):
        assert pasos_de_movimiento(ms / 1000.0)[0] == 1


def test_parada_larga_no_da_un_salto_enorme():
    n, resto = pasos_de_movimiento(2.0)  # la ventana se congelo 2 segundos
    assert n == 4 and resto == 0.0


def test_dt_cero_o_negativo_no_mueve():
    assert pasos_de_movimiento(0.0)[0] == 0
    assert pasos_de_movimiento(-1.0)[0] == 0


@pytest.mark.parametrize("fps_ref,maximo", [(0, 4), (-60, 4), (60, 0)])
def test_parametros_invalidos(fps_ref, maximo):
    with pytest.raises(ValueError):
        pasos_de_movimiento(0.016, 0.0, maximo, fps_ref)
