# ============================================================
# Backend — Face Swap MVP (GPU Enabled)
# Imagem base NVIDIA CUDA para suportar aceleração via GPU
# ============================================================
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Evita prompts interativos e cria .pyc
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Dependências de sistema:
#   - python3 / python3-pip: Python 3.10 (padrão do Ubuntu 22.04)
#   - libgl1 / libglib2.0-0: OpenCV precisa dessas libs
#   - libpq-dev: driver nativo do PostgreSQL (asyncpg)
#   - build-essential: compilar pacotes Python com C extensions
#   - curl: healthcheck e utilidades
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
    libgl1 \
    libglib2.0-0 \
    libpq-dev \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Configura o alias do python
RUN ln -sf /usr/bin/python3 /usr/local/bin/python

WORKDIR /app

# Instala dependências Python primeiro (cacheia camada Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código do backend
COPY . .

# Garante que o entrypoint.sh é executável
RUN chmod +x entrypoint.sh

# Porta do Uvicorn
EXPOSE 8000

# Entrypoint roda migrations e sobe o servidor
ENTRYPOINT ["./entrypoint.sh"]
