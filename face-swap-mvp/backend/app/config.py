"""
app.config — Configurações globais carregadas de variáveis de ambiente
"""

import os
from dotenv import load_dotenv

# Carrega do .env na raiz do projeto ou no backend
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "troque_por_uma_chave_segura_aqui")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
