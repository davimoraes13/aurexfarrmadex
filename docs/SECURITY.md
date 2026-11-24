# Segurança (implementado até agora)

| Regra | Implementação | Teste |
|---|---|---|
| Agente novo sem permissões | deny-by-default em `ToolGateway.execute` | `test_new_agent_has_no_permissions` |
| Permissão por agente e ferramenta | `grant`/`revoke` | `test_grant_does_not_leak_between_agents`, `test_revoke` |
| Alto risco exige aprovação | `RiskLevel.HIGH` + `request_approval`/`approve` | `test_high_risk_needs_approval_even_if_granted` |
| Aprovação presa a agente, ferramenta e argumentos | hash SHA-256 dos argumentos | `test_approval_is_bound_to_*` |
| Aprovação de uso único | removida após o uso | `test_approval_is_single_use` |
| Botão global de parada | `engage_kill_switch` | `test_kill_switch_blocks_everything` |
| Auditoria sem esconder erros | `ToolGateway.audit` | `test_tool_errors_are_audited_not_hidden` |

## Pendente
Autenticação, criptografia, gestão de segredos, isolamento de execução de código, limites por permissão
(pastas/aplicações), proteção contra prompt injection, rate limiting, retenção, backup.
Observação: `approve()` deve ser exposto apenas à interface humana autenticada, nunca a agentes.
