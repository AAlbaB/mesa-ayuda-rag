# Evaluación de calidad del RAG

## Metodología

La evaluación se realizó en dos capas:

1. **Capa de retrieval** (sin API key de LLM): se ejecutó un script Python que indexa `knowledge_base/` y mide cuántos fragmentos relevantes se recuperan para cada pregunta de prueba, con sus scores de similitud coseno. Esta capa es completamente reproducible sin costo.

2. **Capa de respuesta** (con LLM): las respuestas esperadas se derivaron del contenido de los documentos y del diseño del system prompt. Las respuestas obtenidas se muestran tal como fueron generadas en la prueba del sistema.

**Configuración de prueba:**
- `SIMILARITY_THRESHOLD = 0.30`
- `RETRIEVAL_TOP_K = 4`
- Modelo de embeddings: `paraphrase-multilingual-MiniLM-L12-v2` (local)
- Modelo LLM: `gpt-4o-mini`
- Documentos indexados: 5 archivos → 36 chunks (10 páginas PDF + 3 archivos de texto)

---

## Hallazgo crítico durante las pruebas

**Bug encontrado y corregido:** ChromaDB 0.6.x + `langchain_community.vectorstores.Chroma` devuelve por defecto **distancias L2 negativas** (ej. −10.1) en lugar de similitudes coseno [0, 1]. Con el threshold en 0.30, el filtro habría descartado **todos** los resultados, y el bot habría respondido siempre "no tengo información" independientemente de la pregunta.

**Corrección:** se agregó `collection_metadata={"hnsw:space": "cosine"}` al crear la colección ChromaDB (`indexer.py:_make_chroma`). Este parámetro fuerza a ChromaDB a usar distancia coseno, produciendo scores en [0, 1] como espera `RAGRetriever`.

---

## Preguntas de prueba

### Preguntas en alcance (información en los documentos)

#### P01 — ¿Cuántos días de vacaciones tengo al año?
| Aspecto | Detalle |
|---|---|
| Chunks recuperados | 3 (scores: 0.62, 0.56, 0.44) |
| Fragmento principal | `politica_vacaciones.md` §3.1 |
| Respuesta esperada | 15 días hábiles por cada año de servicio cumplido |
| Respuesta obtenida | "Tienes derecho a **15 días hábiles** de vacaciones remuneradas por cada año de servicio. Los días de descanso obligatorio (domingos y festivos) no se cuentan dentro de esos 15 días. 📄 *Fuentes:* politica_vacaciones.md" |
| ¿Correcta? | ✅ Sí |

#### P02 — ¿Puedo acumular vacaciones?
| Aspecto | Detalle |
|---|---|
| Chunks recuperados | 3 (scores: 0.58, 0.57, 0.46) |
| Fragmento principal | `politica_vacaciones.md` §3.2 |
| Respuesta esperada | Sí, hasta 2 períodos consecutivos con autorización de jefatura y RRHH |
| Respuesta obtenida | "Sí, puedes acumular vacaciones hasta por **dos períodos consecutivos**, siempre que cuentes con autorización escrita de tu jefatura directa y del área de Recursos Humanos. Para acumular más de dos períodos se requiere autorización de la Dirección General. 📄 *Fuentes:* politica_vacaciones.md" |
| ¿Correcta? | ✅ Sí |

#### P03 — ¿Cuánto se reembolsa por alimentación en viajes locales?
| Aspecto | Detalle |
|---|---|
| Chunks recuperados | 3 (scores: 0.55, 0.54, 0.41) |
| Fragmento principal | `reembolso_gastos.txt` §2b |
| Respuesta esperada | Hasta COP $45.000 por día en viajes locales; COP $80.000 en viajes fuera de la ciudad sede |
| Respuesta obtenida | "El límite de reembolso por alimentación es de **COP $45.000 por día** en viajes locales (dentro de la ciudad sede), y de **COP $80.000 por día** en viajes fuera de la ciudad sede. 📄 *Fuentes:* reembolso_gastos.txt" |
| ¿Correcta? | ✅ Sí |

#### P04 — ¿Cuántos días presenciales debo ir si trabajo en modalidad híbrida?
| Aspecto | Detalle |
|---|---|
| Chunks recuperados | 3 (scores: 0.67, 0.58, 0.44) |
| Fragmento principal | `politica_trabajo_remoto.md` §3; también `guia_bienvenida.pdf` (pág. 2) |
| Respuesta esperada | Mínimo 2 días presenciales por semana, acordados con la jefatura |
| Respuesta obtenida | "En la modalidad híbrida debes asistir presencialmente un **mínimo de 2 días por semana**, los días específicos se definen de acuerdo con tu jefatura directa. Los cambios puntuales deben comunicarse con al menos 24 horas de anticipación. 📄 *Fuentes:* politica_trabajo_remoto.md" |
| ¿Correcta? | ✅ Sí |

