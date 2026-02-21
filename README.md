# Sistema de Telemedicina y Asistencia Médica IA

## Descripción
Este proyecto es una plataforma de **Telemedicina y Control Médico Remoto** impulsada por Inteligencia Artificial. Utilizando la arquitectura de 3 capas del *Gemini Agent Framework*, el sistema actúa como un asistente médico avanzado capaz de:

- **Generar reportes médicos** detallados basados en investigación confiable.
- **Analizar exámenes de laboratorio e informes** en formato PDF.
- **Interactuar por voz y texto** vía Telegram para acompañamiento de pacientes.
- **Gestionar memoria a largo plazo** para recordar historiales y preferencias del paciente.

## Requisitos Previos

- **Python 3.10+**
- **Conda** (Recomendado para gestión de entornos)
- **Clave de API** (Configurada en `.env`)

## Inicialización del Proyecto (Desde Plantilla)

Para comenzar un nuevo desarrollo basado en este framework:

1.  **Clonar la plantilla:**
    ```bash
    git clone <URL_DEL_REPOSITORIO> <NOMBRE_NUEVO_PROYECTO>
    cd <NOMBRE_NUEVO_PROYECTO>
    ```

2.  **Ejecutar configuración automática:**
    Este script crea el entorno Conda, instala dependencias e inicializa el proyecto.
    ```bash
    bash setup.sh
    ```

3.  **Configurar credenciales:**
    Edita el archivo `.env` generado y añade tus API Keys.

4.  **Activar entorno:**
    Para empezar a trabajar en futuras sesiones:
    ```bash
    conda activate agent_env
    ```

## Uso

Para iniciar el agente médico y conectarlo a Telegram:
```bash
# Iniciar el modo escucha de Telegram
python execution/listen_telegram.py
# O para pruebas en consola:
# python execution/run_agent.py
```

## Arquitectura del Agente
Este proyecto utiliza una arquitectura de 3 capas (Directivas, Orquestación, Ejecución). Para detalles técnicos sobre cómo operar o extender el agente, consulta:

- [Instrucciones del Agente](.gemini/instructions.md)
- [Framework y Filosofía](.gemini/AGENT_FRAMEWORK.md)

## Herramientas de Desarrollo
Este framework incluye herramientas para facilitar tareas comunes:

- **`init_project.py`**: Script para limpiar y configurar un nuevo proyecto desde esta plantilla.
- **`create_new_directive.yaml`**: Directiva para generar automáticamente el esqueleto de nuevas directivas.
- **`update_template.yaml`**: Directiva para traer actualizaciones desde el repositorio plantilla original.
- **`deploy_to_github.yaml`**: Automatiza el flujo de git add/commit/push para reportar avances.

## Control Remoto vía Telegram
Este framework permite controlar al agente desde tu móvil usando Telegram.

### Configuración
1.  **Crear el Bot**:
    - Abre Telegram y busca a **@BotFather**.
    - Envía `/newbot` y sigue las instrucciones.
    - Copia el **HTTP API Token** generado.

2.  **Obtener tu Chat ID**:
    - Añade el `TELEGRAM_BOT_TOKEN` al archivo `.env`.
    - Envía un mensaje (ej. "Hola") a tu nuevo bot en Telegram.
    - Ejecuta: `python execution/telegram_tool.py --action get-id`
    - Copia el ID que aparece en pantalla.

3.  **Actualizar .env**:
    Añade las siguientes líneas a tu archivo `.env`:
    ```env
    TELEGRAM_BOT_TOKEN=tu_token_aqui
    TELEGRAM_CHAT_ID=tu_id_numerico_aqui
    ```

    **Opcional: Multi-Usuario**
    Por defecto, el bot solo te responde a ti. Para permitir que otros (ej. estudiantes) lo usen:
    ```env
    # Opción A: Permitir a TODO el mundo (Público)
    TELEGRAM_ALLOWED_USERS=*
    # Opción B: Lista blanca (IDs separados por comas)
    # TELEGRAM_ALLOWED_USERS=12345678,87654321
    ```

### ¿Cómo encontrar el Bot?
A veces el buscador de Telegram tarda en indexar bots nuevos por su nombre ("MiAgenteIA").
Para asegurar que tus estudiantes lo encuentren:
1.  Diles que busquen por el **usuario exacto** (ej. `@CERO97_BOT`).
2.  O mejor aún, envíales el enlace directo: `https://t.me/CERO97_BOT`

