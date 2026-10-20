# Resumen del Modulo Integrante 1 y Guia de Integracion (`RESUMEN_INT1.md`)

Este documento resume el trabajo completado por el **Integrante 1 (Arquitectura de Interfaz Hibrida, Lobby Caminable y Arena Pygame)** en la rama `Int1_ui_arena`, las directrices de documentacion y estructura aplicadas al codigo, y lo que se espera de los **Integrantes 2, 3 y 4** para el cierre del proyecto.

---

## 1. Resumen de lo Realizado por el Integrante 1 (`Cliente/Interfaz/`)

Todo el desarrollo del Integrante 1 se mantiene **100% aislado dentro de `Cliente/Interfaz/`, `Cliente/Recursos/` y `main.py`**, en formato de **Directorios limpios (`Cliente/Interfaz`, `Cliente/Interfaz/Components`, `Cliente/Interfaz/Tests`)**, sin modificar ningun archivo de `Cliente/Inputs/`, `Cliente/Red/` ni `Servidor/`.

### 1.1 Estandar Estricto de Documentacion Aplicado en Todo el Codigo
Todos los archivos `.py` del modulo cumplen con la guia de estilo y documentacion requerida:
1. **Documentacion de Clases:** Antes de cada `class` (`AppController`, `CompatibleJsonRepository`, `ClienteAuthAdapter`, `LoginView`, `AdminAccessView`, `SignupView`, `HubView`, `JugarView`, `PerfilView`, `SettingsView`, `HeaderAvatar`) se incluye un bloque detallado con:
   - **Proposito:** Responsabilidad exacta de la clase.
   - **Contenido:** Atributos principales y metodos que la conforman.
2. **Documentacion de Funciones y Metodos (Docstrings):** Todas las funciones y metodos contienen:
   - **Descripcion:** Que hace la funcion.
   - **Entradas:** Nombre, tipo de dato y proposito de cada parametro.
   - **Salidas:** Que retorna la funcion y su tipo de dato.
   - **Restricciones:** Condiciones previas, limites, validaciones y manejo de errores.
3. **Comentarios de Linea (Inline):** Explican el *"por que"* en calculos de centrado, resolucion independiente de colisiones en ejes X/Y, deteccion de flancos del mando (`esperando_soltar_accion`), sintesis de audio `.wav` y proyeccion a escala del mini-radar.

### 1.2 Arquitectura de Ventana Unica y Adaptacion Dinamica a la Resolucion
- **[`main.py`](main.py) y [`Cliente/Interfaz/root.py`](Cliente/Interfaz/root.py):**
  - Controlador maestro (`AppController`) que gestiona la transicion en **una sola ventana activa a la vez** (`CustomTkinter` para vistas administrativas $\leftrightarrow$ `Pygame` para Lobby Caminable y Arena).
  - **Escalado dinamico:** Todas las ventanas consultan las dimensiones reales del monitor (`winfo_screenwidth/height` en Tkinter y `pygame.display.Info()` en Pygame) y adaptan tamanos de fuente, paneles, zonas y camara proporcionalmente.
  - **Persistencia local:** Guarda preferencias de color de hitbox, imagen de avatar y volumen en `Cliente/Recursos/config_local.json`.
  - **Audio continuo:** Genera y reproduce automaticamente `Cliente/Recursos/ambiente_espacial.wav` mediante `pygame.mixer`.

### 1.3 Autenticacion Estricta, Rechazo Notorio y Ventana de Acceso Admin (`US-01`, `US-02`, `US-03`)
- **[`Cliente/Interfaz/auth_adapter.py`](Cliente/Interfaz/auth_adapter.py), [`login_view.py`](Cliente/Interfaz/login_view.py) y [`signup_view.py`](Cliente/Interfaz/signup_view.py):**
  - Se conectan al formato de `Servidor/infraestructure/data/usuarios.json` y a la entidad `Cuenta` del Integrante 4 usando `bcrypt`.
  - **Restriccion estricta de Inicio de Sesion:** Si el usuario no tiene una cuenta creada y verificada en `usuarios.json`, o si la contrasena no coincide con el hash `bcrypt`, el Login **bloquea el acceso** y despliega un recuadro rojo de **`ACCESO RECHAZADO`**.
  - **Boton unico `ACCESO ADMIN` y ventana `AdminAccessView`:**
    - En la ventana de Login existe un unico boton discreto **`ACCESO ADMIN`** (sin mostrar nunca la contrasena en pantalla).
    - Al presionarlo, abre una ventana dedicada donde se solicita primero la contrasena oculta (`*`) y luego permite elegir **`ENTRAR COMO ADMIN 1`** o **`ENTRAR COMO ADMIN 2`**.
    - **Verificacion de sesion activa en otro ordenador:** Consulta el estado de red (`estado_partida_red["jugadores"]`) y la sala activa (`verificar_usuario_en_uso`); si otro ordenador ya esta conectado con `Admin 1`, marca el boton como **`ADMIN 1 (EN USO)`** y rechaza el ingreso para evitar duplicados.
  - **Flujo obligatorio de Correo y Codigo de 6 digitos en `Sign Up`:** Valida formato de correo (`usuario@dominio.com`), usuario unico, contrasena alfanumerica de $\ge 8$ caracteres y exige el **codigo de verificacion de 6 digitos** antes de crear la cuenta.

