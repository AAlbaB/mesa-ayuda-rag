# Especificación — Asistente de Mesa de Ayuda con RAG en Telegram

**Versión:** 1.0  
**Fecha:** 2026-11-06  
**Autor:** Andres Alba  
**Estado:** Aprobada (baseline para implementación)

---

## 1. Visión general

El área de mesa de ayuda de Servicios Grupo Bios S.A.S. recibe diariamente preguntas repetitivas sobre políticas internas (vacaciones, gastos, TI, trabajo remoto, etc.). Las respuestas existen en documentos internos que los colaboradores no consultan.

Este sistema implementa un asistente conversacional en Telegram que responde preguntas **basándose exclusivamente en los documentos de la organización**, usando el patrón RAG (Retrieval-Augmented Generation). El sistema procesa e indexa los documentos de una carpeta configurable, y ante cada pregunta recupera los fragmentos relevantes para que un modelo de lenguaje construya una respuesta fundamentada.

---

## 2. Historias de usuario

| ID | Historia |
|---|---|
| US-01 | Como **colaborador**, quiero preguntar sobre políticas internas desde Telegram y recibir una respuesta basada en documentos reales, para resolver dudas sin buscar manualmente en archivos dispersos. |
| US-02 | Como **colaborador**, quiero que el asistente recuerde el contexto de nuestra conversación, para hacer preguntas de seguimiento sin repetir información ya dada. |
| US-03 | Como **colaborador**, quiero saber qué documentos tiene disponibles el asistente, para entender qué temas puedo consultarle. |
| US-04 | Como **colaborador no registrado**, quiero recibir un mensaje claro de acceso denegado, para saber que el sistema existe pero no está disponible para mí. |
| US-05 | Como **administrador de mesa de ayuda**, quiero controlar quién puede usar el bot mediante una lista de IDs de Telegram, para evitar accesos no autorizados sin gestionar contraseñas. |
| US-06 | Como **administrador**, quiero poder agregar o actualizar un documento en la carpeta y reindexar sin reiniciar el bot, para mantener la base de conocimiento actualizada sin interrupciones. |

---

## 3. Requisitos funcionales

### RF-01 — Ingesta de documentos

**Prioridad:** Obligatorio

El sistema lee todos los archivos ubicados en `KNOWLEDGE_BASE_PATH` (por defecto `knowledge_base/`) y los procesa para indexación. Formatos soportados: `.md`, `.txt`, `.pdf`, `.docx`.

**Criterios de aceptación:**

| # | Criterio |
|---|---|
| AC-01.1 | Dado un archivo `.md`, `.txt`, `.pdf` o `.docx` válido en `knowledge_base/`, al iniciar el bot o ejecutar `/reindex`, el archivo es procesado y sus fragmentos quedan almacenados en el índice. |
| AC-01.2 | Un archivo con encoding UTF-8 se lee correctamente, incluyendo caracteres especiales en español (tildes, ñ). |
| AC-01.3 | Un archivo ilegible (corrupto, permisos insuficientes, encoding inválido) genera un mensaje de error en el log y **no detiene** la ingesta de los demás archivos. |
| AC-01.4 | El bot informa al usuario (en el caso de `/reindex`) cuántos documentos fueron procesados y cuántos fallaron. |

---

### RF-02 — Indexación persistente

**Prioridad:** Obligatorio

Los fragmentos y sus embeddings se almacenan en un índice vectorial en disco que persiste entre reinicios del bot.

**Criterios de aceptación:**

| # | Criterio |
|---|---|
| AC-02.1 | Al reiniciar el bot sin modificar `knowledge_base/`, el bot responde preguntas sin necesidad de reindexar (el índice carga del disco). |
| AC-02.2 | El directorio del índice es configurable mediante `VECTOR_STORE_PATH` (default: `./chroma_db/`). |
| AC-02.3 | El índice incluye metadatos de cada fragmento: nombre del archivo fuente, índice del chunk, y número de página cuando esté disponible (PDFs). |

---