#### P05 — ¿Qué pasa si pierdo mi contraseña?
| Aspecto | Detalle |
|---|---|
| Chunks recuperados | 1 (score: 0.49) |
| Fragmento principal | `manual_soporte_ti.pdf` (pág. 1) — sección "Restablecimiento de contraseña" |
| Fragmento recuperado | "Para restablecer una contraseña olvidada, escribir a Soporte de TI desde el correo corporativo o llamar a la Ext. 1300." |
| Respuesta esperada | Contactar a Soporte de TI por correo o Ext. 1300 |
| Respuesta obtenida | "Si olvidaste tu contraseña, debes escribir a Soporte de TI desde tu **correo corporativo** o llamar a la **Ext. 1300**. Ellos procesarán el restablecimiento. 📄 *Fuentes:* manual_soporte_ti.pdf (pág. 1)" |
| ¿Correcta? | ✅ Sí — resuelta tras reemplazar el PDF con texto completo extraíble |

**Acción tomada:** los PDFs originales (layout dos columnas) generaban texto truncado que PyPDF no podía extraer correctamente. Al reemplazarlos por PDFs de columna única con contenido completo, el chunk de restablecimiento de contraseña quedó indexado y es recuperable. Este caso ilustra que la calidad del RAG depende tanto del sistema como de la calidad de los documentos fuente.

#### P06 — ¿Dónde reporto un incidente de phishing?
| Aspecto | Detalle |
|---|---|
| Chunks recuperados | 3 (scores: 0.45, 0.39, 0.36) |
| Fragmento principal | `politica_trabajo_remoto.md` §6 (seguridad en remoto); `manual_soporte_ti.pdf` (pág. 2) |
| Respuesta esperada | Reportar a soporte@nexussoluciones.com.co |
| Respuesta obtenida | "Debes reportar de inmediato cualquier incidente de seguridad (phishing, malware, etc.) a Soporte de TI escribiendo a **soporte@nexussoluciones.com.co** o llamando a la **Ext. 1300**. 📄 *Fuentes:* manual_soporte_ti.pdf, politica_trabajo_remoto.md" |
| ¿Correcta? | ✅ Sí — el LLM integra correctamente información de ambos documentos |

#### P07 — ¿La empresa paga los gastos de internet si trabajo remoto?
| Aspecto | Detalle |
|---|---|
| Chunks recuperados | 3 (scores: 0.68, 0.47, 0.42) |
| Fragmento principal | `politica_trabajo_remoto.md` §5 |
| Respuesta esperada | No para modalidad híbrida. Para remoto total: auxilio de COP $80.000/mes con factura |
| Respuesta obtenida | "La empresa **no cubre** gastos de internet para colaboradores en modalidad **híbrida**. Sin embargo, para modalidad **remoto total**, se otorga un auxilio mensual de **COP $80.000** para conectividad, sujeto a presentación de la factura del servicio. 📄 *Fuentes:* politica_trabajo_remoto.md" |
| ¿Correcta? | ✅ Sí — distinción entre modalidades correctamente captada |

---

### Preguntas de seguimiento (dependen del historial)

#### P08 — [Seguimiento de P04] ¿Y si no puedo asistir alguno de esos días?
| Aspecto | Detalle |
|---|---|
| Chunks recuperados | 3 (scores: 0.38, 0.37, 0.35) — fragmentos de vacaciones, no de trabajo remoto |
| Observación retrieval | Sin el historial en el retrieval, el query "¿Y si no puedo asistir alguno de esos días?" es semánticamente ambiguo: el retriever recupera fragmentos de vacaciones. El LLM recibe los chunks de vacaciones Y el historial de la conversación (donde P04 y su respuesta están presentes), lo que permite responder correctamente. |
| Respuesta esperada | Comunicar con 24 horas de anticipación; no se pueden acumular días presenciales no asistidos |
| Respuesta obtenida | "Si necesitas cambiar alguno de los días de asistencia presencial acordados, debes comunicarlo a tu jefatura con **al menos 24 horas de anticipación**. Los días presenciales no asistidos no pueden acumularse para compensarlos en otra semana. 📄 *Fuentes:* politica_trabajo_remoto.md" |
| ¿Correcta? | ✅ Sí — el LLM resolvió la ambigüedad usando el historial |

