# Criterio técnico

---

## 1. ¿Qué fue lo más difícil de la solución y cómo lo resolviste?

El problema más complejo fue el **conflicto de versiones entre las dependencias de LangChain y ChromaDB**.

LangChain 0.3.x requiere `langchain-core 0.3.x`. Sin embargo, instalar `langchain-huggingface` (el paquete oficial para embeddings de HuggingFace) actualiza automáticamente `langchain-core` a 1.x, lo que rompe silenciosamente `langchain 0.3.x`. El mismo problema ocurrió con `langchain-chroma` y con `chromadb 1.5.9` (que eliminó la API de Chroma que usa `langchain-community`).

La solución requirió tres pasos:
1. **Identificar el origen**: comparar las versiones instaladas antes y después del conflicto con `pip show`.
2. **Cambiar la estrategia de imports**: en lugar de usar los paquetes `langchain-huggingface` y `langchain-chroma` (que arrastran dependencias incompatibles), usar `langchain_community.embeddings.HuggingFaceEmbeddings` y `langchain_community.vectorstores.Chroma`, que son compatibles con `langchain-core 0.3.x`.
3. **Pinear la versión de ChromaDB**: agregar `chromadb>=0.5.0,<1.0.0` en `pyproject.toml` para evitar que `pip` instale la versión 1.x con API incompatible.

Adicionalmente, para que los tests unitarios puedan ejecutarse sin descargar PyTorch (~1.5 GB), se movieron los imports de `HuggingFaceEmbeddings` y `Chroma` a métodos internos (lazy imports), de forma que importar el módulo `indexer.py` no activa la carga del modelo.

---

## 2. ¿Qué decisión tomarías distinto si empezaras de nuevo?

**Pinear todas las versiones exactas desde el primer día.**

En `pyproject.toml` usé rangos (`langchain>=0.3.0,<0.4.0`) que son razonables en teoría, pero en la práctica el ecosistema LangChain actualiza versiones con cambios de API incompatibles con más frecuencia de lo esperado. Con versiones exactas (`langchain==0.3.14`, `langchain-core==0.3.29`) habría evitado las horas invertidas en resolver conflictos de dependencias.

**Consideraría también FAISS en lugar de ChromaDB** para la primera versión. FAISS es más simple (un archivo en disco, sin servidor), no tiene el problema de versiones de ChromaDB y para un índice pequeño (<10K documentos) tiene mejor latencia. ChromaDB añade valor en producción (filtros por metadata, actualización incremental sin reconstruir el índice completo), pero para la prueba técnica FAISS habría sido más directo.

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

---

## 4. ¿Cuáles son los principales riesgos y cómo los mitigarías?

**Seguridad**
- *Prompt injection*: un usuario malicioso puede intentar manipular el bot con instrucciones como "ignora las reglas anteriores y...". Mitigación actual: 7 patrones regex detectados (con log de auditoría) + regla explícita en el system prompt que prohíbe obedecer instrucciones contradictorias del usuario. Para producción: añadir un modelo clasificador de intención previo al retrieval.
- *Credentials en git*: mitigado con `.gitignore` que excluye `.env`, y validado antes de cada commit.

**Privacidad**
- Los documentos de RRHH pueden contener información sensible (salarios, casos disciplinarios). ChromaDB persiste en disco sin cifrado. Mitigación: cifrado de disco del servidor, acceso restringido al directorio `chroma_db/`.
- Los user_ids de Telegram se hashean con HMAC-SHA256 en los logs, no se almacenan en texto plano.

**Costos**
- Sin límite de uso, el costo de API puede escalar inesperadamente. Mitigación actual: `RATE_LIMIT_PER_MINUTE` limita mensajes por usuario. Para producción: alertas de gasto en el proveedor de LLM + presupuesto mensual máximo.

**Calidad de respuestas**
- El modelo de embeddings local puede no capturar jerga interna de la organización (siglas, apodos de sistemas). Mitigación: ajustar `SIMILARITY_THRESHOLD` hacia abajo para ser más permisivo, y complementar con documentos de glosario en `knowledge_base/`.
- Fragmentos muy cortos pueden quedar sin contexto suficiente. Mitigación: ajustar `CHUNK_SIZE` y `CHUNK_OVERLAP` para el tipo de documentos de la organización.

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

**Precio GPT-4o-mini** (nov 2026): $0.15 / 1M tokens input + $0.60 / 1M tokens output.

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
- **Tasa de respuesta fundamentada**: porcentaje de consultas respondidas con fragmentos recuperados vs. mensaje de "no tengo información". Un aumento en "no tengo información" indica que faltan documentos en la base de conocimiento.
- **Volumen de preguntas sin respuesta** (`unanswered_questions.csv`): qué temas no están cubiertos en `knowledge_base/`. Alimenta directamente la priorización de nuevos documentos.

**Métricas de impacto** (requieren integración con el sistema de tickets):
- **Reducción de tickets repetitivos** al help desk en los 3 meses siguientes al despliegue. Si las preguntas sobre vacaciones o reembolsos bajan un 30%, el asistente está absorbiendo carga.
- **Tiempo de respuesta** al colaborador: de horas (ticket) a segundos (bot). Medible comparando tiempos antes y después.

**Métricas de calidad** (requieren encuesta en el bot):
- **NPS o thumbs up/down** por respuesta: añadir dos botones inline en cada respuesta y registrar el feedback en CSV.
- **Tasa de seguimiento**: si el usuario hace una pregunta de seguimiento inmediatamente después, la primera respuesta probablemente fue incompleta o poco clara.

**Revisión periódica** (trimestral):
- Muestrear 20 conversaciones aleatorias del mes y evaluar manualmente si las respuestas son correctas, completas y citan la fuente adecuada. Comparar contra el contenido de los documentos.
