# Registro de decisiones de arquitectura

Formato: **Contexto → Opciones consideradas → Decisión → Justificación → Trade-offs aceptados**

---

## D-01 Lenguaje, framework y librería de Telegram

**Contexto**  
El ecosistema de librerías elegido para el LLM y el cliente de Telegram condiciona toda la arquitectura. Se priorizó madurez del ecosistema ML/AI.

**Opciones consideradas**
- Python 3.11 + python-telegram-bot v21
- TypeScript/Node.js + Telegraf o grammY
- Go + telebot (mínimas librerías ML nativas)

**Decisión**  
Python 3.11 + python-telegram-bot v21.

**Justificación**  
Python domina el ecosistema de ML: LangChain, sentence-transformers, ChromaDB y PyPDF tienen soporte nativo y comunidad activa. python-telegram-bot v21 introdujo soporte nativo de `asyncio`, lo que permite manejar múltiples conversaciones sin bloquear el hilo principal. TypeScript habría requerido wrappers para las librerías de embeddings y un stack separado de ML; Go directamente carece de estas librerías.

**Trade-offs aceptados**  
Python tiene mayor consumo de memoria en reposo que Node.js o Go. Para este caso, el cuello de botella en latencia es siempre el LLM (red), no el runtime del bot. Para un sistema con miles de usuarios concurrentes se evaluaría separar el servidor de Telegram (Node.js) del servicio de RAG (Python), comunicados por HTTP o gRPC.

---

## D-02 Framework de orquestación (LangChain vs implementación propia)

**Contexto**  
El pipeline RAG conecta retrieval + historial + construcción de prompt + llamada al LLM + extracción de fuentes. Se puede implementar con librerías individuales o con un framework de orquestación.

**Opciones consideradas**
- **LangChain 0.3.x**: abstracciones probadas para todos los componentes RAG, multi-proveedor nativo.
- **LlamaIndex**: especializado en indexación y RAG sobre documentos estructurados.
- **Implementación propia**: control total, cero dependencias de orquestación.

**Decisión**  
LangChain 0.3.x con `langchain-community` para las integraciones de ChromaDB y HuggingFace.

**Justificación**  
La capacidad de cambiar de proveedor de LLM (OpenAI → Anthropic → Google) con un solo parámetro de configuración es el principal argumento. LangChain ofrece además abstracciones probadas en producción para el manejo del historial conversacional (mensajes HumanMessage/AIMessage), la construcción del prompt y el retrieval. LlamaIndex habría sido la alternativa más cercana, pero su foco en agentes de recuperación compleja lo hace más pesado para un pipeline RAG lineal como el nuestro.

**Trade-offs aceptados**  
LangChain 0.3.x tiene dependencias transitivas que crean conflictos de versiones si se combinan mal: `langchain-huggingface` y `langchain-chroma` (paquetes separados) actualizan `langchain-core` a 1.x, rompiendo `langchain 0.3.x` que requiere `langchain-core 0.3.x`. La solución fue usar únicamente `langchain-community` para las integraciones y pinear `chromadb < 1.0.0`. Este fue el problema técnico más complejo del proyecto (ver D-04 y `docs/CRITERIO_TECNICO.md §1`).

---

## D-03 Estrategia de fragmentación

**Contexto**  
El tamaño y solapamiento de los fragmentos afectan la precisión del retrieval (fragmentos muy grandes diluyen la señal semántica) y la completitud de la respuesta (fragmentos muy pequeños pueden cortar reglas a la mitad).

**Opciones consideradas**
- `chunk_size=500, overlap=50`: fragmentos pequeños, alta precisión, mayor riesgo de cortar párrafos
- `chunk_size=800, overlap=100`: fragmentos medianos, equilibrio contexto/precisión
- `chunk_size=1200, overlap=200`: fragmentos grandes, contexto completo, menor precisión en retrieval

**Decisión**  
`chunk_size = 800`, `chunk_overlap = 100`, separador `RecursiveCharacterTextSplitter`.

**Justificación**  
Los documentos de políticas típicamente tienen párrafos de 400–700 caracteres. Un chunk de 800 captura entre 1 y 2 párrafos completos, lo que garantiza que las reglas queden dentro de un mismo fragmento y no partidas en la mitad. El splitter `RecursiveCharacterTextSplitter` respeta `\n\n` y `\n` antes de cortar por carácter, mejorando la coherencia semántica. El overlap de 100 (12.5%) asegura continuidad sin duplicar excesivamente el contenido.

