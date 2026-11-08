FROM python:3.11-slim

# libgomp1: runtime OpenMP requerido por PyTorch/sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala dependencias antes de copiar el código fuente para aprovechar el layer cache.
# Mientras pyproject.toml no cambie, esta capa se reutiliza en reconstrucciones.
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Código fuente y prompt de sistema por defecto
COPY src/ src/
COPY prompts/ prompts/

# Usuario sin privilegios de root (buena práctica de seguridad en contenedores)
RUN useradd --create-home --shell /bin/bash botuser \
    && mkdir -p /app/knowledge_base /app/chroma_db \
    && chown -R botuser:botuser /app

USER botuser

# HuggingFace descarga el modelo de embeddings al HOME del usuario activo
ENV HF_HOME=/home/botuser/.cache/huggingface

CMD ["python", "-m", "src.main"]
