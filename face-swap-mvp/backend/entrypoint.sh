#!/bin/bash
set -e

echo "=========================================="
echo " Face Swap MVP — Backend Startup"
echo "=========================================="

# ------------------------------------------------------------------
# 0. Baixa modelos ONNX se não existirem
# ------------------------------------------------------------------
echo "[0/3] Verificando modelos..."

MODEL_DIR="/app/models"
SWAP_MODEL="${MODEL_DIR}/inswapper_128.onnx"

if [ ! -f "${SWAP_MODEL}" ]; then
    echo "  Baixando inswapper_128.onnx do HuggingFace..."
    mkdir -p "${MODEL_DIR}"
    curl -L -o "${SWAP_MODEL}" \
        "https://huggingface.co/ezioruan/inswapper_128.onnx/resolve/main/inswapper_128.onnx"
    echo "  Download concluído! ($(du -h "${SWAP_MODEL}" | cut -f1))"
else
    echo "  inswapper_128.onnx já existe ($(du -h "${SWAP_MODEL}" | cut -f1))"
fi

# GFPGAN — face enhancer (melhora qualidade do rosto swapped)
ENHANCER_MODEL="${MODEL_DIR}/GFPGANv1.4.onnx"

if [ ! -f "${ENHANCER_MODEL}" ]; then
    echo "  Baixando GFPGANv1.4.onnx do HuggingFace..."
    mkdir -p "${MODEL_DIR}"
    curl -L -o "${ENHANCER_MODEL}" \
        "https://huggingface.co/hacksider/deep-live-cam/resolve/main/GFPGANv1.4.onnx"
    echo "  Download concluído! ($(du -h "${ENHANCER_MODEL}" | cut -f1))"
else
    echo "  GFPGANv1.4.onnx já existe ($(du -h "${ENHANCER_MODEL}" | cut -f1))"
fi

# ------------------------------------------------------------------
# 1. Aguarda o PostgreSQL aceitar conexões (até 30 segundos)
#    Nota: O docker-compose já usa healthcheck/depends_on, mas este
#    script serve como fallback para execuções fora do compose.
# ------------------------------------------------------------------
echo "[1/3] Aguardando PostgreSQL..."

MAX_RETRIES=30
RETRY_COUNT=0

# Usa Python para extrair host/porta e testar a conexão TCP
until python3 -c "
import socket, os
from urllib.parse import urlparse

url = os.environ.get('DATABASE_URL', '')
if not url:
    raise SystemExit('DATABASE_URL inválida')

parsed = urlparse(url)
host, port = parsed.hostname, parsed.port
if not host or port is None:
    raise SystemExit('DATABASE_URL inválida')

s = socket.create_connection((host, port), timeout=2)
s.close()
" 2>/dev/null; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "ERRO: PostgreSQL não ficou disponível após ${MAX_RETRIES}s"
        exit 1
    fi
    echo "  Tentativa ${RETRY_COUNT}/${MAX_RETRIES}..."
    sleep 1
done

echo "  PostgreSQL está pronto!"

# ------------------------------------------------------------------
# 2. Roda as migrations do Alembic (quando configuradas)
# ------------------------------------------------------------------
echo "[2/3] Rodando migrations..."

if [ -f "/app/alembic.ini" ]; then
    alembic upgrade head
    echo "  Migrations aplicadas com sucesso!"
else
    echo "  alembic.ini não encontrado — pulando migrations (FASE 1)"
fi

# ------------------------------------------------------------------
# 3. Sobe o servidor Uvicorn
# ------------------------------------------------------------------
echo "[3/3] Iniciando Uvicorn..."
echo "=========================================="

exec uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info