**Trade-offs aceptados**  
Fragmentos más grandes incrementan el costo en tokens al pasarlos al LLM. Ambos parámetros son configurables en `.env` sin modificar código, lo que permite ajustarlos según el tipo de documentos de la organización.

---

## D-04 Modelo de embeddings y almacén vectorial

**Contexto**  
El evaluador no debería necesitar una segunda API key para los embeddings. El almacén vectorial debe persistir entre reinicios sin servicios en la nube adicionales.

**Opciones consideradas**  
*Embeddings:* OpenAI `text-embedding-3-small` (API, $0.02/1M tokens), Cohere multilingual (API), HuggingFace local.  
*Almacén:* ChromaDB (local), FAISS (local sin servidor), Qdrant (Docker), pgvector (PostgreSQL).

**Decisión**  
`paraphrase-multilingual-MiniLM-L12-v2` (HuggingFace, local) + ChromaDB persistente en disco.

**Justificación**  
El modelo HuggingFace elegido fue diseñado específicamente para similitud semántica en 50+ idiomas con buen desempeño en español, con solo 50 M de parámetros (ligero frente a modelos más grandes). Al ser local, el evaluador no necesita configurar una segunda API key ni incurrir en costos adicionales de embedding. ChromaDB persiste en la carpeta `chroma_db/` del proyecto sin servidor externo, lo que simplifica el despliegue. FAISS es más rápido en consultas puras pero no soporta modificaciones incrementales nativamente (habría que reconstruir el índice entero en cada ingesta).

**Trade-offs aceptados**  
La primera instalación descarga PyTorch (~1.5 GB). La calidad de los embeddings locales es inferior a `text-embedding-3-large` de OpenAI para preguntas muy específicas o con jerga técnica de la organización. ChromaDB 0.x tiene un único proceso por directorio (no escalable horizontalmente sin migrar a un servidor PersistentClient dedicado).

---

## D-05 Modelo de lenguaje por defecto

**Contexto**  
Elegir el modelo que genera las respuestas buscando el mejor balance calidad/costo/latencia para preguntas de mesa de ayuda en español.

**Opciones consideradas**
- GPT-4o (OpenAI): mayor calidad, $2.50 / 1M tokens input
- **GPT-4o-mini (OpenAI): alta calidad, $0.15 / 1M tokens input**
- Claude 3 Haiku (Anthropic): comparable en precio y calidad
- Gemini 1.5 Flash (Google): el más barato, calidad aceptable

**Decisión**  
`gpt-4o-mini` (OpenAI) como modelo por defecto.

**Justificación**  
En benchmarks de Q&A sobre documentos en español, GPT-4o-mini tiene un desempeño muy cercano a GPT-4o a ~17x menor costo. Para preguntas de RRHH y TI (políticas de vacaciones, reembolsos, trabajo remoto) no se requiere el razonamiento complejo de GPT-4o. El evaluador puede cambiar a cualquier otro proveedor y modelo configurando `LLM_PROVIDER` y `LLM_MODEL` en `.env`.

**Trade-offs aceptados**  
Para documentos muy técnicos o preguntas de múltiples pasos, GPT-4o-mini puede producir respuestas menos precisas. La barrera de similitud (SIMILARITY_THRESHOLD) mitiga esto: si los chunks recuperados no son suficientemente relevantes, el sistema responde que no tiene información en lugar de forzar al LLM a construir algo impreciso.

---

## D-06 Diseño del prompt de sistema y estrategia anti-alucinación

**Contexto**  
Los LLMs tienden a generar información plausible pero falsa cuando no tienen suficiente contexto. En un asistente de RRHH/mesa de ayuda, una respuesta incorrecta sobre vacaciones o reembolsos puede causar perjuicio real.

**Opciones consideradas**
- Instrucción solo en el prompt: "responde solo con la información provista"
- Doble barrera: umbral de similitud + prompt restrictivo
- Fine-tuning del modelo con ejemplos de "no sé": sobrepasa el alcance

**Decisión**  
Doble barrera: `SIMILARITY_THRESHOLD` (primera línea) + `system_prompt.md` restrictivo (segunda línea).

