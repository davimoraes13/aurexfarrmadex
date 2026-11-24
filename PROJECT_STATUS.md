# PROJECT_STATUS

_Atualizado em 24/11/2026_

## Construído e testado (35 testes, 34 passando e 1 que só roda com FastAPI instalado)
- **Missões:** máquina de estados, pausa/retomada, limites contra loops (`backend/core/mission.py`).
- **Tool Gateway:** permissões deny-by-default, aprovação de alto risco de uso único, kill switch, auditoria.
- **Persistência:** SQLite (`backend/database/db.py`), com ida e volta de missões testada.
- **Memory Engine:** adicionar, buscar (por termos), editar, apagar, exportar; recusa credenciais.
- **Model Manager:** roteamento gratuito primeiro, fallback, contabilidade de tokens/custo; pago só com autorização.
- **Agent Factory / Skill Factory:** validação, duplicar, exportar/importar (importados nascem inativos),
  agentes sem permissões reais até `grant` humano.
- **Orquestrador:** executa planos via Gateway; alto risco pausa em AWAITING_APPROVAL; kill switch pausa; verificação final.

## Escrito, mas NÃO verificado com FastAPI real (sem rede no ambiente de criação)
- `main.py` (entrypoint do deploy) e `backend/api/main.py`: caminhos de import e rotas conferidos só com stubs.
  O CI (`.github/workflows/ci.yml`) roda isso com FastAPI real a cada push.
- `OllamaProvider` em `backend/providers/manager.py` (precisa de Ollama rodando).

## Limitações conhecidas
- Em deploy serverless, o estado em memória/SQLite não persiste entre requisições.
- Busca da memória é por termos, não semântica (pgvector/embeddings pendentes).
- Nenhum planejador com LLM ainda: o orquestrador recebe o plano pronto.
- Permissões de risco moderado ainda não têm limites por pasta/aplicação.
- SQLite é provisório; PostgreSQL ainda não foi integrado.

## Não iniciado
Dashboard/frontend (Next.js), chat com streaming, provedores em nuvem, MCP, pesquisa/navegador,
Coding Studio, Computer Use, automação, voz, multimodal, Mission Control (UI), marketplace,
desktop (Tauri), mobile/PWA, analytics, autenticação, deploy.

## Próximo passo
Verificar a API com FastAPI instalado e ligá-la ao Orquestrador e ao banco; em seguida, o planejador
com LLM (via Model Manager) e o chat com streaming.
