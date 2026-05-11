# 🎭 Face Swap MVP

Real-time face swap via webcam usando InsightFace + ONNX.

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) e [Docker Compose](https://docs.docker.com/compose/install/) instalados
- (Opcional) [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) para aceleração por GPU

## Quick Start

```bash
# 1. Clone o repositório
git clone <repo-url>
cd face-swap-mvp

# 2. Configure as variáveis de ambiente
cp .env.example .env
# Edite .env e troque SECRET_KEY por uma chave segura

# 3. Suba todos os serviços
docker compose up --build

# 4. Acesse no browser
# Frontend: http://localhost:3000
# Backend API docs: http://localhost:8000/docs
```

## Serviços

| Serviço    | Porta | Descrição                        |
|------------|-------|----------------------------------|
| `db`       | 5432  | PostgreSQL 16                    |
| `backend`  | 8000  | FastAPI + Uvicorn                |
| `frontend` | 3000  | Nginx servindo HTML/JS estático  |

## GPU NVIDIA (Opcional)

Para habilitar aceleração por GPU, descomente o bloco `deploy` no `docker-compose.yml`:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

## Status do Projeto

- [x] FASE 1 — Setup do ambiente Docker
- [x] FASE 2 — Banco de dados
- [x] FASE 3 — Face Swap Engine
- [ ] FASE 4 — Autenticação JWT
- [x] FASE 5 — Backend (FastAPI + WebSocket)
- [x] FASE 6 — Frontend
- [ ] FASE 7 — Integração e ajustes
- [ ] FASE 8 — Documentação
