# Reglas de extracción, guardianes y eventos (US-18, US-21, US-22)

**Responsable:** Integrante 2 · **Código:** `Servidor/domain/dinamicas.py` · **Pruebas:** `Servidor/pruebas/test_dinamicas.py`, `Servidor/pruebas/test_movimiento_red.py`

El servidor es la autoridad: calcula puntos, congelamientos, guardianes y eventos, y los clientes solo los dibujan (CA-21.8). Moverse nunca da puntos (CA-19.4).

## Extracción de energía (US-18 / US-19)

| Condición | Resultado |
|---|---|
| Partida activa, dentro del radio de 210 px, no congelado, reactor disponible | Se pagan **40 pts por segundo** de extracción (x2 en "Doble extracción") |
| Partida inactiva | Rechazada: "La partida no esta activa" |
| Fuera del radio | Rechazada: "Acercate al reactor para extraer" |
| Congelado | Rechazada: "Estas congelado" |
| Reactor sobrecargado | Rechazada: "Reactor en sobrecarga, espera" |

- Los puntos se miden con el reloj del servidor, no por cantidad de mensajes: copias o retransmisiones del mismo evento no suman (CA-18.8). Una pausa mayor a 0.5 s reinicia la sesión de extracción.
- El motivo de un rechazo llega solo a quien lo causó (`{"tipo":"rechazo","mensaje":...}`) y se repite como máximo cada 1.5 s.
- Al terminar la partida (meta de puntos o tiempo) no se aceptan más extracciones (CA-25.3).

## Guardianes y congelamiento (US-21)

- 4 guardianes base, uno en cada esquina; durante el evento "Refuerzo de guardianes" aparecen 5 más.
- **Comportamiento:** persiguen al avatar no congelado más cercano a 200 px/s (un jugador va a ~420 px/s). Sin objetivo, vuelven a su puesto.
- **Contacto** (≤ 44 px): el jugador queda congelado 5 s (configurable con `congelamiento`). Durante un evento especial, un nuevo contacto suma tiempo al que ya tenía, con tope de 4 veces la duración base.
- El guardian se recarga 3 s tras congelar (se aleja a su puesto).
- Un congelado no se mueve (el servidor ignora su posición) ni extrae; se libera solo al terminar el tiempo.
- Los guardianes nunca modifican el puntaje.

## Eventos especiales (US-22)

Se programan al iniciar la partida, uno a la vez y sin traslapes, entre el 10 % y el 95 % de la duración, en orden aleatorio. Si la partida es corta se reduce la duración de cada evento.

| Evento | Veces | Duración máx. | Efecto |
|---|---|---|---|
| Energía adicional | 3 | 15 s | Icono en lugar aleatorio; el primero que lo toca gana 80 pts y desaparece |
| Refuerzo de guardianes | 1 | 30 s | 5 guardianes extra con las mismas reglas |
| Sobrecarga del reactor | 2 | 12 s | El reactor se desactiva: no se puede extraer |
| Doble extracción (creativo) | 1 | 15 s | La extracción paga el doble |
| Tormenta eléctrica (creativo) | 1 | 15 s | Los guardianes van 1.6 veces más rápido |

Al terminar un evento (o la partida) se restauran las condiciones anteriores y ninguno se aplica dos veces.

## Estado que reciben los clientes

El mensaje `estado` incluye: `guardianes` (`id`, `x`, `y`, `extra`), `estado_reactor` (`disponible` o `sobrecargado`), `evento_especial` (`tipo`, `nombre`, `activo`, `restante`, y `x`, `y`, `puntos` para la energía adicional), y por jugador `congelado` y `congelado_restante`. También `partida_finalizada`, `ganador_id`, `puntos_meta` y `modo`.

`configurar_partida` acepta `minutos`, `puntos`, `modo` (`tiempo`, `puntos` o ninguno = lo que ocurra primero) y `congelamiento`. Cada partida nueva reinicia los puntajes.

## Pendiente / límites conocidos

- Los guardianes no esquivan muros: el servidor no conoce el mapa de obstáculos (los dibuja el cliente).
- Las trampas (US-20) son locales al cliente; el servidor no las valida.
