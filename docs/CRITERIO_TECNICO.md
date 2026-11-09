# Criterio técnico

---

## 1. ¿Qué fue lo más difícil de la solución y cómo lo resolviste?

Lo más difícil no fue el código sino entender el problema completo y aplicar correctamente la metodología exigida: **Spec Driven Development (SDD)**.

El documento de la prueba requería que las especificaciones existieran y estuvieran commiteadas *antes* de escribir cualquier línea de código. Eso implicó varios retos en cadena: leer e interpretar todos los requisitos funcionales y no funcionales, traducirlos a historias de usuario con criterios de aceptación verificables, definir cada tarea vinculada a su requisito (T-00..T-38 → RF-01..RF-10) y estructurar el orden de implementación para que los deseables no bloquearan los obligatorios.

El patrón era estricto: un solo commit con specs y código mezclados invalida la entrega. Eso obligó a pensar primero, implementar después, y registrar cada decisión de arquitectura en el momento en que se tomaba, no al final como suele hacerse.

Lo resolví apoyándome en Claude Code: primero en modo chat para entender y desglosar los requisitos del documento, luego en modo CLI para ejecutar cada fase. La clave fue ir punto por punto — entender qué pedía cada RF, definir un criterio de aceptación concreto y verificable, y solo entonces asignar una tarea con estado y referencia al requisito correspondiente.

---

## 2. ¿Qué decisión tomarías distinto si empezaras de nuevo?

**La decisión que tomaría distinta es documentarme mejor sobre la metodología SDD antes de empezar, y construir una herramienta especializada para ejecutarla.**

Durante el proyecto aprendí SDD sobre la marcha, lo que implicó ajustes y correcciones al avance. Con más tiempo, habría creado una **skill o agente dedicado a SDD** en Claude Code: una herramienta a la que se le entrega la lista de requisitos funcionales y no funcionales del proyecto, y que guía cada etapa de forma estructurada — análisis, especificación, desglose en tareas, implementación y documentación — retroalimentándose con el avance real del proyecto.

Este agente iría más allá de la estructura básica. Según el lenguaje y las tecnologías elegidas, incluiría etapas adicionales como: cobertura mínima de código por módulo, revisión de identificación (naming conventions, type hints, docstrings), análisis estático con el linter configurado, y validación de que cada tarea commiteada cierra efectivamente el criterio de aceptación que decía cerrar.

La idea es que el agente no solo genere la documentación inicial sino que la mantenga viva: cuando se detecta un ajuste o una corrección durante la implementación, actualiza automáticamente la tarea y registra el motivo, manteniendo la trazabilidad entre requisito, tarea, commit y prueba sin depender de que el desarrollador lo haga manualmente al final.

---

## 3. ¿Qué cambiarías para llevar esto a producción con miles de documentos y cientos de usuarios concurrentes?

