# Uso de herramientas de inteligencia artificial

---

## 1. Herramientas utilizadas

| Herramienta | Modelo / versión | Rol en el proyecto |
|---|---|---|
| **Claude Code** (CLI de Anthropic) | claude-sonnet-4-6 | Asistente principal: especificación, diseño, generación de código, pruebas y documentación |

No se utilizaron otras herramientas de IA de forma sistemática. Claude Code fue el único asistente durante todo el desarrollo.

---

## 2. Para qué y en qué etapa se usó

| Etapa | Uso concreto |
|---|---|
| **Especificación (SDD)** | Redacción colaborativa de `specs/spec.md`, `specs/plan.md` y `specs/tasks.md`. El desarrollador proveyó el contexto del problema y los requisitos del documento de la prueba; Claude Code propuso la estructura de historias de usuario, criterios de aceptación y el desglose en 38 tareas. |
| **Diseño** | Propuesta de la arquitectura en capas (ingesta, retrieval, LLM, bot, seguridad), selección de librerías y justificación de decisiones. El desarrollador tomó las decisiones finales y pidió ajustes en la selección de modelos de embeddings y LLM. |
| **Implementación** | Generación de todos los módulos de código Python. Claude Code escribió el código; el desarrollador revisó la lógica, corrigió comportamientos y detectó vulnerabilidades de seguridad. |
| **Pruebas** | Generación de los 40 casos de prueba distribuidos en 4 archivos. El desarrollador verificó la cobertura y solicitó casos adicionales para edge cases. |
| **Documentos ficticios** | Generación del **contenido** de los 5 documentos de `knowledge_base/` (políticas de vacaciones, reembolso de gastos, trabajo remoto, soporte de TI y guía de bienvenida). Todos son **ficticios**: corresponden a una empresa imaginaria llamada *Nexus Soluciones S.A.S.* y no representan ninguna organización real. El texto de cada documento fue redactado por **Claude (claude-sonnet-4-6)**; los archivos `.pdf` se materializaron con `fpdf2` ejecutado dentro del entorno virtual del proyecto. |
| **Documentación** | Redacción de todos los archivos `docs/` y `README.md`. El desarrollador proveyó las respuestas técnicas (criterio propio) y Claude Code estructuró y redactó el texto. |

---

## 3. Flujo de trabajo

El proyecto siguió un ciclo corto por tarea:

1. El desarrollador describía la tarea con contexto técnico suficiente (ej. "implementa el sanitizador con 7 patrones de prompt injection, debe logguear warning pero no bloquear el mensaje").
2. Claude Code generaba el código o documento.
3. El desarrollador leía el resultado, lo probaba si era código (ejecutando los tests o inspeccionando manualmente), y pedía correcciones específicas.
4. Se hacía commit con mensaje Conventional Commits que referenciaba la tarea (`[T-XX]`).

Para tareas grandes (ej. `handlers.py` con todo el pipeline RAG), el desarrollador dividió la tarea en subtareas y revisó cada parte antes de continuar.

---

## 4. Prompts representativos

### Prompt 1 — Especificación inicial

> *"Contexto: prueba técnica 'Asistente de mesa de ayuda con RAG en Telegram' para Servicios Grupo Bios S.A.S. [...] La metodología es Spec Driven Development (SDD) — specs deben estar commitadas antes de cualquier código. Stack aprobado: Python 3.11+, python-telegram-bot v21, LangChain 0.3.x, ChromaDB, HuggingFace embeddings local (paraphrase-multilingual-MiniLM-L12-v2), OpenAI GPT-4o-mini, .env-only config, Gitflow. Crea specs/spec.md, specs/plan.md y specs/tasks.md con el estándar SDD."*

**Por qué así:** Se dio todo el contexto de la prueba en un solo prompt, incluyendo la metodología (SDD), el stack ya aprobado y las restricciones (Gitflow, .env-only). Sin ese contexto, Claude Code habría propuesto un stack diferente y no habría entendido la restricción de que los specs debían existir antes que el código.