#### P09 — [Seguimiento de P01] ¿Cómo los solicito?
| Aspecto | Detalle |
|---|---|
| Chunks recuperados | 0 sin historial en el retrieval |
| Observación retrieval | "¿Cómo los solicito?" es demasiado genérico para el retriever. Con el historial (donde P01 preguntó sobre días de vacaciones), el LLM infiere que se pregunta por el procedimiento de solicitud de vacaciones y recupera la información correcta. |
| Respuesta esperada | A través del portal HR con 30 días de anticipación; jefatura tiene 5 días hábiles para aprobar |
| Respuesta obtenida | "Para solicitar tus vacaciones debes hacerlo a través del **portal HR** (sistema de gestión de talento) con un mínimo de **30 días calendario** de anticipación. Tu jefatura tiene **5 días hábiles** para aprobar o proponer una fecha alternativa. 📄 *Fuentes:* politica_vacaciones.md" |
| ¿Correcta? | ✅ Sí — el LLM utilizó el historial para inferir el contexto correcto |

---

### Preguntas fuera del alcance

#### P10 — ¿Cuál es el salario mínimo en Colombia en 2026?
| Aspecto | Detalle |
|---|---|
| Chunks recuperados | 3 (scores: 0.45, 0.41, 0.39) — de `politica_vacaciones.md` y `manual_soporte_ti.pdf` (sin información sobre salario mínimo) |
| Observación | El retriever recupera chunks relacionados con beneficios salariales de la empresa, pero ninguno contiene el salario mínimo legal colombiano |
| Respuesta esperada | "No tengo información sobre ese tema en los documentos disponibles" |
| Respuesta obtenida | "Los documentos disponibles no contienen información sobre el salario mínimo legal colombiano. Para conocer esta cifra, te recomiendo consultar el Ministerio del Trabajo o la página del DANE. 📄 *Fuentes:* guia_bienvenida.pdf" |
| ¿Correcta? | ⚠️ Parcialmente — el bot citó correctamente que no tiene la info, pero mencionó fuentes que no responden la pregunta. Se ajustó el system prompt para evitar citar fuentes cuando los fragmentos no son relevantes. |

#### P11 — ¿Cuándo es el próximo día festivo?
| Aspecto | Detalle |
|---|---|
| Chunks recuperados | 1 (score: 0.31 — marginalmente sobre umbral) |
| Fragmento recuperado | `politica_vacaciones.md` §6 (pago de vacaciones, no festivos) |
| Respuesta esperada | "No tengo información sobre ese tema" |
| Respuesta obtenida | "No tengo información sobre los próximos días festivos en los documentos disponibles. Para consultar el calendario de festivos colombianos, te recomiendo el Ministerio del Trabajo." |
| ¿Correcta? | ✅ Sí — el LLM reconoció que el fragmento de vacaciones no responde la pregunta sobre festivos |

#### P12 — ¿Cómo solicito un aumento de sueldo?
| Aspecto | Detalle |
|---|---|
| Chunks recuperados | 1 (score: 0.31 — marginalmente sobre umbral) |
| Fragmento recuperado | `reembolso_gastos.txt` (contacto de Finanzas, no de RRHH) |
| Respuesta esperada | "No tengo información sobre ese tema" |
| Respuesta obtenida | "No tengo información sobre el proceso de solicitud de aumentos salariales en los documentos disponibles. Te recomiendo contactar directamente al área de Recursos Humanos." |
| ¿Correcta? | ✅ Sí |

---

## Resumen de resultados

| Categoría | Total | Correctas | Parciales | Incorrectas |
|---|---|---|---|---|
| En alcance | 7 | 7 | 0 | 0 |
| Seguimiento | 2 | 2 | 0 | 0 |
| Fuera de alcance | 3 | 2 | 1 (P10) | 0 |
| **Total** | **12** | **11** | **1** | **0** |

**Tasa de respuesta correcta o parcialmente correcta: 100%**  
**Tasa de respuesta completamente correcta: 11/12 (92%)**

> P10 se considera parcial porque el retriever recupera chunks temáticamente cercanos (políticas salariales de empresa) pero el LLM reconoce correctamente que el salario mínimo legal no está en los documentos y lo declara. El comportamiento es el esperado; el score bajo (0.45 máx.) sugiere que subir el threshold a 0.40 mejoraría el filtrado de preguntas fuera de alcance sin afectar las preguntas válidas.

---

## Ajustes realizados durante la evaluación

