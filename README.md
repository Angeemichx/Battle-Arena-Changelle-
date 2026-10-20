# Battle Arena Challenge

Plataforma multijugador con integración hardware-software.
Curso CE-1105 Principios de Modelado en Ingeniería · II Semestre 2026 · Instituto Tecnológico de Costa Rica.

Dos jugadores compiten en tiempo real dentro de una arena gráfica, controlando su avatar con dispositivos físicos (mandos o panel de botones). El juego incluye registro con verificación de correo, configuración de partida, puntuación, determinación automática del ganador y una pantalla de victoria.

## Arquitectura

El proyecto se divide en cliente y servidor.

```
Cliente/      Interfaz (Pygame), entrada de hardware (Inputs), configuración y red
servidor/     Lógica de juego, autenticación y persistencia (arquitectura por capas)
  domain/            Entidades del negocio
  use_cases/         Reglas de negocio (autenticación, motor de juego)
  adapters/          Repositorio JSON, envío de correo
  infraestructure/   Servidor de sockets y almacenamiento de datos
Documentos/   Enunciados del proyecto
docs/         Documentación técnica
```

El servidor se despliega en un contenedor Docker. El cliente se ejecuta en la máquina local porque necesita acceso a la pantalla y a los dispositivos USB.

## Estrategia de ramas

- `main`: versión estable, se actualiza al cerrar cada Sprint.
- `develop`: integración del trabajo de los Sprints.
- `Sprint_2`, `Sprint_3`: una rama de integración por Sprint.
- `IntN_*`: una rama por integrante dentro de cada Sprint. El código se integra mediante Pull Request con revisión cruzada.

## Pruebas

```
pip install pytest
python -m pytest Cliente/Inputs/Tests Cliente/Config/Tests -q
```

## Documentación

Los detalles de hardware están en `docs/` y la Wiki del repositorio recopila el diseño del proyecto.
