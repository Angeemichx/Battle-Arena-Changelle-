"""Pruebas de la capa de entrada: sin mando ni pygame (mando simulado)."""
import pytest

from Cliente.Inputs.gamepad_manager import (
    Command,
    GamepadInput,
    GamepadMapping,
    InputDeviceError,
    InputManager,
    KeyboardInput,
    direction_from,
)


class FakeJoystick:
    def __init__(self, axes=(0.0, 0.0), buttons=(0,), hat=(0, 0), numhats=1, name="Fake"):
        self.axes, self.buttons, self.hat = list(axes), list(buttons), hat
        self.numhats, self.name = numhats, name

    def get_name(self): return self.name
    def get_numaxes(self): return len(self.axes)
    def get_numbuttons(self): return len(self.buttons)
    def get_numhats(self): return self.numhats
    def get_axis(self, i): return self.axes[i]
    def get_button(self, b): return self.buttons[b]
    def get_hat(self, i): return self.hat


# ---------- pruebas positivas: los 5 botones ----------

@pytest.mark.parametrize(
    "hat, expected",
    [((0, 1), Command.UP), ((0, -1), Command.DOWN),
     ((-1, 0), Command.LEFT), ((1, 0), Command.RIGHT)],
)
def test_dpad_genera_las_cuatro_direcciones(hat, expected):
    pad = GamepadInput(FakeJoystick(hat=hat))
    assert pad.poll() == {expected}


@pytest.mark.parametrize(
    "axes, expected",
    [((0.0, -0.9), Command.UP), ((0.0, 0.9), Command.DOWN),
     ((-0.9, 0.0), Command.LEFT), ((0.9, 0.0), Command.RIGHT)],
)
def test_joystick_genera_las_cuatro_direcciones(axes, expected):
    pad = GamepadInput(FakeJoystick(axes=axes, numhats=0))
    assert pad.poll() == {expected}


def test_boton_accion():
    pad = GamepadInput(FakeJoystick(buttons=(1, 0)))
    assert pad.poll() == {Command.ACTION}


def test_diagonal_y_accion_simultaneas():
    pad = GamepadInput(FakeJoystick(hat=(1, 1), buttons=(1,)))
    assert pad.poll() == {Command.RIGHT, Command.UP, Command.ACTION}


def test_teclado_de_respaldo():
    state = {1: True, 2: False, 3: False, 4: False, 5: True}
    kb = KeyboardInput(
        lambda: state,
        {Command.UP: (1,), Command.DOWN: (2,), Command.LEFT: (3,),
         Command.RIGHT: (4,), Command.ACTION: (5,)},
    )
    assert kb.poll() == {Command.UP, Command.ACTION}


def test_manager_une_fuentes():
    a = GamepadInput(FakeJoystick(hat=(1, 0)))
    b = GamepadInput(FakeJoystick(buttons=(1,)))
    assert InputManager([a, b]).poll() == {Command.RIGHT, Command.ACTION}


def test_direction_from_coordenadas_de_pantalla():
    assert direction_from({Command.UP, Command.LEFT}) == (-1, -1)
    assert direction_from({Command.DOWN}) == (0, 1)


# ---------- pruebas negativas ----------

def test_zona_muerta_ignora_deriva_del_joystick():
    pad = GamepadInput(FakeJoystick(axes=(0.1, -0.2), numhats=0))
    assert pad.poll() == frozenset()


def test_sin_botones_presionados_no_hay_comandos():
    assert GamepadInput(FakeJoystick()).poll() == frozenset()


def test_direcciones_opuestas_se_cancelan():
    assert direction_from({Command.LEFT, Command.RIGHT}) == (0, 0)


def test_mando_sin_ejes_ni_dpad_es_rechazado():
    with pytest.raises(InputDeviceError):
        GamepadInput(FakeJoystick(axes=(), numhats=0))


def test_mando_sin_botones_es_rechazado():
    with pytest.raises(InputDeviceError):
        GamepadInput(FakeJoystick(buttons=()))


def test_boton_de_accion_inexistente_no_revienta():
    pad = GamepadInput(FakeJoystick(buttons=(0,)), GamepadMapping(action_buttons=(7,)))
    assert pad.poll() == frozenset()


@pytest.mark.parametrize("kwargs", [{"deadzone": 1.0}, {"deadzone": -0.1}, {"action_buttons": ()}])
def test_mapeo_invalido_es_rechazado(kwargs):
    with pytest.raises(ValueError):
        GamepadMapping(**kwargs)
