# JARVIS X ULTIMATE 3.0

Sistema operacional pessoal de IA (multiagentes), em construção incremental.
Idioma padrão: português brasileiro. Prioridade: soluções gratuitas/open-source.

## Estado atual
Veja `PROJECT_STATUS.md`. Hoje existe o **núcleo testado**: missões, Tool Gateway, persistência, memória, Model Manager,
Agent/Skill Factory e orquestrador.

## Executar os testes (somente biblioteca padrão do Python 3.12)
    python -m unittest discover -s tests -t .

## Executar a API (requer instalação de dependências)
    pip install -r requirements.txt
    uvicorn backend.api.main:app --reload
    # GET http://localhost:8000/health

## Estrutura
    backend/core/       missões e estados (JARVIS CORE)
    backend/security/   Tool Gateway (permissões, aprovação, kill switch, auditoria)
    backend/api/        API FastAPI mínima
    backend/orchestrator/  execução de planos
    backend/agents/     Agent Factory e Skill Factory
    backend/providers/  Model Manager
    backend/memory/     Memory Engine
    backend/database/   persistência (SQLite)
    docs/               arquitetura e segurança
    tests/              testes automatizados
