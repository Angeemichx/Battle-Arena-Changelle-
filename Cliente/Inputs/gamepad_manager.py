"""Capa de entrada del cliente (US-11 / US-12).

Convierte lo que haga el hardware (mando Xbox/PS5) o el teclado de respaldo
en *comandos del juego* independientes del dispositivo. El resto del cliente
(arena_view, red) solo conoce `Command`, nunca botones ni ejes concretos.

Diseño (SOLID):
- `InputSource` es la abstracción; `GamepadInput` y `KeyboardInput` son
  implementaciones intercambiables (Open/Closed, Liskov).
- `InputManager` combina fuentes sin saber de pygame (Dependency Inversion).
- Este módulo no importa pygame al cargarse, por lo que se puede probar
  sin ventana ni mando físico. Solo `create_default_input_manager` lo usa.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Iterable, Mapping, Protocol


class Command(Enum):
    """Los cinco controles mínimos exigidos por el stakeholder."""

    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    ACTION = auto()


class InputDeviceError(Exception):
    """El dispositivo de entrada no es utilizable (faltan ejes, etc.)."""


class JoystickLike(Protocol):
    """Subconjunto de `pygame.joystick.Joystick` que necesitamos."""

    def get_name(self) -> str: ...
    def get_numaxes(self) -> int: ...
    def get_numbuttons(self) -> int: ...
    def get_numhats(self) -> int: ...
    def get_axis(self, axis_number: int) -> float: ...
    def get_button(self, button: int) -> int: ...
    def get_hat(self, hat_number: int) -> tuple[int, int]: ...


@dataclass(frozen=True)
class GamepadMapping:
    """Qué eje/botón corresponde a cada comando. Ajustable por mando."""

    axis_x: int = 0
    axis_y: int = 1
    hat_index: int = 0
    deadzone: float = 0.4
    action_buttons: tuple[int, ...] = (0,)  # A en Xbox / Cruz en PS5

    def __post_init__(self) -> None:
        if not 0.0 <= self.deadzone < 1.0:
            raise ValueError("deadzone debe estar en el rango [0, 1)")
        if not self.action_buttons:
            raise ValueError("Debe haber al menos un botón de acción")


class InputSource(ABC):
    """Una fuente de comandos (mando, teclado, panel serial, etc.)."""

    @abstractmethod
    def poll(self) -> frozenset[Command]:
        """Comandos activos en este instante."""


class GamepadInput(InputSource):
    """D-pad (hat) o joystick izquierdo + botón de acción."""

    def __init__(self, joystick: JoystickLike, mapping: GamepadMapping | None = None):
        self._joy = joystick
        self._map = mapping or GamepadMapping()
        self._validate()

    @property
    def name(self) -> str:
        return self._joy.get_name()

    def _validate(self) -> None:
        needed_axes = max(self._map.axis_x, self._map.axis_y) + 1
        has_hat = self._joy.get_numhats() > self._map.hat_index
        if self._joy.get_numaxes() < needed_axes and not has_hat:
            raise InputDeviceError(
                f"'{self.name}' no tiene ejes ni D-pad utilizables para moverse."
            )
        if self._joy.get_numbuttons() < 1:
            raise InputDeviceError(f"'{self.name}' no tiene botones.")

    def poll(self) -> frozenset[Command]:
        active: set[Command] = set()
        dx, dy = self._read_direction()
        if dx < 0:
            active.add(Command.LEFT)
        elif dx > 0:
            active.add(Command.RIGHT)
        if dy < 0:
            active.add(Command.UP)
        elif dy > 0:
            active.add(Command.DOWN)
        if self._action_pressed():
            active.add(Command.ACTION)
        return frozenset(active)

    def _read_direction(self) -> tuple[int, int]:
        # 1) D-pad: prioridad, es digital y sin deriva.
        if self._joy.get_numhats() > self._map.hat_index:
            hx, hy = self._joy.get_hat(self._map.hat_index)
            if hx or hy:
                return hx, -hy  # el hat usa +1 = arriba; pantalla usa +y = abajo
        # 2) Joystick analógico con zona muerta.
        if self._joy.get_numaxes() > max(self._map.axis_x, self._map.axis_y):
            ax = self._joy.get_axis(self._map.axis_x)
            ay = self._joy.get_axis(self._map.axis_y)
            dz = self._map.deadzone
            return (
                (ax > dz) - (ax < -dz),
                (ay > dz) - (ay < -dz),
            )
        return 0, 0

    def _action_pressed(self) -> bool:
        n = self._joy.get_numbuttons()
        return any(
            b < n and self._joy.get_button(b) for b in self._map.action_buttons
        )


class KeyboardInput(InputSource):
    """Respaldo de desarrollo cuando no hay mando conectado.

    `key_state` es un callable que devuelve algo indexable por código de tecla
    (en pygame: `pygame.key.get_pressed`).
    """

    def __init__(
        self,
        key_state: Callable[[], Mapping[int, bool]],
        key_map: Mapping[Command, Iterable[int]],
    ):
        self._key_state = key_state
        self._key_map = {cmd: tuple(keys) for cmd, keys in key_map.items()}

    def poll(self) -> frozenset[Command]:
        state = self._key_state()
        return frozenset(
            cmd
            for cmd, keys in self._key_map.items()
            if any(state[k] for k in keys)
        )


class InputManager:
    """Une varias fuentes y entrega un único conjunto de comandos."""

    def __init__(self, sources: Iterable[InputSource] = ()):
        self._sources: list[InputSource] = list(sources)

    def add_source(self, source: InputSource) -> None:
        self._sources.append(source)

    def clear_sources(self) -> None:
        self._sources.clear()

    @property
    def sources(self) -> tuple[InputSource, ...]:
        return tuple(self._sources)

    def poll(self) -> frozenset[Command]:
        active: set[Command] = set()
        for source in self._sources:
            active |= source.poll()
        return frozenset(active)


def direction_from(commands: Iterable[Command]) -> tuple[int, int]:
    """(dx, dy) en coordenadas de pantalla. Direcciones opuestas se cancelan."""
    cmds = set(commands)
    dx = (Command.RIGHT in cmds) - (Command.LEFT in cmds)
    dy = (Command.DOWN in cmds) - (Command.UP in cmds)
    return dx, dy


def create_default_input_manager(
    mapping: GamepadMapping | None = None,
    allow_keyboard_fallback: bool = True,
) -> InputManager:
    """Detecta el primer mando; si no hay (y se permite), usa el teclado."""
    import pygame  # import tardío: solo aquí se necesita pygame

    pygame.joystick.init()
    manager = InputManager()
    if pygame.joystick.get_count() > 0:
        joy = pygame.joystick.Joystick(0)
        joy.init()
        manager.add_source(GamepadInput(joy, mapping))
    elif allow_keyboard_fallback:
        manager.add_source(
            KeyboardInput(
                pygame.key.get_pressed,
                {
                    Command.UP: (pygame.K_UP, pygame.K_w),
                    Command.DOWN: (pygame.K_DOWN, pygame.K_s),
                    Command.LEFT: (pygame.K_LEFT, pygame.K_a),
                    Command.RIGHT: (pygame.K_RIGHT, pygame.K_d),
                    Command.ACTION: (pygame.K_SPACE,),
                },
            )
        )
    else:
        raise InputDeviceError("No hay mando conectado.")
    return manager