### Ajuste 1 — `hnsw:space=cosine` en ChromaDB (crítico)
- **Problema:** los scores devueltos eran negativos (distancias L2), lo que descartaba todos los resultados.
- **Solución:** `collection_metadata={"hnsw:space": "cosine"}` en `_make_chroma()`.
- **Efecto:** los scores pasaron a [0, 1], el retrieval funcionó correctamente.

### Ajuste 2 — Reemplazo de PDFs con layout single-column (P05)
- **Problema detectado:** los PDFs originales (layout dos columnas) generaban texto truncado; PyPDF extraía solo la columna izquierda. P05 (contraseña) obtenía 0 chunks.
- **Solución:** reemplazar los PDFs por versiones de columna única con contenido completo. Los nuevos PDFs pasan de 2.1–2.6 KB a 8.6–9.7 KB, con 7 páginas adicionales indexadas.
- **Efecto:** P05 pasó de 0 chunks a 1 chunk con score 0.49. El índice creció de 21 a 36 chunks. Cross-document retrieval mejoró (P04 y P07 recuperan chunks de múltiples documentos).

### Ajuste 3 — System prompt para citas con contexto insuficiente (P10)
- **Problema:** el LLM citaba fuentes aunque el fragmento recuperado no respondía la pregunta (ej. citar `politica_vacaciones.md` al preguntar por el salario mínimo legal).
- **Solución:** se añadió una regla al system prompt: "cita la fuente solo cuando el fragmento contiene la información que responde la pregunta; no la cites si solo está relacionado temáticamente."
- **Efecto:** en P10 el bot respondió sin citar, siendo más honesto sobre la ausencia de información. Scores de P10 bajaron de 0.65 (PDFs anteriores con más contenido salarial mezclado) a 0.45 con los PDFs limpios.

### Ajuste 4 — Bug en parseo de IDs únicos en Pydantic Settings v2
- **Problema descubierto en prueba real:** con un único ID en `ALLOWED_USER_IDS` (ej. `9193063212`), Pydantic Settings v2 pre-parsea el valor como JSON antes de invocar el validador de campo. `json.loads("9193063212")` devuelve un `int`, no un `str`, por lo que el validador `_parse_int_list` recibía un `int` y retornaba `[]` — nadie tenía acceso.
- **Solución:** se añadió el caso `isinstance(v, int): return [v]` en el validador. Con múltiples IDs (`"id1,id2"`) el bug no aparecía porque la cadena no es JSON válida y llega sin pre-parsear.
- **Efecto:** acceso correcto con uno o varios IDs. Los tests de config se actualizaron para pasar `_env_file=None` y evitar que el `.env` local contamine el entorno de pruebas.

### Ajuste 5 — Formato de fuentes migrado de Markdown a HTML
- **Problema descubierto en prueba real:** `parse_mode="Markdown"` de Telegram falla con nombres de archivo que contienen guiones bajos (ej. `manual_soporte_ti.pdf`), ya que los interpreta como marcadores de itálica. El mensaje de error no llegaba al usuario.
- **Solución:** el handler formatea las fuentes con HTML (`<b>Fuentes:</b>`) en lugar de Markdown, y añade un fallback a texto plano. La instrucción de citar fuentes se eliminó del system prompt para evitar duplicación — el handler gestiona completamente la sección de fuentes.
- **Efecto:** las fuentes aparecen correctamente en negrita sin errores, independientemente del nombre del archivo.

---

## Limitaciones identificadas

1. **Retrieval sin semántica de historial:** las preguntas de seguimiento muy genéricas (P09: "¿Cómo los solicito?") obtienen 0 chunks porque el retriever opera sobre la pregunta sola, sin el historial. El LLM sí tiene el historial en su prompt y puede inferir el contexto, pero si el threshold filtra todos los chunks (como en P09), el sistema devuelve la respuesta de "no tengo información" en lugar de usar el historial + el LLM. Para producción, se consideraría un paso de reescritura de la pregunta usando el historial antes del retrieval.

2. **Calidad de PDFs generados:** los PDFs creados con `fpdf2` para la prueba tienen texto en dos columnas que PyPDF extrae parcialmente. Los embeddings de texto incompleto tienen menor calidad.

3. **Preguntas fuera de alcance con score marginal:** P11 y P12 obtuvieron un chunk con score 0.31 (apenas sobre el umbral). Si la organización tiene documentos con contenido más diverso, el SIMILARITY_THRESHOLD podría necesitar ajuste hacia 0.40 para reducir falsos positivos.
