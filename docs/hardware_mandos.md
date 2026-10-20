# Integración con hardware: mandos (US-12)

**Responsable:** Integrante 2 · **Rama:** `Int2_mandos` · **Módulo:** `Cliente/Inputs/gamepad_manager.py`

## Controles

| Comando del juego | Mando (D-pad) | Mando (joystick izquierdo) | Teclado (respaldo) |
|---|---|---|---|
| `UP` | Arriba | Eje Y negativo | Flecha arriba / W |
| `DOWN` | Abajo | Eje Y positivo | Flecha abajo / S |
| `LEFT` | Izquierda | Eje X negativo | Flecha izquierda / A |
| `RIGHT` | Derecha | Eje X positivo | Flecha derecha / D |
| `ACTION` | Botón 0 (A en Xbox, Cruz en PS5) | — | Barra espaciadora |

- El D-pad tiene prioridad sobre el joystick.
- El joystick usa una zona muerta de 0.4 para ignorar la deriva.
- El botón de acción se puede cambiar con `GamepadMapping(action_buttons=...)`.

## Flujo hardware → software

1. El mando produce un estado de botones/ejes.
2. `GamepadInput.poll()` lo traduce a un conjunto de `Command`.
3. `InputManager` combina todas las fuentes activas.
4. `direction_from()` convierte los comandos en un desplazamiento `(dx, dy)` en coordenadas de pantalla.
5. La arena mueve el avatar y el cliente envía el movimiento al servidor.

## Cómo ejecutar las pruebas

```
pip install pytest
python -m pytest Cliente/Inputs/Tests -q
```

Las pruebas usan un mando simulado, así que no requieren hardware conectado.

## Estado de los criterios de aceptación

| Criterio | Estado |
|---|---|
| CA-12.1 Existe un dispositivo físico funcional | Probado con un control de PS4 (19/10/2026) |
| CA-12.2 Mínimo cinco controles | Probado en físico: D-pad/joystick (4 direcciones) + botón de acción |
| CA-12.3 Cada botón genera un evento identificable | Implementado (`Command`) |
| CA-12.4 El evento llega al software | Implementado (`poll()`) |
| CA-12.5 El software lo transforma en acción de juego | Implementado (`direction_from`) |
| CA-12.6 El movimiento por hardware modifica el avatar | Integrado en lobby y arena (Integrante 1 usa `InputManager`) |
| CA-12.7 Los demás jugadores observan el movimiento | Pendiente: depende de la sincronización por red (Integrante 3) |

## Prueba con hardware real

- Control probado: **PS4 (DualShock 4)** conectado por USB, detectado por pygame sin configuración extra.
- Para repetir la prueba y ver los números de botón de cualquier control: `py -m pytest` no la cubre, se hace a mano ejecutando el juego (`py main.py`) y moviéndose por el lobby con el control.
- Si algún control usa otro botón de acción, se cambia con `GamepadMapping(action_buttons=(n,))` sin tocar el resto del código.

## Pendientes

- [ ] Adjuntar evidencia (captura o video corto) de la prueba con el control.
- [ ] Confirmar con el profesor que un control comercial cuenta como el dispositivo de cinco botones.
- [ ] Sincronizar el movimiento entre jugadores por red (Integrante 3).