| Área | Cambio necesario | Motivo |
|---|---|---|
| **Embeddings** | Servidor de embeddings dedicado (Triton, TorchServe) o migrar a OpenAI `text-embedding-3-small` | El modelo HuggingFace local carga en un único proceso; no se puede escalar horizontalmente |
| **Vector store** | ChromaDB PersistentClient con servidor HTTP, o migrar a Qdrant/Weaviate | ChromaDB 0.x tiene un único proceso por directorio |
| **Historial** | Redis con TTL por sesión (ej. 24 h) | La memoria se pierde al reiniciar y no se puede escalar a múltiples réplicas |
| **Rate limiting** | Redis (atómico y compartido entre réplicas) | El sliding window en memoria no es compartido entre instancias del bot |
| **Ingesta** | Pipeline asíncrono independiente (Celery/worker) | Separar la ingesta del bot evita que un reindexado lento bloquee las respuestas |
| **Despliegue** | Docker Compose con réplicas del bot + 1 servidor de embeddings + Redis + ChromaDB | Resiliencia y escalabilidad horizontal |
| **Observabilidad** | Tracing de trazas completas (LangSmith o Langfuse), métricas en Prometheus | Para diagnosticar latencias y detectar regresiones en calidad de respuesta |
| **Seguridad** | Webhook (en lugar de polling) + HTTPS + validación de firma de Telegram | Polling no es adecuado para producción; webhook con firma evita peticiones falsas |
| **Calidad del RAG** | Re-ranking (CrossEncoder) después del retrieval inicial | Mejora la precisión cuando el índice es grande y los embeddings no capturan fineza semántica |
| **Control de acceso** | Base de datos de usuarios con roles y panel de administración | La lista blanca en `.env` no escala; agregar o revocar usuarios requiere reiniciar el bot |
| **Calidad de documentos** | Pipeline de validación antes de indexar: detectar PDFs escaneados sin OCR, duplicados y archivos corruptos | Con miles de documentos, un archivo mal indexado contamina los resultados de retrieval |
| **Infraestructura en la nube** | Migrar a servicios administrados: Cloud Storage o S3 para `knowledge_base/`, Vertex AI o OpenSearch para el vector store, Cloud Run o ECS para el bot | Elimina la gestión de servidores, habilita autoescalado y garantiza disponibilidad sin intervención manual |
| **CI/CD** | Pipeline automatizado (GitHub Actions o Cloud Build): lint → tests → build de imagen Docker → deploy al entorno correspondiente según la rama | Garantiza que ningún cambio llega a producción sin pasar por las pruebas y el proceso de revisión |

---

## 4. ¿Cuáles son los principales riesgos y cómo los mitigarías?

| Riesgo | Mitigación actual | Mitigación en producción |
|---|---|---|
| **Prompt injection** | 7 patrones regex con log de auditoría + regla explícita en el system prompt | Añadir un modelo clasificador de intención previo al retrieval |
| **Credenciales en git** | `.gitignore` excluye `.env`; verificado con `git log --all --full-history -- .env` | Secret scanning automatizado en el pipeline de CI |
| **Privacidad de documentos** | ChromaDB persiste en disco sin cifrado; acceso restringido al directorio `chroma_db/` | Cifrado en reposo del volumen + control de acceso por rol al vector store |
| **User IDs en logs** | HMAC-SHA256 anonimiza el `user_id` en todos los eventos del log | Mantener el mismo mecanismo; auditoría periódica de los logs |
| **Costos de API** | `RATE_LIMIT_PER_MINUTE` limita mensajes por usuario | Alertas de gasto en el proveedor de LLM + presupuesto mensual máximo |
| **Calidad de embeddings** | `SIMILARITY_THRESHOLD` configurable; documentos de glosario en `knowledge_base/` | Re-ranking con CrossEncoder; fine-tuning del modelo con jerga interna |
| **Chunks sin contexto** | `CHUNK_SIZE` y `CHUNK_OVERLAP` configurables en `.env` | Ajuste por tipo de documento tras análisis de las preguntas sin respuesta |
| **Disponibilidad** | — | Supervisión del proceso con reinicio automático (systemd/Docker restart policy) + alerta ante caída |
| **Obsolescencia de documentos** | — | Versionado de documentos con fecha de vigencia en los metadatos; alerta cuando un documento supera N días sin revisión |

---

## 5. ¿Cuánto cuesta aproximadamente cada consulta con la configuración por defecto?

Configuración por defecto: `gpt-4o-mini`, `RETRIEVAL_TOP_K=4`, `HISTORY_LENGTH=10`.

**Componentes del prompt:**

| Componente | Tokens estimados |
|---|---|
| System prompt (`system_prompt.md`) | ~300 |
| Historial (hasta 10 turnos × ~80 tokens avg.) | ~800 |
| 4 chunks de contexto (800 chars × 4 × 0.3 tok/char) | ~960 |
| Pregunta del usuario | ~30 |
| **Total input** | **~2.090 tokens** |

**Output:**

| Componente | Tokens estimados |
|---|---|
| Respuesta del LLM | ~200 |

