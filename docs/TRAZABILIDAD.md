# Matriz de trazabilidad de requisitos

**Proyecto:** Asistente de Mesa de Ayuda con RAG en Telegram  
**Fecha:** 2026-11-08  
**Rama:** develop → master

---

## Requisitos funcionales

| Requisito | Criterios de aceptación (spec.md) | Tarea(s) | Commit(s) | Prueba(s) | Estado |
|---|---|---|---|---|---|
| **RF-01** Ingesta de documentos | AC-01.1 (.md/.txt/.pdf indexados) · AC-01.2 (UTF-8 con tildes) · AC-01.3 (error aislado) · AC-01.4 (resumen al admin) | T-07, T-10, T-30 | `861b1e7` `874ce2f` | EVALUACION.md P01–P07 (chunks recuperados en todos los formatos) | ✅ |
| **RF-02** Indexación persistente | AC-02.1 (carga del disco sin reindexar) · AC-02.2 (VECTOR_STORE_PATH configurable) · AC-02.3 (metadatos: source, page, chunk_index) | T-09 | `861b1e7` | EVALUACION.md (scores y metadatos presentes en todos los resultados) | ✅ |
| **RF-03** Respuesta fundamentada con fuente | AC-03.1 (fuente en cada respuesta) · AC-03.2 (pág. N en PDFs) · AC-03.3 (sin información ajena al contexto) · AC-03.4 (máx. RETRIEVAL_TOP_K fragmentos) | T-11, T-13, T-15 | `75c5799` `afd268b` `eb70ab2` `c13d7db` | `tests/test_retriever.py::TestRetrieverThreshold::test_chunks_above_threshold_returned` · `test_top_k_passed_to_store` · EVALUACION.md P01–P07 | ✅ |
| **RF-04** Manejo de lo desconocido | AC-04.1 (threshold filtra chunks irrelevantes) · AC-04.2 (mensaje sin fuentes inventadas) · AC-04.3 (system prompt instruye no inventar) · AC-04.4 (log de pregunta sin respuesta) | T-14, T-15, T-29 | `afd268b` `eb70ab2` | `tests/test_retriever.py::TestRetrieverThreshold::test_chunks_below_threshold_filtered` · `test_mixed_scores_filtered_correctly` · EVALUACION.md P10–P12 | ✅ |
| **RF-05** Contexto conversacional | AC-05.1 (seguimiento coherente) · AC-05.2 (HISTORY_LENGTH configurable) · AC-05.3 (historiales independientes por usuario) · AC-05.4 (no persiste entre reinicios) · AC-05.5 (/reset borra historial) | T-17, T-18 | `eb70ab2` | EVALUACION.md P08 (seguimiento de P04) · P09 (seguimiento de P01) | ✅ |
| **RF-06** Comandos | AC-06.1 (respuesta < 5 s) · AC-06.2 (/fuentes indica si no hay docs) · AC-06.3 (acceso verificado antes del comando) | T-16, T-15 | `eb70ab2` `c13d7db` | Prueba manual: /start, /help, /reset, /fuentes, /reindex verificados con bot en Telegram | ✅ |
| **RF-07** Control de acceso + rate limit | AC-07.1 (usuario no listado → denegado) · AC-07.2 (check antes del procesamiento) · AC-07.3 (mensaje neutro) · AC-07.4 (lista vacía → nadie accede) · AC-07.5 (admin usa /reindex) | T-19, T-20 | `eb70ab2` `c13d7db` | `tests/test_access.py::TestAccessControl::test_allowed_user_has_access` · `test_unknown_user_denied` · `test_admin_has_implicit_access` · `test_empty_allowed_denies_everyone` · `TestRateLimiter::test_exceeding_limit_denied` · `test_window_resets_after_time` (6 tests) | ✅ |
| **RF-08** Reindexación (deseable) | AC-08.1 (solo admin ejecuta /reindex) · AC-08.2 (resumen N docs / M fallos) · AC-08.3 (índice actualizado) | T-27 | `eb70ab2` | EVALUACION.md §"Prueba de reindexación dinámica" pasos 3–5 | ✅ |
| **RF-09** Indexación incremental (deseable) | AC-09.1 (archivo sin cambios no se reprocesa) · AC-09.2 (hash MD5 + timestamp en index_state.json) · AC-09.3 (archivo modificado: borrar e reinsertar) | T-28 | `861b1e7` | EVALUACION.md §"Prueba de reindexación dinámica" paso 6 (segundo /reindex no reprocesa) | ✅ |
| **RF-10** Log preguntas sin respuesta (deseable) | AC-10.1 (timestamp ISO-8601, hash user_id, pregunta) · AC-10.2 (ruta configurable UNANSWERED_LOG_PATH) · AC-10.3 (archivo no en git) | T-29 | `eb70ab2` | Prueba manual: se generó `unanswered_questions.csv` al hacer preguntas fuera de alcance durante la evaluación | ✅ |

