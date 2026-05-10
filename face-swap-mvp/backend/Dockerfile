# ============================================================
# Backend — Face Swap MVP
# Imagem base leve; dependências de sistema para OpenCV e dlib
# ============================================================
FROM python:3.11-slim

# Evita prompts interativos e cria .pyc
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Dependências de sistema:
#   - libgl1 / libglib2.0-0: OpenCV precisa dessas libs
#   - libpq-dev: driver nativo do PostgreSQL (asyncpg)
#   - build-essential: compilar pacotes Python com C extensions
#   - curl: healthcheck e utilidades
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libpq-dev \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

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
