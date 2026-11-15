"""
Movimiento independiente de los cuadros por segundo (FPS).

El avatar avanza un numero fijo de pixeles por "paso" y se espera 60 pasos por segundo. Si una laptop
va a 30 FPS debe dar 2 pasos por cuadro; si no, se movera la mitad de rapido que la otra laptop.
"""
from __future__ import annotations


def pasos_de_movimiento(
    dt: float, resto: float = 0.0, maximo: int = 4, fps_ref: float = 60.0
) -> tuple[int, float]:
    """
    Cuantos pasos de movimiento dar en este cuadro.

    dt: segundos del cuadro. resto: fraccion de paso acumulada del cuadro anterior.
    Devuelve (pasos, nuevo_resto). Un cuadro de duracion normal (a ~60 FPS, con la variacion de
    unos milisegundos que tiene clock.tick; hasta ~10% mas largo) siempre da 1 paso, para que el
    movimiento no tiemble. Por debajo de ~54 FPS se compensa con pasos extra.
    """
    if fps_ref <= 0 or maximo < 1:
        raise ValueError("fps_ref debe ser positivo y maximo al menos 1.")
    marcos = max(0.0, dt) * fps_ref
    if 0.85 <= marcos <= 1.12:
        return 1, 0.0
    total = max(0.0, resto) + marcos
    pasos = int(total)
    return min(pasos, maximo), total - pasos if pasos <= maximo else 0.0