---

## Requisitos no funcionales con evidencia

| Requisito | Criterios clave (spec.md §4) | Tarea(s) | Commit(s) | Prueba(s) | Estado |
|---|---|---|---|---|---|
| **NF-01** Parametrización | 20 variables en `.env`; sin valores quemados en código; fallo rápido si falta variable requerida | T-04, T-05 | `9249100` | `tests/test_config.py::TestSettingsDefaults::test_defaults_applied` · `test_required_missing_telegram_token` · `test_required_missing_llm_api_key` · `TestIntListParsing` (4 tests) · `TestValidators` (5 tests) — 13 tests en total | ✅ |
| **NF-02** Ejecución | ≤ 4 comandos tras configurar `.env`; `.env.example` comentado; Docker deseable | T-03, T-05, T-31 | `5e446cc` `9249100` | README.md §Instalación rápida (3 comandos verificados manualmente) | ⚠️ T-31 (Dockerfile) pendiente — deseable según spec; documentado en DECISIONES.md D-08 |
| **NF-03** Seguridad | Credenciales fuera de git; mitigación de prompt injection; logs sin IDs en texto plano | T-06, T-19, T-21 | `937c54c` `eb70ab2` | `tests/test_access.py` (control de acceso) · `git log --all --full-history -- .env` confirma que `.env` nunca fue commiteado | ✅ |
| **NF-04** Calidad | Tests automatizados; type hints; ruff; logs JSON; docstrings | T-06, T-22, T-23, T-24, T-25 | `937c54c` `43553b0` | 40 tests en 4 archivos — todos pasan (`pytest tests/ -v`: 40 passed, 0.23 s) | ✅ |

---

## Verificación

### Resultado de pytest

