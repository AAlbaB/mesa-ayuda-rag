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

1. El desarrollador describía la tarea con contexto técnico suficiente.
2. Claude Code generaba el código o documento.
3. El desarrollador leía el resultado, lo probaba si era código (ejecutando los tests o inspeccionando manualmente), y pedía correcciones específicas.
4. Se hacía commit con mensaje Conventional Commits que referenciaba la tarea (`[T-XX]`).

Para tareas grandes (ej. `handlers.py` con todo el pipeline RAG), el desarrollador dividió la tarea en subtareas y revisó cada parte antes de continuar.

---

## 4. Prompts representativos

### Prompt 1 — Arranque por fases con compuerta de aprobación

> *”Contexto: prueba técnica “Asistente de mesa de ayuda con RAG en Telegram”. Requisitos completos en ./Prueba_técnica_-_Analista_Transformación_Digital.md. Léelo completo y trátalo como fuente de verdad. Entrega límite: lunes 09/11/2026, 12:00 m. Hoy es viernes 06/11/2026.*
>
> *Metodología obligatoria: Spec Driven Development. La especificación debe existir y estar commiteada ANTES que cualquier código. Un solo commit o specs posteriores al código invalidan la entrega.*
>
> *FASE 0 — Análisis (sin escribir código ni archivos):*
> *1. Resume: requisitos obligatorios vs. deseables (RF-01..RF-10), no funcionales (parametrización, ejecución, seguridad, calidad), entregables y criterios que invalidan la entrega.*
> *2. Lista ambigüedades y supuestos que debo confirmar. Propón opciones con trade-offs para: lenguaje [Python/Java/otro], framework de Telegram, orquestación RAG vs. implementación propia, almacén vectorial local, embeddings locales vs. API, LLM por defecto, fragmentación, configuración (.env vs. YAML). Recomienda una opción por tema y espera mi decisión.*
> *3. Propón un cronograma realista hasta el lunes 12:00, priorizando obligatorios sobre deseables.*
>
> *FASE 1 — Especificación (tras mi aprobación de la Fase 0):*
> *1. `git init`, `.gitignore` (sin .env, índices, venv, dependencias) y primer commit.*
> *2. Crear specs/spec.md (historias de usuario, requisitos refinados con criterios de aceptación verificables, supuestos, fuera de alcance), specs/plan.md (arquitectura, componentes, modelo de datos, flujos; referencia los RF) y specs/tasks.md (tareas T-01, T-02… vinculadas a requisitos, con estado).*
> *3. Commit solo de specs. Detente y espera mi aprobación.*
>
> *FASE 2 — Implementación (tras aprobar specs):*
> *- Una tarea de tasks.md a la vez, con commits pequeños en Conventional Commits que referencien la tarea: `feat(retrieval): agrega umbral de similitud [T-07]`.*
> *- Orden: estructura base y config → ingesta/indexación (.md, .txt, .pdf; persistente) → recuperación y respuesta con fuente → manejo de lo desconocido → historial por usuario → comandos (/start, /help, /reset, /fuentes) → control de acceso → rate limit → pruebas → deseables (/reindex, indexación incremental, log de preguntas sin respuesta, .docx, Docker).*
> *- Si cambio de decisión, actualiza specs y registra el motivo.*
>
> *Reglas transversales:*
> *- Cero secretos en código o git; incluye .env.example comentado con todas las variables del documento (sección 4.1) y system prompt en prompts/system_prompt.md.*
> *- Mitigación de prompt injection documentada e implementada.*
> *- Errores visibles al usuario (LLM caído, timeout, documento ilegible, mensaje vacío/no textual) y logs estructurados sin secretos.*
> *- Pruebas de lógica central (config, chunking, retrieval, control de acceso).*
> *- Docstrings, type hints, formateador y linter configurados.*
> *- Ejecutable con README en máximo 3-4 comandos; no depender del contenido de mis documentos de ejemplo.*
> *- Incluye 3-5 documentos ficticios en knowledge_base/ (al menos uno PDF).*
> *- Prioriza pocas cosas bien hechas sobre muchas a medias.*
>
> *FASE 3 — Documentación (README.md, docs/ARQUITECTURA.md, DECISIONES.md, USO_IA.md, EVALUACION.md con ≥10 preguntas: ≥3 fuera de alcance y ≥2 de seguimiento, CRITERIO_TECNICO.md con las 7 preguntas). Ve registrando decisiones y uso de IA durante el desarrollo, no al final.*
>
> *Empieza solo con la FASE 0.”*

