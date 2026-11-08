# Asistente de Mesa de Ayuda con RAG en Telegram

Bot conversacional que responde preguntas sobre políticas internas de la organización,
basándose exclusivamente en los documentos de `knowledge_base/`. Si la información no
está en los documentos, el bot lo dice claramente sin inventar.

**Proveedores de LLM soportados:** OpenAI, Anthropic (Claude), Google (Gemini).  
**Embeddings:** modelo local HuggingFace — el evaluador **no** necesita una segunda API key.

---

## Tabla de contenido

- [Requisitos previos](#requisitos-previos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Ejecución](#ejecución)
- [Cómo agregar o actualizar documentos](#cómo-agregar-o-actualizar-documentos)
- [Uso](#uso)
- [Limitaciones conocidas](#limitaciones-conocidas)
- [Documentación adicional](#documentación-adicional)

---

## Requisitos previos

| Requisito | Versión mínima | Notas |
|---|---|---|
| Python | 3.11 | Verificar con `python --version` |
| API key de LLM | — | OpenAI, Anthropic o Google (una sola) |
| Token de Telegram | — | Obtenido de @BotFather |

---

## Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/AAlbaB/mesa-ayuda-rag.git
cd mesa-ayuda-rag

# 2. Crear entorno virtual e instalar dependencias
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
# source .venv/bin/activate

pip install -e .
```

> **Primera instalación:** `sentence-transformers` descarga PyTorch (~1.5 GB).
> Es normal que tarde 5–15 minutos. Las ejecuciones siguientes son inmediatas.

---

## Configuración

### 1. Crear el bot en Telegram

1. Abre Telegram y busca **@BotFather**.
2. Envía `/newbot` y sigue las instrucciones.
3. Copia el **token** que BotFather entrega (formato `123456789:AAF...`).

### 2. Obtener tu ID de usuario de Telegram

1. Busca **@userinfobot** en Telegram y envía cualquier mensaje.
2. Copia el número del campo `Id` (ej. `987654321`).

### 3. Crear y editar el archivo `.env`

```bash
cp .env.example .env
```

Edita `.env` con al menos estos cuatro valores:

```ini
TELEGRAM_BOT_TOKEN=token_de_botfather

# Proveedor: openai | anthropic | google
LLM_PROVIDER=openai
LLM_API_KEY=sk-...

# IDs de Telegram autorizados (separados por coma si son varios)
ALLOWED_USER_IDS=987654321
# Para poder usar /reindex:
ADMIN_USER_IDS=987654321
```

Consulta [`.env.example`](.env.example) para ver todas las variables con descripción y valores por defecto.

**Variables de modelo según proveedor:**

| Proveedor | `LLM_MODEL` sugerido |
|---|---|
| `openai` | `gpt-4o-mini` (por defecto) |
| `anthropic` | `claude-3-haiku-20240307` |
| `google` | `gemini-1.5-flash` |

---

## Ejecución

### Opción A — Python directo

```bash
python -m src.main
```

### Opción B — Docker (recomendado, no requiere Python instalado)

```bash
# Primera vez: construye la imagen e inicia el contenedor
docker compose up --build

# Siguientes arranques (imagen ya construida)
docker compose up
```

> **Primera construcción:** `sentence-transformers` descarga PyTorch (~1.5 GB) dentro del contenedor. Puede tardar 10–20 minutos según la conexión. Las ejecuciones siguientes usan el volumen `hf_cache` y son inmediatas.

El bot indexa automáticamente los documentos de `knowledge_base/` y queda a la espera de mensajes.
La terminal mostrará logs en formato JSON con el estado de cada operación.

---

## Cómo agregar o actualizar documentos

1. Copia el archivo en la carpeta `knowledge_base/`.  
   Formatos soportados: `.md`, `.txt`, `.pdf`, `.docx`.
2. **Opción A — próximo inicio:** el bot detecta el cambio por hash MD5 y solo reindexará el archivo nuevo o modificado.
3. **Opción B — sin reiniciar:** envía `/reindex` al bot (requiere ser administrador en `ADMIN_USER_IDS`).

No es necesario modificar ningún archivo de código.

---

## Uso

| Comando | Descripción | Acceso |
|---|---|---|
| `/start` | Mensaje de bienvenida | Todos |
| `/help` | Lista de comandos | Todos |
| `/fuentes` | Documentos indexados actualmente | Todos |
| `/reset` | Borra tu historial de conversación | Todos |
| `/reindex` | Reindexar `knowledge_base/` sin reiniciar | Solo admins |

Escribe tu pregunta directamente en el chat. El bot responde con la información de los documentos y cita la fuente.

**Ejemplos de preguntas:**

```
¿Cuántos días de vacaciones tengo al año?
¿Cómo solicito el reembolso de un taxi?
¿Puedo trabajar desde casa todos los días?
¿Qué hago si se me olvida mi contraseña?
```

---

## Limitaciones conocidas

- **Historial en memoria:** el historial conversacional se pierde al reiniciar el bot. Para producción se recomendaría Redis.
- **Solo texto:** el bot no procesa imágenes, audio ni archivos enviados directamente por Telegram; los documentos deben estar en `knowledge_base/` previamente.
- **Control de acceso manual:** `ALLOWED_USER_IDS` se configura en `.env`; no hay interfaz de administración web.
- **Primera carga del modelo:** los embeddings se descargan (~100 MB) la primera vez que se ejecuta el bot. Las siguientes cargas usan caché local (`~/.cache/huggingface/`).
- **Concurrencia:** el modelo de embeddings local carga en un solo proceso. Para múltiples réplicas se requeriría un servidor de embeddings independiente.

---

## Ejecutar las pruebas

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

40 casos de prueba cubren configuración, fragmentación, retrieval y control de acceso.

---

## Documentación adicional

| Archivo | Contenido |
|---|---|
| [specs/spec.md](specs/spec.md) | Historias de usuario, requisitos y criterios de aceptación |
| [specs/plan.md](specs/plan.md) | Arquitectura, componentes y tecnologías |
| [specs/tasks.md](specs/tasks.md) | Tareas de implementación con estado actual |
| [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md) | Diagrama de componentes, flujos y estructura de carpetas |
| [docs/DECISIONES.md](docs/DECISIONES.md) | Registro de 8 decisiones de arquitectura (ADR) |
| [docs/USO_IA.md](docs/USO_IA.md) | Transparencia sobre el uso de herramientas de IA |
| [docs/EVALUACION.md](docs/EVALUACION.md) | Evaluación de calidad del RAG con 10 preguntas |
| [docs/CRITERIO_TECNICO.md](docs/CRITERIO_TECNICO.md) | Reflexiones técnicas y análisis de producción |
| [docs/TRAZABILIDAD.md](docs/TRAZABILIDAD.md) | Matriz de trazabilidad RF→tarea→commit→prueba→estado |
| [.env.example](.env.example) | Plantilla de configuración completa y comentada |