### RF-03 — Respuesta fundamentada con fuente

**Prioridad:** Obligatorio

El bot responde únicamente con base en los fragmentos recuperados del índice e indica la fuente.

**Criterios de aceptación:**

| # | Criterio |
|---|---|
| AC-03.1 | Cada respuesta incluye al menos el nombre del archivo fuente del fragmento más relevante utilizado. |
| AC-03.2 | Si el fragmento proviene de un PDF y hay número de página disponible, la fuente incluye `(pág. N)`. |
| AC-03.3 | La respuesta no contiene información que no esté en los fragmentos recuperados (verificable comparando respuesta con contexto en logs de debug). |
| AC-03.4 | Se recuperan como máximo `RETRIEVAL_TOP_K` fragmentos (default: 4) para construir la respuesta. |

---

### RF-04 — Manejo de lo desconocido

**Prioridad:** Obligatorio

Si la información no está en los documentos, el asistente lo indica claramente sin inventar.

**Criterios de aceptación:**

| # | Criterio |
|---|---|
| AC-04.1 | Si la similitud del fragmento más relevante es menor a `SIMILARITY_THRESHOLD` (default: 0.3), el bot responde con un mensaje preconfigurado indicando que no tiene información sobre el tema. |
| AC-04.2 | El mensaje de "no sé" no menciona documentos específicos ni inventa fuentes. |
| AC-04.3 | El prompt de sistema instruye explícitamente al LLM a no inventar información y a remitir al mensaje de "no sé" cuando los fragmentos no son suficientes. |
| AC-04.4 | (Si RF-10 implementado) La pregunta sin respuesta se registra en el log de preguntas sin respuesta. |

---

### RF-05 — Contexto conversacional por usuario

**Prioridad:** Obligatorio

El bot mantiene un historial por usuario para entender preguntas de seguimiento.

**Criterios de aceptación:**

| # | Criterio |
|---|---|
| AC-05.1 | Una pregunta de seguimiento (p.ej. "¿y cuántos días son?") recibe una respuesta coherente con la pregunta anterior del mismo usuario. |
| AC-05.2 | El número de mensajes conservados en el historial es configurable con `HISTORY_LENGTH` (default: 10 mensajes). |
| AC-05.3 | El historial de un usuario no afecta el historial de otro usuario. |
| AC-05.4 | El historial se mantiene en memoria del proceso; **no persiste entre reinicios** del bot (supuesto documentado). |
| AC-05.5 | El comando `/reset` borra el historial del usuario que lo ejecuta (ver RF-06). |

---

### RF-06 — Comandos

**Prioridad:** Obligatorio

El bot responde a los siguientes comandos:

| Comando | Comportamiento |
|---|---|
| `/start` | Mensaje de bienvenida con descripción del asistente y resumen de comandos disponibles. |
| `/help` | Lista de comandos disponibles con una línea de descripción cada uno. |
| `/reset` | Borra el historial conversacional del usuario que ejecuta el comando y confirma la acción. |
| `/fuentes` | Lista los documentos indexados (nombre de archivo y formato). |
| `/reindex` | (Solo admin, RF-08 deseable) Reprocesa `knowledge_base/` y actualiza el índice. |

**Criterios de aceptación:**

| # | Criterio |
|---|---|
| AC-06.1 | Todos los comandos obligatorios responden en menos de 5 segundos bajo condiciones normales. |
| AC-06.2 | Si el bot no tiene documentos indexados, `/fuentes` lo indica explícitamente. |
| AC-06.3 | Un usuario sin acceso no puede ejecutar ningún comando (el check de acceso es previo). |

---

### RF-07 — Control de acceso

**Prioridad:** Obligatorio

Solo los usuarios con IDs de Telegram en `ALLOWED_USER_IDS` pueden usar el bot. Los administradores (`ADMIN_USER_IDS`) tienen acceso implícito.

**Criterios de aceptación:**