**Por qué así:**
- **Fases con aprobación:** el documento invalida la entrega si las specs se commitean después del código, así que separé análisis, especificación, implementación y documentación, y exigí detenerse a esperar mi aprobación entre fases.
- **Decisiones con opciones, no impuestas:** pedí alternativas con trade-offs en lenguaje, framework, almacén vectorial, embeddings, LLM, chunking y configuración, para decidir y poder justificar después cada elección en DECISIONES.md.
- **Restricciones desde el inicio:** incluí los criterios de invalidación (secretos, commits pequeños con ID de tarea, specs primero) y las reglas transversales para que el agente las aplicara desde el principio en lugar de corregirlas al final.
- **Alcance acotado:** terminé con “Empieza solo con la FASE 0” para evitar que escribiera código antes de revisar el plan.
- **Origen:** lo redacté con ayuda de Claude (chat) a partir del documento de requisitos y lo ejecuté en Claude Code.

### Prompt 2 — Diagnóstico de bug durante la prueba real

> *"El bot arranca bien pero rechaza al usuario aunque el ID correcto está en el .env. Ejecuta: `.venv/Scripts/python -c "from src.config import get_settings; s = get_settings(); print('allowed:', s.allowed_user_ids)"`"*

**Por qué así:** En lugar de revisar el código a ciegas, el prompt aisló el problema en una sola variable: si `get_settings()` devuelve `[]` con el `.env` presente, el bug está en el parseo de la config, no en el bot. Esa salida (`allowed: []`) fue suficiente para identificar que Pydantic Settings v2 pre-parsea el valor como JSON (`json.loads("9193063212") == 9193063212`, un `int`, no un `str`) antes de invocar el validador de campo. El prompt de diagnóstico previno varios ciclos de prueba y error en el código del bot.

### Prompt 3 — Diagnóstico del bug crítico de ChromaDB

> *"El bot arranca sin errores pero ante cualquier pregunta responde siempre 'No tengo información sobre ese tema', incluso para preguntas literales del documento. Los logs muestran que retrieve() devuelve []. Revisa indexer.py: ¿está configurado hnsw:space=cosine en la colección de ChromaDB? ¿Los scores de similarity_search_with_relevance_scores son positivos?"*

**Por qué así:** Fue el bug más crítico del proyecto — sin `hnsw:space=cosine`, ChromaDB usa distancia L2 y los scores son negativos, lo que hace que el filtro por `SIMILARITY_THRESHOLD` descarte todos los chunks. El prompt va directo a la causa raíz con preguntas verificables: si los scores son negativos, el espacio de similitud está mal configurado.

### Prompt 4 — Eliminación de fuentes duplicadas entre LLM y handler

> *"El bot muestra las fuentes dos veces: el LLM las cita dentro del texto porque el system prompt se lo pide, y handlers.py las añade al pie del mensaje. Elimina la instrucción de citar fuentes de system_prompt.md y deja que solo el handler las añada en HTML."*

**Por qué así:** Identificar una responsabilidad duplicada entre el prompt de sistema y el código requiere ver ambos artefactos a la vez. La solución con una sola instrucción coordinó cambios en dos archivos distintos (`system_prompt.md` y `handlers.py`) sin ambigüedad sobre cuál debía ceder.