**Precio GPT-4o-mini** (según tarifa vigente al momento de la entrega): $0.15 / 1M tokens input + $0.60 / 1M tokens output.

```
Costo por consulta = (2.090 × 0.15 / 1.000.000) + (200 × 0.60 / 1.000.000)
                   = $0.000314 + $0.000120
                   ≈ $0.00043 por consulta  (~$0.43 por cada 1.000 consultas)
```

**Proyección mensual** con 100 usuarios activos × 10 preguntas/día × 22 días hábiles:
- 22.000 consultas/mes × $0.00043 ≈ **$9.50 / mes** (muy bajo).

> *Nota:* los embeddings son locales, sin costo adicional. El costo del servidor (RAM, CPU para los embeddings) no está incluido.

---

## 6. ¿Qué dejaste por fuera de manera consciente y por qué?

| Elemento | Motivo de exclusión |
|---|---|
| **Webhook** (en lugar de polling) | Polling es suficiente para una demo/prueba técnica. Webhook requiere un servidor HTTPS público, lo que agrega complejidad de despliegue que no aporta al criterio evaluado. |
| **Persistencia del historial** | La memoria es suficiente para la prueba. Redis agrega una dependencia de infraestructura que complicaría el setup del evaluador. |
| **Re-ranking de chunks** (CrossEncoder) | Mejora la calidad en índices grandes, pero agrega latencia y complejidad. Para 5 documentos ficticios no es necesario; se menciona como mejora para producción. |
| **Interfaz de administración web** | El control de acceso se hace por `ALLOWED_USER_IDS` en `.env`. Una UI web para gestionar usuarios agrega semanas de desarrollo sin impactar los requisitos evaluados. |
| **Multi-idioma del bot** | El sistema responde en el idioma del sistema prompt (español). Agregar detección de idioma y respuestas en inglés o portugués agrega complejidad sin ser un requisito. |
| **Tests de integración end-to-end** | Requieren un token real de Telegram y una API key activa, lo que los hace inadecuados para un repositorio público. Los tests unitarios con mocks cubren la lógica central de forma suficiente. |

---

## 7. ¿Cómo mediría la organización si el asistente está generando valor?

**Métricas operacionales** (sin infraestructura adicional):
- **Adopción**: usuarios activos por semana. Si nadie usa el bot, todas las demás métricas son irrelevantes. Medible con los logs existentes contando `user_id_hash` únicos por período.
- **Tasa de respuesta fundamentada**: porcentaje de consultas respondidas con fragmentos recuperados vs. mensaje de "no tengo información". Un aumento en "no tengo información" indica que faltan documentos en la base de conocimiento.
- **Volumen de preguntas sin respuesta** (`unanswered_questions.csv`): qué temas no están cubiertos en `knowledge_base/`. Alimenta directamente la priorización de nuevos documentos.

**Métricas de impacto** (requieren integración con el sistema de tickets):
- **Reducción de tickets repetitivos** al help desk en los 3 meses siguientes al despliegue. Si las preguntas sobre vacaciones o reembolsos bajan un 30%, el asistente está absorbiendo carga.
- **Tiempo de respuesta** al colaborador: de horas (ticket) a segundos (bot). Medible comparando tiempos antes y después.

**Métricas de calidad** (requieren encuesta en el bot):
- **NPS o thumbs up/down** por respuesta: añadir dos botones inline en cada respuesta y registrar el feedback en CSV.
- **Tasa de seguimiento**: si el usuario hace una pregunta de seguimiento inmediatamente después, la primera respuesta probablemente fue incompleta o poco clara.

**Revisión periódica** (trimestral):
- El administrador de mesa de ayuda muestrea 20 conversaciones aleatorias del mes y evalúa si las respuestas son correctas, completas y citan la fuente adecuada. Los hallazgos se traducen en dos acciones concretas: actualizar o agregar documentos en `knowledge_base/` para cubrir las brechas detectadas, y ajustar `SIMILARITY_THRESHOLD` o `CHUNK_SIZE` si hay patrones de respuestas incorrectas por retrieval deficiente.