**Justificación**  
Primera barrera: si ningún chunk supera `SIMILARITY_THRESHOLD` (0.30), la respuesta es un mensaje predefinido que nunca llega al LLM, eliminando completamente el riesgo de alucinación. Segunda barrera: el system prompt en `prompts/system_prompt.md` instruye explícitamente al modelo a responder "No tengo información sobre ese tema" si la respuesta no está en los fragmentos provistos. El prompt no está hardcodeado; `SYSTEM_PROMPT_PATH` permite actualizarlo sin modificar código. Se incluyó además detección de 7 patrones de prompt injection en el input del usuario (con log de auditoría, sin bloquear el mensaje).

**Trade-offs aceptados**  
Un umbral muy alto (ej. 0.70) puede filtrar preguntas legítimamente relacionadas cuyo vocabulario difiere del documento. Se eligió 0.30 como valor conservador para no perder preguntas válidas. El prompt restrictivo introduce algo de rigidez: el bot puede responder "no tengo información" a preguntas que podría deducir con conocimiento general; esto es intencional y está documentado como limitación conocida.

---

## D-07 Manejo y almacenamiento del historial conversacional

**Contexto**  
El bot necesita mantener contexto entre mensajes del mismo usuario para responder preguntas de seguimiento ("¿y cuántos días son?", "¿y si trabajo remoto?"). El historial debe ser eficiente y tener un límite configurable.

**Opciones consideradas**
- SQLite: persistente entre reinicios, agrega complejidad de migraciones
- Redis: persistente, alta disponibilidad, requiere servicio adicional
- **Memoria (`deque`)**: simple, sin dependencias, se pierde al reiniciar

**Decisión**  
`collections.deque(maxlen=HISTORY_LENGTH)` por usuario, en memoria.

**Justificación**  
Para una prueba técnica y un sistema de baja concurrencia, la simplicidad supera la persistencia. El `deque` descarta automáticamente los mensajes más antiguos cuando se llena, evitando un crecimiento ilimitado de memoria. La longitud máxima es configurable (`HISTORY_LENGTH=10` por defecto). `/reset` permite al usuario borrar su historial. Para una sesión de preguntas sobre políticas de RRHH, perder el historial al reiniciar el bot es un inconveniente menor.

**Trade-offs aceptados**  
El historial se pierde al reiniciar el bot. Para producción con usuarios frecuentes, Redis con TTL por sesión sería la opción correcta. Se documenta como limitación conocida en el README.

---

## D-08 Mecanismo de configuración y separación de secretos

**Contexto**  
El sistema tiene ~20 parámetros configurables: algunos son secretos (tokens, API keys) y otros son parámetros de comportamiento (tamaño de chunks, temperatura del LLM). Deben configurarse sin modificar código y los secretos no pueden aparecer en el repositorio.

**Opciones consideradas**
- `.env` para secretos + `config.yaml` para parámetros de comportamiento (dos archivos)
- **`.env` único** cargado y validado por Pydantic Settings
- Variables de entorno del sistema operativo

**Decisión**  
`.env` único, cargado y validado por `Pydantic Settings` (`pydantic-settings`).

**Justificación**  
Con 20 parámetros, separar en dos archivos agrega complejidad (dos archivos a gestionar, dos sintaxis) sin un beneficio real de seguridad a esta escala. Pydantic Settings valida tipos automáticamente (int, float, `list[int]`), aplica valores por defecto y falla al arrancar con un mensaje claro si falta una variable requerida. El validador personalizado `_parse_int_list` convierte `"123,456"` → `[123, 456]` para las listas de IDs, simplificando la configuración. **Nota de implementación:** Pydantic Settings v2 pre-parsea los valores numéricos del `.env` como JSON antes de invocar los validadores, de modo que un valor como `"9193063212"` llega al validador ya convertido en `int`, no en `str`. Fue necesario añadir un caso `isinstance(v, int): return [v]` en `_parse_int_list`; sin él, la lista de IDs autorizados quedaba vacía y nadie tenía acceso (bug detectado en prueba real del bot).

**Trade-offs aceptados**  
El `.env` crece conforme se agregan parámetros, mezclando secretos con configuración operacional. Para un proyecto en producción, separar secretos (`.env` con permisos restrictivos) de configuración (`config.yaml` versionable sin secretos) mejoraría la seguridad operativa. Se documenta como mejora para producción en `CRITERIO_TECNICO.md §3`.