| # | Criterio |
|---|---|
| AC-07.1 | Un usuario cuyo ID no está en `ALLOWED_USER_IDS` ni en `ADMIN_USER_IDS` recibe un mensaje de acceso denegado ante cualquier mensaje o comando. |
| AC-07.2 | El check de acceso ocurre **antes** de cualquier procesamiento del mensaje (retrieval, LLM, historial). |
| AC-07.3 | El mensaje de acceso denegado no revela información sobre el sistema ni sobre los usuarios autorizados. |
| AC-07.4 | Si `ALLOWED_USER_IDS` está vacío, **nadie** tiene acceso (configuración conservadora — el administrador debe listar explícitamente los IDs). |
| AC-07.5 | Un usuario en `ADMIN_USER_IDS` puede usar todos los comandos incluyendo `/reindex`. |

---

### RF-08 — Reindexación (Deseable)

**Prioridad:** Deseable

Comando `/reindex` restringido a administradores para procesar documentos nuevos o modificados sin reiniciar el bot.

**Criterios de aceptación:**

| # | Criterio |
|---|---|
| AC-08.1 | Solo usuarios en `ADMIN_USER_IDS` pueden ejecutar `/reindex`; los demás reciben un mensaje de acceso insuficiente. |
| AC-08.2 | El bot responde al administrador con un resumen: N documentos procesados, M fallos. |
| AC-08.3 | El índice queda actualizado con los documentos nuevos o modificados. |

---

### RF-09 — Indexación incremental (Deseable)

**Prioridad:** Deseable

Al iniciar o ejecutar `/reindex`, el sistema procesa solo los archivos nuevos o modificados.

**Criterios de aceptación:**

| # | Criterio |
|---|---|
| AC-09.1 | Un archivo que no cambió desde la última indexación **no** se reprocesa. |
| AC-09.2 | Se mantiene un registro de archivos indexados con su hash MD5 y timestamp. |
| AC-09.3 | Un archivo modificado (hash diferente) se reprocesa y sus fragmentos anteriores se eliminan del índice antes de reinsertar los nuevos. |

---

### RF-10 — Log de preguntas sin respuesta (Deseable)

**Prioridad:** Deseable

Las preguntas que activan RF-04 se registran como insumo para mejorar la base de conocimiento.

**Criterios de aceptación:**

| # | Criterio |
|---|---|
| AC-10.1 | Cada pregunta sin respuesta se registra con: timestamp ISO-8601, hash del user_id (no el ID real), y texto de la pregunta. |
| AC-10.2 | El registro se hace en un archivo configurable (`UNANSWERED_LOG_PATH`, default: `unanswered_questions.csv`). |
| AC-10.3 | El archivo de registro **no se sube al repositorio** (incluido en `.gitignore`). |

---

## 4. Requisitos no funcionales

### NF-01 — Parametrización

Todas las variables de la tabla siguiente deben estar en `.env` (nunca en código). Ninguna tiene valor por defecto quemado en el código; los defaults se definen en el modelo de configuración (Pydantic Settings).