### Prompt 5 — Bug report por comportamiento observable (reindexación)

> *"Cuando saco archivos del knowledge_base y uso reindex funciona correctamente porque los saca y no salen en fuentes, pero cuando los vuelvo a agregar a la carpeta y uso reindex no los toma."*

**Por qué así:** El prompt describe el síntoma exacto observado, no una hipótesis sobre el código. Claude Code trazó la causa raíz hasta `index_state.json`: al eliminar un archivo, los chunks se purgaban de ChromaDB pero la entrada del estado no se limpiaba; al re-agregar el mismo archivo, el MD5 coincidía y no se detectaba como nuevo. La corrección requirió dos cambios coordinados en `pipeline.py`.

### Prompt 6 — Diagnóstico de bugs por log de error y comportamiento del contenedor

> *[Logs de Docker con `PermissionError: [Errno 13] Permission denied: '/home/botuser/.cache/huggingface/hub'`]*
>
> *"Funcionó el contenedor pero no se escribieron las preguntas no respondidas en: unanswered_questions.csv"*

**Por qué así:** Dos bugs distintos reportados por observación directa del sistema corriendo, no por revisión de código. El primero se diagnosticó moviendo `HF_HOME` a `/app/.cache/huggingface` para que quedara bajo el `chown -R` del Dockerfile. El segundo llevó a descubrir que la condición `not chunks` era insuficiente: el retriever devolvía chunks sobre el umbral para preguntas fuera de alcance, y el LLM declaraba no tener información — pero el log y las fuentes no lo capturaban. Se añadió `_answer_has_no_info()` y se cambió la condición a `not sources`.

---

## 5. Sugerencias que rechacé o corregí

Esta sección es la más relevante para demostrar criterio sobre lo generado.

**Rechazo 1 — langchain-huggingface como dependencia principal**  
Claude Code propuso inicialmente `langchain-huggingface` y `langchain-chroma` como las dependencias para embeddings y vector store. Esto creó un conflicto de versiones: `langchain-huggingface` actualiza automáticamente `langchain-core` a 1.x, rompiendo `langchain 0.3.x`. Se rechazó y se migró a `langchain-community`, que es compatible con `langchain-core 0.3.x`.

**Rechazo 2 — pip install en el Python del sistema**  
Durante la generación de PDFs ficticios, Claude Code intentó ejecutar `pip install fpdf2` sobre el Python del sistema en lugar del entorno virtual del proyecto. Se rechazó; se estableció la regla de usar siempre `.venv/Scripts/pip` para cualquier instalación durante todo el proyecto.

**Rechazo 3 — Commits directamente en master**  
Claude Code hizo el primer commit de código directamente en la rama `master`. Se rechazó y se estableció el flujo Gitflow: `master` solo recibe merges `--no-ff` desde `develop`, todo el desarrollo ocurre en `feature/*`.

**Rechazo 4 — parse_mode="Markdown" para mensajes con nombres de archivo**  
La propuesta inicial formateaba todos los mensajes del bot con `parse_mode="Markdown"`. En la prueba real, los nombres de archivo con guiones bajos (`manual_soporte_ti.pdf`) provocaron errores de Telegram ("Can't parse entities") porque los guiones bajos se interpretan como marcadores de itálica. Se rechazó y se migró a `parse_mode="HTML"` con un helper `_md_to_html()` que convierte `**negrita**` a `<b>negrita</b>` y escapa caracteres HTML antes de enviar.

**Rechazo 5 — Validador de IDs sin manejo del tipo int**  
El validador `_parse_int_list` original solo manejaba `str` y `list`. Durante la prueba real se descubrió que Pydantic Settings v2 pre-parsea los valores del `.env` como JSON antes de invocar los validadores: un ID único como `9193063212` llega como `int`, no como `str`. El validador retornaba `[]` y nadie tenía acceso. Se rechazó la implementación original y se añadió el caso `isinstance(v, int): return [v]`.

