# Battle Arena Challenge

Plataforma multijugador con integración hardware-software.
Curso CE-1105 Principios de Modelado en Ingeniería · II Semestre 2026 · Instituto Tecnológico de Costa Rica.

Dos jugadores compiten en tiempo real dentro de una arena gráfica, controlando su avatar con dispositivos físicos (mandos o panel de botones). El juego incluye registro con verificación de correo, configuración de partida, puntuación, determinación automática del ganador y una pantalla de victoria.

## Cómo se juega

1. Inicio de sesión o registro (con verificación de correo y recuperación de contraseña).
2. Menú principal: perfil, ajustes y selección de avatar.
3. **Jugar**: crear sala (anfitrión) o unirse a una (invitado).
4. Lobby caminable: el anfitrión configura la partida (tiempo o puntos para ganar).
5. Arena: los jugadores se mueven por el mapa y **extraen energía del Reactor Central** manteniendo el botón de acción dentro de su zona.
6. Pantalla de victoria con el ganador y la tabla de posiciones.

### Puntuación

- Extraer en el Reactor: **+40 puntos por segundo**.
- Moverse **no** otorga puntos.
- La partida termina al alcanzar la meta de puntos o al agotarse el tiempo, según la configuración. Si hay empate en el primer lugar se aplica el desempate automático (+2 minutos, o una meta mayor en el modo por puntos).

### Controles

| Comando | Mando | Teclado |
|---|---|---|
| Mover | D-pad o joystick izquierdo | Flechas / WASD |
| Acción (extraer) | Botón 0 | Barra espaciadora |

Detalles en `docs/hardware_mandos.md`. Se probó con un mando de PS4.

## Arquitectura

El proyecto se divide en cliente y servidor.

```
Cliente/      Interfaz (CustomTkinter + Pygame), entrada de hardware, configuración y red
  Interfaz/        Vistas (login, hub, lobby, arena, victoria...) y sincronización de red
  Inputs/          Mandos y teclado (GamepadManager, InputManager)
  Config/          Configuración de partida y validaciones
  descubrimiento.py  Búsqueda automática del servidor en la red
Servidor/     Lógica de juego, autenticación y persistencia (arquitectura por capas)
  domain/            Entidades del negocio (Jugador, Partida, Cuenta)
  use_cases/         Reglas de negocio (autenticación)
  adapters/          Repositorio JSON, envío de correo
  infraestructure/   Servidor de sockets TCP
  pruebas/           Pruebas del servidor
  descubrimiento_servidor.py  Responde a la búsqueda del cliente por UDP
Documentos/   Enunciados y documentos de los Sprints
docs/         Documentación técnica
```

El servidor se despliega en un contenedor Docker. El cliente se ejecuta en la máquina local porque necesita acceso a la pantalla y a los dispositivos USB.

### Comunicación

Mensajes JSON, uno por línea, sobre TCP (puerto `5555`). El cliente envía `identificar`, `movimiento` (posición absoluta, puntaje y color) y `accion`; el servidor responde con `bienvenida` y difunde el `estado` de la partida a todos los jugadores. Máximo 2 jugadores por partida.

El cliente encuentra el servidor por difusión UDP (puerto `5556`) en la red Radmin VPN. También se puede indicar la IP del anfitrión al unirse, o fijarla con las variables de entorno `SERVER_HOST` y `SERVER_PORT`.

## Cómo ejecutar

Requisitos: Python 3.11 o superior y Docker (para el servidor).

**Servidor** (en la máquina anfitriona, con Docker Desktop abierto):

```
iniciar_servidor.bat
```

Reinicia el contenedor y lanza el servicio de descubrimiento. Para ejecutarlo sin Docker: `pip install -r Servidor/requirements.txt` y `python -m Servidor.main_servidor`.

**Cliente** (en cada computadora):

```
pip install customtkinter pillow pygame-ce
python main.py
```

Para jugar en dos computadoras, ambas deben estar en la misma red (Radmin VPN) y tener actualizados cliente y servidor.

## Estrategia de ramas

- `main`: versión estable, se actualiza al cerrar cada Sprint.
- `develop`: integración del trabajo de los Sprints.
- `IntN_*`: una rama por integrante o tema. Nadie edita `develop` ni `main` directamente: el código se integra mediante Pull Request con revisión cruzada (`IntN_*` → `develop` → `main`).

## Pruebas

```
pip install pytest pygame-ce bcrypt python-dotenv
python -m pytest Servidor/pruebas/test_partida.py Servidor/pruebas/test_movimiento_red.py -q
python -m pytest Cliente/Inputs/Tests Cliente/Config/Tests Cliente/Tests -q
python -m pytest Cliente/Interfaz/Tests/test_red_sync.py Cliente/Interfaz/Tests/test_pasos.py -q
```

Las pruebas de interfaz completas (`Cliente/Interfaz/Tests`) requieren CustomTkinter instalado. El pipeline de Azure DevOps (`azure-pipelines.yml`) ejecuta las pruebas del servidor y las del cliente que no necesitan ventana.

## Documentación

Los detalles de hardware están en `docs/` y la Wiki del repositorio recopila el diseño del proyecto.