```
$ pytest tests/ -v
========================= test session starts ==========================
collected 40 items

tests/test_access.py::TestAccessControl::test_allowed_user_has_access  PASSED
tests/test_access.py::TestAccessControl::test_unknown_user_denied       PASSED
tests/test_access.py::TestAccessControl::test_admin_has_implicit_access PASSED
tests/test_access.py::TestAccessControl::test_admin_flag                PASSED
tests/test_access.py::TestAccessControl::test_empty_allowed_denies_everyone PASSED
tests/test_access.py::TestAccessControl::test_admin_not_in_allowed_still_has_access PASSED
tests/test_access.py::TestRateLimiter::test_first_messages_allowed      PASSED
tests/test_access.py::TestRateLimiter::test_exceeding_limit_denied      PASSED
tests/test_access.py::TestRateLimiter::test_different_users_independent PASSED
tests/test_access.py::TestRateLimiter::test_window_resets_after_time    PASSED
tests/test_chunker.py::TestDocumentChunker::test_long_text_produces_multiple_chunks PASSED
tests/test_chunker.py::TestDocumentChunker::test_no_chunk_exceeds_configured_size  PASSED
tests/test_chunker.py::TestDocumentChunker::test_short_text_stays_as_single_chunk  PASSED
tests/test_chunker.py::TestDocumentChunker::test_source_metadata_preserved         PASSED
tests/test_chunker.py::TestDocumentChunker::test_page_metadata_preserved           PASSED
tests/test_chunker.py::TestDocumentChunker::test_chunk_index_added                 PASSED
tests/test_chunker.py::TestDocumentChunker::test_chunk_index_independent_per_source PASSED
tests/test_chunker.py::TestDocumentChunker::test_empty_list_returns_empty          PASSED
tests/test_chunker.py::TestDocumentChunker::test_empty_document_content            PASSED
tests/test_config.py::TestSettingsDefaults::test_defaults_applied                  PASSED
tests/test_config.py::TestSettingsDefaults::test_required_missing_telegram_token   PASSED
tests/test_config.py::TestSettingsDefaults::test_required_missing_llm_api_key      PASSED
tests/test_config.py::TestIntListParsing::test_comma_separated_string              PASSED
tests/test_config.py::TestIntListParsing::test_single_id                           PASSED
tests/test_config.py::TestIntListParsing::test_empty_string_gives_empty_list       PASSED
tests/test_config.py::TestIntListParsing::test_list_passthrough                    PASSED
tests/test_config.py::TestValidators::test_invalid_llm_provider                    PASSED
tests/test_config.py::TestValidators::test_valid_providers                         PASSED
tests/test_config.py::TestValidators::test_log_level_normalized_to_upper           PASSED
tests/test_config.py::TestValidators::test_invalid_log_level                       PASSED
tests/test_config.py::TestValidators::test_chunk_overlap_must_be_less_than_chunk_size PASSED
tests/test_config.py::TestValidators::test_valid_chunk_overlap                     PASSED
tests/test_retriever.py::TestRetrievedChunkFormatting::test_format_source_with_page PASSED
tests/test_retriever.py::TestRetrievedChunkFormatting::test_format_source_without_page PASSED
tests/test_retriever.py::TestRetrievedChunkFormatting::test_content_property       PASSED
tests/test_retriever.py::TestRetrieverThreshold::test_chunks_above_threshold_returned PASSED
tests/test_retriever.py::TestRetrieverThreshold::test_chunks_below_threshold_filtered PASSED
tests/test_retriever.py::TestRetrieverThreshold::test_mixed_scores_filtered_correctly PASSED
tests/test_retriever.py::TestRetrieverThreshold::test_empty_index_returns_empty_list  PASSED
tests/test_retriever.py::TestRetrieverThreshold::test_top_k_passed_to_store           PASSED

========================== 40 passed in 0.23s ==========================
```

### Huecos detectados

| Tipo de hueco | Detalle |
|---|---|
| **Requisito sin prueba automatizada** | RF-02 (indexación persistente): no hay test unitario del indexer; la evidencia es la evaluación manual con retrieval real. Causa: las dependencias de ChromaDB y sentence-transformers hacen los tests lentos y dependientes de GPU/descarga; se optó por lazy imports y evaluación funcional en su lugar (documentado en D-04). |
| **Requisito sin prueba automatizada** | RF-05 (historial): no hay test unitario de `ConversationHistory`; la evidencia son P08 y P09 de la evaluación. |
| **Requisito sin prueba automatizada** | RF-08 y RF-09 (reindex, incremental): las pruebas son manuales con el bot corriendo (docs/EVALUACION.md §Reindexación dinámica). |
| **Requisito sin prueba automatizada** | RF-10 (log CSV): verificación manual al revisar `unanswered_questions.csv` durante la evaluación. |
| **Tarea sin commit propio** | T-12 (`prompts/system_prompt.md`), T-13 (`chain.py`), T-14 (RF-04 en chain) y T-30 (.docx): sus commits están agrupados en merges de feature; no tienen commit de tarea individual etiquetado. |
| **Requisito parcial** | NF-02 (Docker): T-31 marcado como Pendiente. Es un deseable según spec.md §NF-02; el bot corre correctamente sin Docker (`python -m src.main`). |
| **Sin hueco** | Todos los 10 RF tienen al menos un commit real y evidencia (automatizada o manual). Los 4 NF tienen commits y evidencia. Ningún commit con `[T-XX]` queda sin tarea asociada en tasks.md. |