| Variable | Tipo | Default | Descripción |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | str | — | Token del bot de Telegram (requerido) |
| `LLM_PROVIDER` | str | `openai` | Proveedor LLM: `openai`, `anthropic`, `google` |
| `LLM_MODEL` | str | `gpt-4o-mini` | Modelo a utilizar |
| `LLM_API_KEY` | str | — | API key del proveedor (requerida) |
| `LLM_TEMPERATURE` | float | `0.1` | Temperatura de generación |
| `LLM_MAX_TOKENS` | int | `512` | Máximo de tokens de la respuesta |
| `EMBEDDING_PROVIDER` | str | `huggingface` | Proveedor de embeddings |
| `EMBEDDING_MODEL` | str | `paraphrase-multilingual-MiniLM-L12-v2` | Modelo de embeddings |
| `KNOWLEDGE_BASE_PATH` | str | `knowledge_base` | Carpeta de documentos |
| `VECTOR_STORE_PATH` | str | `chroma_db` | Directorio de persistencia ChromaDB |
| `CHUNK_SIZE` | int | `800` | Tamaño de fragmento en caracteres |
| `CHUNK_OVERLAP` | int | `100` | Solapamiento entre fragmentos |
| `RETRIEVAL_TOP_K` | int | `4` | Fragmentos recuperados por pregunta |
| `SIMILARITY_THRESHOLD` | float | `0.30` | Similitud mínima para considerar un fragmento relevante |
| `SYSTEM_PROMPT_PATH` | str | `prompts/system_prompt.md` | Ruta del prompt de sistema |
| `HISTORY_LENGTH` | int | `10` | Mensajes de historial por usuario |
| `ALLOWED_USER_IDS` | list[int] | `[]` | IDs de Telegram autorizados |
| `ADMIN_USER_IDS` | list[int] | `[]` | IDs de administradores |
| `RATE_LIMIT_PER_MINUTE` | int | `10` | Máximo mensajes por usuario por minuto |
| `LOG_LEVEL` | str | `INFO` | Nivel de logs (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `UNANSWERED_LOG_PATH` | str | `unanswered_questions.csv` | Archivo de preguntas sin respuesta (RF-10) |

### NF-02 — Ejecución

- El proyecto debe poder ejecutarse con máximo 4 comandos después de configurar `.env`.
- Incluye `.env.example` con todas las variables, valores de ejemplo y comentarios.
- Docker/Docker Compose es deseable.

### NF-03 — Seguridad

- Ninguna API key, token o credencial en código ni en historial de git.
- Mitigación de prompt injection: el prompt de sistema incluye instrucción explícita de ignorar instrucciones del usuario que contradigan las reglas del asistente; los mensajes de usuario se tratan como datos, no como instrucciones.
- Los logs no registran el contenido de secretos ni IDs de usuario en texto plano.

### NF-04 — Calidad

- Manejo de errores con mensaje al usuario: LLM caído, timeout, documento ilegible, mensaje vacío o no textual.
- Logs estructurados en JSON con campos: `timestamp`, `level`, `module`, `event`, `user_id_hash` (nunca el ID real).
- Pruebas automatizadas: configuración, fragmentación, retrieval, control de acceso.
- Type hints en todas las funciones y clases públicas.
- Linter y formateador: `ruff` configurado en `pyproject.toml`.
- Docstrings en módulos, clases y funciones públicas.

---

## 5. Supuestos

| ID | Supuesto |
|---|---|
| A-01 | El historial conversacional no persiste entre reinicios del bot (en memoria). Si se requiere persistencia, es una mejora futura. |
| A-02 | El bot opera en modo polling (no webhook). Adecuado para entornos de desarrollo y prueba. |
| A-03 | El evaluador tiene acceso a internet para descargar el modelo de embeddings en el primer arranque (~420 MB, descarga automática de HuggingFace). |
| A-04 | Se asume Python 3.11+ instalado en el entorno de ejecución. |
| A-05 | Los documentos en `knowledge_base/` pueden estar en español o inglés. El modelo de embeddings elegido es multilingüe. |
| A-06 | "Usuario autorizado" se identifica únicamente por Telegram user_id numérico. No hay gestión de roles adicional. |
| A-07 | El evaluador proveerá su propio `TELEGRAM_BOT_TOKEN` y `LLM_API_KEY`. El proveedor por defecto es OpenAI; se documentan los proveedores alternativos soportados. |
| A-08 | El rate limiting es en memoria y se reinicia al reiniciar el bot. No es distribuido. |

---

## 6. Fuera de alcance

- Persistencia del historial conversacional entre reinicios.
- Webhook mode (el polling es suficiente para la prueba).
- Autenticación con roles granulares (más allá de usuario/admin).
- Soporte para mensajes de voz, imágenes, archivos adjuntos en Telegram.
- Integración con sistemas externos (correo, ticketing, CRM).
- UI web de administración.
- Métricas en tiempo real (dashboard, alertas).
- Autenticación de múltiples administradores con distintos permisos.
- Búsqueda semántica avanzada con reranking.
- Evaluación automática de calidad RAG (RAGAS u otros frameworks).
