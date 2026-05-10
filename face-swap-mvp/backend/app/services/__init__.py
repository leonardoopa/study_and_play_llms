"""
app.services — Camada de lógica de negócio

Cada service encapsula regras de negócio de um domínio:
- Recebe dados já validados (DTOs ou primitivos)
- Interage com o banco via SQLAlchemy session
- Retorna models ou dados processados ao controller

Os services serão implementados nas fases seguintes:
- auth_service.py    (FASE 4)
- face_service.py    (FASE 5)
- session_service.py (FASE 5)
- swap_service.py    (FASE 5 — lógica do face swap)
"""