### Prompt 2 — Implementación del sanitizador con restricción de seguridad

> *"Implementa src/security/sanitizer.py: truncado a 2000 chars; detecta 7 patrones de inyección con regex; solo logguea warning (no bloquea el mensaje porque el system prompt es la defensa real); doc de cada patrón con la técnica que mitiga."*

**Por qué así:** Se especificó el comportamiento exacto (no bloquear) y el motivo de diseño (el system prompt es la defensa real). Sin eso, Claude Code habría propuesto bloquear el mensaje, lo que habría dado falsos positivos en preguntas legítimas con palabras como "ignora" o "olvida".

### Prompt 3 — Corrección de conflicto de versiones

> *"langchain-huggingface está actualizando langchain-core a 1.x, rompiendo langchain 0.3.x. También chromadb 1.5.9 se instaló con API incompatible. Solución: quitar langchain-huggingface y langchain-chroma de las dependencias, usar langchain_community.embeddings.HuggingFaceEmbeddings y langchain_community.vectorstores.Chroma, pinear chromadb<1.0.0, actualizar indexer.py, recrear el venv."*

**Por qué así:** El desarrollador ya había diagnosticado el problema; el prompt tenía la causa raíz y la solución. Claude Code ejecutó los cambios coordinados en pyproject.toml, indexer.py y la recreación del venv.

### Prompt 4 — Lazy imports para tests sin torch

> *"Los tests no deben requerir instalar torch (1.5 GB) para correr. Mover los imports de HuggingFaceEmbeddings y Chroma a lazy (dentro de los métodos) en indexer.py, y mover el import de VectorIndexer a TYPE_CHECKING en retriever.py."*

**Por qué así:** Se especificó exactamente el mecanismo (lazy imports + TYPE_CHECKING), no solo el objetivo. Eso evitó soluciones alternativas como mocking a nivel de módulo, que habrían complicado el código de producción.

### Prompt 5 — Auditoría de seguridad

> *"Revisa src/security/, src/ingestion/pipeline.py y src/bot/handlers.py buscando: 1) user_id en texto plano en logs, 2) manejo incompleto de archivos eliminados en el modo incremental, 3) inyección de fórmulas CSV en el log de preguntas sin respuesta, 4) cualquier otro problema de seguridad visible."*

**Por qué así:** Se listaron explícitamente las categorías de vulnerabilidad a buscar. Una pregunta genérica "¿tiene problemas de seguridad?" habría producido una revisión superficial.

---

## 5. Sugerencias que rechacé o corregí

Esta sección es la más relevante para demostrar criterio sobre lo generado.

**Rechazo 1 — Build backend incorrecto en pyproject.toml**  
Claude Code generó `build-backend = "setuptools.backends.legacy:build"`. Al ejecutar la instalación, esta ruta no existe en setuptools moderno. Se corrigió a `setuptools.build_meta`. Lección: siempre verificar que el código generado funciona antes de hacer commit.

**Rechazo 2 — SHA-256 simple para user_id en logs**  
La primera versión de `hash_user_id()` usaba `hashlib.sha256(str(user_id).encode()).hexdigest()`. Los user_ids de Telegram son números secuenciales en un rango acotado (~100M IDs), lo que hace esta función vulnerable a ataques de preimagen por fuerza bruta (un atacante puede hashear todos los IDs posibles y buscar coincidencias en el log). Se rechazó y se implementó HMAC-SHA256 con `LOG_HASH_KEY` del entorno.

**Rechazo 3 — langchain-huggingface como dependencia principal**  
Claude Code propuso inicialmente `langchain-huggingface` y `langchain-chroma` como las dependencias para embeddings y vector store. Esto creó el conflicto de versiones descrito en §1. Se rechazó y se migró a `langchain-community`.