### Comandos Disponibles
Una vez activado el modo escucha (`/telegram` en el CLI), puedes usar:
- **Chat normal**: Habla con el agente para consultas generales.
- **`/investigar [tema]`**: El agente buscará en internet y te dará un resumen (ej. `/investigar últimas noticias de IA`).
- **`/resumir [url]`**: Lee una web y te dice de qué trata.
- **`/recordar [texto]`**: Guarda una nota en la memoria a largo plazo del agente.
- **`/memorias`**: Muestra una lista de los últimos recuerdos almacenados.
- **`/olvidar [ID]`**: Elimina un recuerdo específico usando su ID.
- **`/ayuda`**: Muestra la lista de comandos disponibles.

### Gestión de Pacientes (Rol Médico)
- **`/nuevo_paciente [Nombre]`**: Registra un nuevo paciente (ID automático).
- **`/pacientes`**: Lista todos los pacientes activos.
- **`/monitorear [ID]`**: Ver signos vitales de un paciente específico.
- **`/simular_crisis [ID]`**: Provocar una crisis en un paciente específico.
- **`/estabilizar [ID]`**: Restaurar signos vitales normales.

### Documentación
En la carpeta `docs/` encontrarás los manuales de usuario (`manual_medico.tex` y `manual_paciente.tex`) listos para compilar a PDF.
Para generarlos (requiere tener LaTeX instalado):
```bash
pdflatex -output-directory=docs docs/manual_medico.tex
pdflatex -output-directory=docs docs/manual_paciente.tex
```

## Integración con Hardware (ESP32-CAM)
El sistema soporta la integración de una cámara ESP32-CAM para dotar al agente de "visión".

### Configuración
1.  **Firmware**:
    - **Seguridad WiFi**: No escribas tu contraseña en el código. Agrégala al archivo `.env`:
      ```env
      WIFI_SSID=NombreDeTuRed
      WIFI_PASSWORD=TuContraseña
      ```
    - **Sincronización**: Ejecuta el script para generar las credenciales seguras para la cámara:
      ```bash
      python execution/sync_wifi_credentials.py
      ```
    - **Carga**: Abre el archivo `.ino` (en `execution/` o `firmware/SimpleCamServer/`) con Arduino IDE y súbelo. El código leerá automáticamente las credenciales generadas.

2.  **Conexión**:
    - Obtén la IP de la cámara desde el Monitor Serie.
    - Agrégala a tu archivo `.env`:
      ```env
      ESP32_CAM_IP=192.168.1.XXX
      ```

### Notas de Hardware
- **Alimentación**: Se recomienda usar el pin de **5V**. La placa consume picos de corriente altos; si se reinicia al tomar fotos (error "Brownout"), tu fuente de energía es insuficiente.
- **Modo Ejecución**: Recuerda desconectar el cable entre `IO0` y `GND` después de subir el código y presionar el botón de **Reset** para iniciar el servidor.
- **Sin Tarjeta SD**: Este firmware no requiere tarjeta microSD; las imágenes se procesan en la RAM y se envían directamente.

### Uso
El agente utiliza la directiva `capture_image.yaml` para interactuar con el hardware. Puedes pedirle explícitamente que tome una foto o que analice el entorno visual.

## Reportar Avances (Git)
Para guardar tu trabajo y subirlo a GitHub, puedes usar la herramienta de despliegue incluida:

1.  **Primera subida (si reiniciaste el historial):**
    ```bash
    python execution/deploy_to_github.py --message "Entrega inicial" --remote <URL_TU_REPO>
    ```

2.  **Avances diarios:**
    ```bash
    python execution/deploy_to_github.py --message "Implementando función X"
    ```

## Mantenimiento y Contribución
Si deseas proponer cambios o mejoras, consulta la [Guía de Contribución](CONTRIBUTING.md).

Para mantener este proyecto actualizado con la plantilla original, puedes utilizar la directiva `directives/update_template.yaml`. Esta herramienta permite al agente traer los últimos cambios del repositorio base y fusionarlos con tu trabajo actual.

## Licencia
Este proyecto está bajo la Licencia MIT. Consulta el archivo [LICENSE](LICENSE) para más detalles.