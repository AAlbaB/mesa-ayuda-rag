# Tareas de implementación — Asistente de Mesa de Ayuda con RAG en Telegram

**Versión:** 1.0  
**Fecha:** 2026-11-06  
**Referencia:** specs/spec.md · specs/plan.md

**Estados:** `Pendiente` · `En progreso` · `Completada` · `Cancelada`

---

## Fase 1 — Especificación (SDD)

| ID | Descripción | Requisito(s) | Estado |
|---|---|---|---|
| T-00 | git init, .gitignore, primer commit | — | Completada |
| T-01 | Crear specs/spec.md, specs/plan.md, specs/tasks.md y commitear | SDD | Completada |

---

## Fase 2 — Estructura base y configuración

| ID | Descripción | Requisito(s) | Estado |
|---|---|---|---|
| T-02 | Estructura de carpetas del proyecto (`src/`, `tests/`, `prompts/`, `knowledge_base/`, `docs/`) | plan.md §8 | Completada |
| T-03 | `pyproject.toml`: dependencias, configuración de ruff, pytest | NF-04 | Completada |
| T-04 | `src/config.py`: Pydantic Settings con todas las variables de NF-01; falla rápido si falta variable requerida | NF-01 | Completada |
| T-05 | `.env.example` comentado con todas las variables | NF-01, NF-02 | Completada |
| T-06 | Logging estructurado (JSON) configurado en `src/logging_setup.py`; HMAC para anonimizar user_id | NF-04 | Completada |

---

## Fase 3 — Ingesta e indexación

| ID | Descripción | Requisito(s) | Estado |
|---|---|---|---|
| T-07 | `src/ingestion/loader.py`: carga .md, .txt, .pdf con metadatos (source, page) | RF-01 | Completada |
| T-08 | `src/ingestion/chunker.py`: RecursiveCharacterTextSplitter con CHUNK_SIZE/OVERLAP | RF-02 | Completada |
| T-09 | `src/ingestion/indexer.py`: ChromaDB persistente; métodos build_index, load_index, get_indexed_sources | RF-02 | Completada |
| T-10 | `src/ingestion/pipeline.py`: integración loader → chunker → indexer; modo incremental (RF-09) | RF-01, RF-02 | Completada |

---

## Fase 4 — Retrieval y respuesta

| ID | Descripción | Requisito(s) | Estado |
|---|---|---|---|
| T-11 | `src/retrieval/retriever.py`: búsqueda de similitud con filtro por SIMILARITY_THRESHOLD | RF-03, RF-04 | Completada |
| T-12 | `prompts/system_prompt.md`: prompt de sistema con reglas de fundamentación, citas y anti-inyección | NF-01, NF-03 | Completada |
| T-13 | `src/llm/chain.py`: cadena LangChain; selección de proveedor LLM por config; formateo de respuesta con fuentes | RF-03 | Completada |
| T-14 | Manejo de lo desconocido: mensaje preconfigurado cuando 0 chunks superan el umbral | RF-04 | Completada |

---

## Fase 5 — Bot de Telegram

| ID | Descripción | Requisito(s) | Estado |
|---|---|---|---|
| T-15 | `src/bot/handlers.py`: handler de mensaje de texto; integración con retrieval + LLM | RF-03, RF-04 | Completada |
| T-16 | Comandos /start, /help, /reset, /fuentes, /reindex (admin) | RF-06, RF-08 | Completada |
| T-17 | `src/bot/history.py`: ConversationHistory en memoria con deque y HISTORY_LENGTH | RF-05 | Completada |
| T-18 | Integración del historial en el flujo de consulta + `src/main.py` como punto de entrada | RF-05 | Completada |

---

## Fase 6 — Seguridad

| ID | Descripción | Requisito(s) | Estado |
|---|---|---|---|
| T-19 | `src/security/access.py`: AccessControl (ALLOWED_USER_IDS + ADMIN_USER_IDS); RateLimiter (sliding window en memoria) | RF-07, NF-01 | Completada |
| T-20 | Integración de access control y rate limit como middleware en todos los handlers | RF-07 | Completada |
| T-21 | `src/security/sanitizer.py`: truncado a 2000 chars; detección de 7 patrones de inyección con log de auditoría | NF-03 | Completada |

---

## Fase 7 — Pruebas

| ID | Descripción | Requisito(s) | Estado |
|---|---|---|---|
| T-22 | `tests/test_config.py`: 13 casos — defaults, vars requeridas, parseo CSV, validadores | NF-04 | Completada |
| T-23 | `tests/test_chunker.py`: 8 casos — tamaño, solapamiento, metadatos, edge cases | NF-04 | Completada |
| T-24 | `tests/test_retriever.py`: 8 casos — threshold, top-k, mixed scores, formato fuente | NF-04 | Completada |
| T-25 | `tests/test_access.py`: 8 casos — acceso, admin, rate limit, ventana temporal | NF-04 | Completada |

---

## Fase 8 — Documentos ficticios

| ID | Descripción | Requisito(s) | Estado |
|---|---|---|---|
| T-26 | 5 documentos: vacaciones.md, gastos.txt, trabajo_remoto.md, soporte_ti.pdf (2 págs.), bienvenida.pdf | Sección 8 | Completada |

---

## Fase 9 — Deseables (si el tiempo lo permite)

| ID | Descripción | Requisito(s) | Estado |
|---|---|---|---|
| T-27 | Comando /reindex restringido a admins; reprocesa knowledge_base/ | RF-08 | Completada |
| T-28 | Indexación incremental: hash MD5 en index_state.json; skip de archivos sin cambios; delete+reindex de modificados | RF-09 | Completada |
| T-29 | Log de preguntas sin respuesta en CSV (timestamp, hash user_id, pregunta) | RF-10 | Completada |
| T-30 | Soporte .docx: python-docx via langchain-community | RF-01 | Completada |
| T-31 | Dockerfile y docker-compose.yml | NF-02 | Pendiente |

---

## Fase 10 — Documentación final

| ID | Descripción | Requisito(s) | Estado |
|---|---|---|---|
| T-32 | README.md: descripción, prereqs, instalación, configuración, ejecución, uso, limitaciones | Sección 6.1 | Pendiente |
| T-33 | docs/ARQUITECTURA.md: diagrama Mermaid, flujos detallados, estructura de carpetas | Sección 6.2 | Pendiente |
| T-34 | docs/DECISIONES.md: 8 decisiones con contexto, opciones, decisión, justificación, trade-offs | Sección 6.3 | Pendiente |
| T-35 | docs/USO_IA.md: herramientas, prompts representativos, sugerencias rechazadas, verificación manual | Sección 6.4 | Pendiente |
| T-36 | docs/EVALUACION.md: ≥10 preguntas (≥3 fuera de alcance, ≥2 de seguimiento), resultados, ajustes | Sección 6.5 | Pendiente |
| T-37 | docs/CRITERIO_TECNICO.md: 7 preguntas respondidas | Sección 6.6 | Pendiente |

---

## Resumen de progreso

| Fase | Tareas | Completadas | % |
|---|---|---|---|
| Especificación | 2 | 2 | 100% |
| Estructura base | 5 | 5 | 100% |
| Ingesta/indexación | 4 | 4 | 100% |
| Retrieval/respuesta | 4 | 4 | 100% |
| Bot Telegram | 4 | 4 | 100% |
| Seguridad | 3 | 3 | 100% |
| Pruebas | 4 | 4 | 100% |
| Docs ficticios | 1 | 1 | 100% |
| Deseables | 5 | 4 | 80% |
| Documentación final | 6 | 0 | 0% |
| **Total** | **38** | **31** | **82%** |