### 1.4 Vistas Administrativas y Componentes (`US-05`, `US-06`, `US-08`)
- **[`avatar_select_view.py`](Cliente/Interfaz/avatar_select_view.py), [`hub_view.py`](Cliente/Interfaz/hub_view.py), [`jugar_view.py`](Cliente/Interfaz/jugar_view.py), [`perfil_view.py`](Cliente/Interfaz/perfil_view.py), [`settings_view.py`](Cliente/Interfaz/settings_view.py) y [`Cliente/Interfaz/Components/`](Cliente/Interfaz/Components/):**
  - **Selector de Avatar en CustomTkinter (`avatar_select_view.py` - US-06):** Ventana dedicada accesible desde el Menú Principal para previsualizar y elegir entre los 5 colores base (#E63946, #1D3557, #2A9D8F, #E9C46A, #7209B7), cargar imagen de avatar desde disco mediante `filedialog` y persistir la configuración en `config_local.json`.
  - **Header Avatar persistente** en la barra superior (`Components/header_avatar.py`).
  - **Salas de Partida (`Jugar`):** Permite crear sala como Anfitrion (Host) o conectarse como Invitado por IP y Puerto.
  - **Configuracion de Audio (`Settings`):** Slider de volumen de `0%` a `100%` en tiempo real con boton `LISTO` que retorna a la vista de origen.

### 1.5 Lobby Caminable 100% Controlable con Mando (`US-09`, `US-10`, `US-11`)
- **[`Cliente/Interfaz/lobby_view.py`](Cliente/Interfaz/lobby_view.py):**
  - **3 Zonas Fisicas en el Piso del Lobby:**
    1. **Zona Izquierda (`SALIR AL MENU`):** Regresa al menu administrativo caminando hacia la izquierda y presionando el **5to boton de accion (`Command.ACTION`)**.
    2. **Zona Central (`MESA DE COMANDO`):** Al presionar el **5to boton de accion**, abre el modal de configuracion.
    3. **Zona Derecha (`ZONA DE DESPEGUE`):** Al presionar el **5to boton de accion**, valida las restricciones e inicia la partida hacia la Arena.
  - **Movimiento suave sin saltos en bordes y bloqueo de seguridad del boton de accion:**
    - Almacena las coordenadas exactas en pixeles (`pos_x`, `pos_y`) para deslizarse suavemente por los bordes de la Mesa de Comando.
    - Al regresar de una partida al Lobby, ubica al jugador local en la zona central segura (`rel_x = 0.50, rel_y = 0.78`) y exige **soltar fisicamente el boton de accion y volverlo a tocar (`esperando_soltar_accion`)** antes de activar cualquier zona.
  - **Navegacion Completa por Mando dentro del Modal de la Mesa:**
    - `UP` / `DOWN`: Cambia entre la fila de Pestanas, Opciones y el boton `LISTO`.
    - `LEFT` / `RIGHT`: Recorre pestanas o las opciones de **Colores** (con exclusion mutua **CA-10.3**), **Mapa y Parametros** (Duracion `1, 3, 5 min` y Meta de Puntos `300, 500, 800 pts` con candado para invitados **CA-10.2**) y **Musica**.
    - `Command.ACTION`: Confirma la opcion seleccionada o cierra el modal en `LISTO`.
  - **Restriccion Notoria de Minimo 2 Jugadores (`CA-09.5`):**
    - Si hay menos de 2 jugadores en la sala ($< 2/4$), la Zona de Despegue **rechaza el inicio de la partida** y muestra un banner rojo de alerta.
    - *Atajo de prueba local:* Presionar **`F2`** en el Lobby simula la conexion de un 2do a 4to jugador; **`F3`** lo retira.

### 1.6 Arena de Batalla ($3600 \times 2600$ px), Meta de 500 Puntos y Victoria (`US-07`, `US-14`, `US-15`, `US-16`, `US-17`)
- **[`Cliente/Interfaz/arena_collisions.py`](Cliente/Interfaz/arena_collisions.py) y [`arena_view.py`](Cliente/Interfaz/arena_view.py):**
  - **Mapa ampliado a $3600 \times 2600$ px:** Diseñado con pasillos amplios para 4 jugadores y guardianes, con **Reactor Central en `(1800, 1300)`** y **4 plataformas de Spawn** (Norte, Sur, Oeste, Este).
  - **Camara con seguimiento (`Camera Follow`) y HUD (`Components/hud.py`):** Muestra el mini-avatar del jugador, reloj central `MM:SS`, tarjetas de puntaje y **Mini-Radar en tiempo real**.
  - **Reglas de Puntuacion por Segundo:**
    - **Movimiento:** Cada **1 segundo** acumulado en movimiento suma **+10 puntos** ($\text{segundos\_movimiento} \times 10$).
    - **Extraccion en Reactor:** Al mantener presionado el **5to boton (`Command.ACTION`)** dentro del radio del Reactor Central, el jugador se detiene, muestra el aro de su color + `[EXTRAYENDO +40 PTS/S]` y cada **1 segundo** suma **+40 puntos** ($\text{segundos\_reactor} \times 40$).
  - **Meta de 500 Puntos, Desempate Automatico (`CA-16.4`) y Pantalla de Victoria (`US-17`):**
    - La meta predeterminada es de **500 puntos**.
    - Si el reloj llega a `00:00` o un jugador alcanza los `500 pts`, evalua al ganador.
    - **Desempate automatico (`CA-16.4`):** Si hay empate en el primer lugar, **suma automaticamente +2 minutos (`120s`)** al reloj y muestra un banner de desempate.
    - **Pantalla de Victoria (`US-17`):** Muestra el avatar del campeon, felicitacion, tabla de posiciones ordenada y permite **volver al Lobby presionando el 5to boton del mando (`Command.ACTION`)** tras haber soltado el boton previamente.

---

## 2. ¿Que Esperamos de los Demas Integrantes para la Integracion Final?

### 2.1 Lo que esperamos del **Integrante 2** (`Cliente/Inputs/` - Mando y Controles)
1. **Mantener intacta la firma de `gamepad_manager.py`:**
   - Nuestra interfaz importa y utiliza `Command` (`UP`, `DOWN`, `LEFT`, `RIGHT`, `ACTION`), `create_default_input_manager(allow_keyboard_fallback=True)` y `direction_from(commands)`.
2. **Vibracion / Feedback Haptico (Opcional):**
   - Si el Integrante 2 expone un metodo de vibracion al extraer en el Reactor o colisionar, puede invocarse directamente en `arena_view.py`.

### 2.2 Lo que esperamos del **Integrante 3** (`Cliente/Red/` y `Servidor/partida.py` - Sockets TCP y Sincronizacion)
1. **Envio de paquetes de estado (`tipo: "estado"`) con coordenadas, nombre y color:**
   - [`AppController.actualizar_estado_red(datos)`](Cliente/Interfaz/root.py) ya procesa los paquetes JSON del servidor TCP:
     ```json
     {
       "tipo": "estado",
       "jugadores": [
         {"id": 1, "nombre": "Admin 1", "x": 1800, "y": 260, "puntaje": 50, "color": "#E63946", "color_nombre": "Rojo"}
       ],
       "activa": true,
       "ganador": null
     }
     ```
   - Esto permite sincronizar en red la posicion en el mapa de $3600 \times 2600$ px, la **exclusion mutua de colores (`CA-10.3`)**, el conteo de jugadores (`2/4`, `3/4`, `4/4`) y la verificacion de si **`Admin 1` o `Admin 2` ya estan conectados en otro ordenador**.
2. **Evento de Inicio de Partida y Guardianes:**
   - Escuchar la accion `"INICIAR_PARTIDA"` enviada por el Host y, cuando esten listos los guardianes, enviarlos en el paquete `"estado"` para dibujarlos en `world_surface`.

### 2.3 Lo que esperamos del **Integrante 4** (`Servidor/` - Persistencia, Correo Real SMTP, Cuentas y Reglas de Dominio)
1. **Envio Real del Correo Electronico de Verificacion (`US-02`):**
   - La interfaz de `Sign Up` (`Cliente/Interfaz/signup_view.py`) ya tiene toda la validacion visual y del codigo de 6 digitos.
   - **Responsabilidad del Integrante 4:** Configurar y conectar el servicio de envio de correo real en `Servidor/use_cases/auth_service.py` (o su adaptador SMTP en `Servidor/adapters/`) para que el codigo de 6 digitos llegue al correo real del usuario.
2. **Unificar nombres de metodos en `Servidor/adapters/json_repository.py` y `Servidor/use_cases/auth_service.py`:**
   - Alinear `get_by_email(email)` y `username_exists(username)` en `json_repository.py` (actualmente cubiertos por nuestra clase `CompatibleJsonRepository` en `Cliente/Interfaz/auth_adapter.py`).
3. **Persistencia de Estadisticas / Historial de Partidas (`US-16` / `US-17`):**
   - Indicarnos el metodo del repositorio para guardar el `jugador_ganador` y el `ranking` al finalizar la partida en `arena_view.py`.

---

## 3. Como Ejecutar y Probar Todo el Modulo

1. **Iniciar la aplicacion:**
   ```powershell
   py main.py
   ```
2. **Ejecutar las 36 pruebas unitarias:**
   ```powershell
   py -m pytest
   ```
