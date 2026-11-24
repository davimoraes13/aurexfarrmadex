# Arquitetura (v0.1)

Princípio: construir a fundação verificável antes de qualquer módulo avançado.

## Decisões
- **Backend:** Python + FastAPI + Pydantic. O núcleo (`core`, `security`) usa só a biblioteca padrão,
  para ser testável sem dependências e portável.
- **Tool Gateway:** único caminho de execução de ferramentas. Agentes nunca chamam ferramentas diretamente.
- **Missões:** máquina de estados explícita com limites de transições e replanejamentos (sem loops infinitos).
- **Ordem de construção:** núcleo → persistência (PostgreSQL) → chat com streaming → Model Manager
  (LiteLLM/Ollama) → agentes (LangGraph) → demais módulos, conforme as 25 etapas do master prompt.

## Fluxo previsto
Usuário → JARVIS CORE (Mission) → Orchestrator → Agente → Tool Gateway → Ferramenta
(cada passo auditado; ação de alto risco pausa a missão em AWAITING_APPROVAL).

## Próximos módulos (ainda não implementados)
Persistência, Model Manager, Orchestrator, agentes, memória (pgvector), MCP, frontend Next.js, Tauri.
