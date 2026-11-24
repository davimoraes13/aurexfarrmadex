"""Ponto de entrada para deploy (Vercel/Render/etc. procuram `app` em main.py na raiz).

A aplicação real fica em backend/api/main.py.
Local:  uvicorn main:app --reload
"""
from backend.api.main import app  # noqa: F401  (reexporta a instância FastAPI)