**Rechazo 6 — Usuario root en el contenedor Docker con HF_HOME en /home**  
Claude Code generó el Dockerfile con `HF_HOME=/home/botuser/.cache/huggingface`. Al levantar el contenedor, el volumen nombrado `hf_cache` se montaba sobre ese directorio y era creado por Docker como root, impidiendo que `botuser` escribiera en él (`PermissionError: [Errno 13] Permission denied`). Se corrigió moviendo `HF_HOME` a `/app/.cache/huggingface` y creando ese directorio dentro del `chown -R botuser:botuser /app` del Dockerfile, de modo que el volumen se monta sobre una ruta que ya pertenece al usuario correcto.

**Rechazo 7 — Condición `not chunks` para registrar preguntas sin respuesta**  
La implementación original de `handlers.py` solo registraba en `unanswered_questions.csv` cuando el retriever no devolvía ningún chunk (`not chunks`). Esto dejaba sin registrar el caso en que sí se recuperaban chunks pero el LLM detectaba que no respondían la pregunta. Verificado en prueba real: preguntas fuera de alcance como "¿Qué clima hace hoy en Bogotá?" no se registraban y además mostraban fuentes junto al mensaje "No tengo información". Se corrigió añadiendo `_answer_has_no_info()` en `chain.py` (retorna `sources=[]` cuando el LLM declara no tener información) y cambiando la condición de log a `not sources` en `handlers.py`.

**Rechazo 8 — `index_state.json` no se limpiaba al eliminar archivos**  
Al eliminar un archivo de `knowledge_base/` y ejecutar `/reindex`, `_delete_by_sources()` purgaba correctamente los chunks de ChromaDB pero no eliminaba la entrada correspondiente en `index_state.json`. Si el archivo se volvía a agregar con el mismo contenido, el MD5 coincidía con el estado guardado y `_select_files()` no lo marcaba como nuevo — el archivo quedaba sin indexar silenciosamente. Se corrigió con `_remove_deleted_from_state()` que limpia el estado al purgar, y añadiendo un cross-check contra ChromaDB en `_select_files()` para auto-sanar desincronizaciones previas.

---

## 6. Qué verifiqué manualmente y cómo

| Aspecto | Método de verificación |
|---|---|
| **Generación de PDFs** | Abrir los archivos PDF en el visor del sistema para verificar que el texto era legible y el formato correcto |
| **Lazy imports** | Verificar que `python -m pytest tests/ -v` corre sin instalar sentence-transformers |
| **Tests pasan** | `pytest tests/ -v` con las dependencias de producción instaladas |
| **Patrón Gitflow** | `git log --oneline --graph` para verificar la historia de ramas |
| **Credenciales fuera del repositorio** | `git log --all --full-history -- .env` para confirmar que el archivo nunca fue commitado |
| **Prueba real del bot en Telegram** | Se probaron los 5 comandos y preguntas de la evaluación con el bot corriendo en modo polling; se diagnosticaron y corrigieron bugs (acceso bloqueado, Markdown con guiones bajos, fuentes mostradas sin información, preguntas no registradas en CSV) antes del merge a master |
| **Contenedor Docker funcional** | `docker compose up --build` y prueba del bot desde Telegram con el contenedor corriendo; se verificaron permisos del volumen `hf_cache` y visibilidad de `unanswered_questions.csv` en el host |
| **Registro de preguntas sin respuesta** | Preguntas fuera de alcance enviadas al bot con el contenedor levantado; se inspeccionó `unanswered_questions.csv` directamente en el host para confirmar que se escribían las entradas correctamente |
| **Reindexación tras eliminar y re-agregar archivos** | Se retiraron archivos de `knowledge_base/`, se ejecutó `/reindex` y se verificó que desaparecieron de `/fuentes`; luego se re-agregaron, se ejecutó `/reindex` y se confirmó que volvieron a aparecer |

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
