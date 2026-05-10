"""
Face Swap MVP — Entry Point

Este arquivo é o ponto de entrada do Uvicorn.
Toda a configuração da aplicação está no package `app`.

Uso:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

from app import app