**Rechazo 4 — pip install en el Python del sistema**  
Durante la generación de PDFs ficticios, Claude Code intentó ejecutar `pip install fpdf2` sobre el Python del sistema en lugar del entorno virtual del proyecto. Se rechazó; se estableció la regla de usar siempre `.venv/Scripts/pip` para cualquier instalación.

**Rechazo 5 — Commits directamente en master**  
Claude Code hizo el primer commit de código directamente en la rama `master`. Se rechazó y se estableció el flujo Gitflow: `master` solo recibe merges `--no-ff` desde `develop`, todo el desarrollo ocurre en `feature/*`.

**Rechazo 7 — parse_mode="Markdown" para mensajes con nombres de archivo**
La propuesta inicial formateaba todos los mensajes del bot con `parse_mode="Markdown"`. En la prueba real del bot, los nombres de archivo con guiones bajos (`manual_soporte_ti.pdf`) provocaron errores de Telegram ("Can't parse entities") porque los guiones bajos se interpretan como marcadores de itálica. Se rechazó y se migró a `parse_mode="HTML"` para las fuentes (donde se controla el formato) y sin parse_mode para los mensajes estáticos.

**Rechazo 8 — Validador de IDs sin manejo del tipo int**
El validador `_parse_int_list` original solo manejaba `str` y `list`. Durante la prueba real se descubrió que Pydantic Settings v2 pre-parsea los valores de `.env` como JSON antes de invocar los validadores: un ID único como `9193063212` llega como `int`, no como `str`. El validador retornaba `[]` y nadie tenía acceso. Se rechazó la implementación original y se añadió el caso `isinstance(v, int): return [v]`.

**Rechazo 6 — Bloquear mensajes detectados como inyección**  
La propuesta inicial del sanitizador bloqueaba mensajes que coincidieran con los patrones de inyección. Se rechazó porque genera falsos positivos: palabras como "ignora", "olvida" o "pretende" aparecen en preguntas legítimas ("¿puedo ignorar las instrucciones del jefe?"). La defensa real es el system prompt; el sanitizador solo registra el intento.

---

## 6. Qué verifiqué manualmente y cómo

| Aspecto | Método de verificación |
|---|---|
| **Conflictos de versiones** | `pip show langchain-core chromadb` antes y después de cada instalación |
| **Generación de PDFs** | Abrir los archivos PDF en el visor del sistema para verificar que el texto era legible y el formato correcto |
| **Lazy imports** | Verificar que `python -m pytest tests/ -v` corre sin instalar sentence-transformers |
| **40 tests pasan** | `pytest tests/ -v` con las dependencias de producción instaladas |
| **Patrón Gitflow** | `git log --oneline --graph` para verificar la historia de ramas |
| **Credenciales fuera del repositorio** | `git log --all --full-history -- .env` para confirmar que el archivo nunca fue commitado |
| **Linting** | `ruff check src/ tests/` para verificar que el código no tiene errores de estilo |

---

## 7. Proporción IA vs. criterio propio

| Componente | Generado por IA | Criterio propio |
|---|---|---|
| Código fuente | ~80% (estructura y sintaxis) | ~20% (decisiones de diseño, correcciones de seguridad, ajustes de comportamiento) |
| Especificación (specs/) | ~60% (redacción) | ~40% (qué incluir, qué dejar fuera, prioridades) |
| Decisiones de arquitectura | ~30% (redacción) | ~70% (las decisiones en sí, las justificaciones técnicas, los rechazos) |
| Criterio técnico | ~20% (redacción y estructura) | ~80% (las respuestas son criterio propio del desarrollador) |
| Evaluación del RAG | ~40% (formato y preguntas de ejemplo) | ~60% (selección de preguntas de seguimiento, análisis de resultados, ajustes) |

La proporción de IA es alta en la generación de código repetitivo (boilerplate, casos de prueba, configuración). El criterio propio dominó en las decisiones de arquitectura, el diagnóstico de problemas y la evaluación crítica de lo generado.
