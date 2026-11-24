"""Orquestrador: executa um plano (lista de passos) de uma Mission via Tool Gateway.
Alto risco pausa em AWAITING_APPROVAL; kill switch pausa; falhas de permissão encerram em FAILED."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from backend.core.mission import Mission, MissionState as S
from backend.security.gateway import GatewayError, KillSwitchActive, RiskLevel, ToolGateway


@dataclass
class Step:
    agent: str
    tool: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunResult:
    state: S
    results: list[Any] = field(default_factory=list)
    pending_approval: list[int] = field(default_factory=list)
    error: str = ""


class Orchestrator:
    def __init__(self, gateway: ToolGateway,
                 verifier: Callable[[list[Any]], bool] | None = None) -> None:
        self.gateway = gateway
        self.verifier = verifier or (lambda results: len(results) > 0)

    def run(self, mission: Mission, steps: list[Step],
            approvals: dict[int, str] | None = None) -> RunResult:
        approvals = approvals or {}
        if mission.state == S.RECEIVED:
            mission.transition(S.ANALYZING)
            mission.transition(S.PLANNING)
        elif mission.state == S.PAUSED:
            mission.resume()

        pending = [i for i, s in enumerate(steps)
                   if self.gateway.risk_of(s.tool) >= RiskLevel.HIGH and i not in approvals]
        if pending:
            if mission.state != S.AWAITING_APPROVAL:
                mission.transition(S.AWAITING_APPROVAL, "ação de alto risco")
            return RunResult(mission.state, pending_approval=pending)

        if mission.state != S.EXECUTING:
            mission.transition(S.EXECUTING)
        results: list[Any] = []
        for i, st in enumerate(steps):
            try:
                results.append(self.gateway.execute(st.agent, st.tool, st.args, approvals.get(i)))
            except KillSwitchActive as exc:
                mission.pause(str(exc))
                return RunResult(mission.state, results, error=str(exc))
            except GatewayError as exc:
                mission.transition(S.FAILED, f"passo {i}: {exc}")
                return RunResult(mission.state, results, error=str(exc))
            except Exception as exc:
                mission.transition(S.FAILED, f"passo {i}: {type(exc).__name__}")
                return RunResult(mission.state, results, error=repr(exc))
        mission.transition(S.VERIFYING)
        if self.verifier(results):
            mission.transition(S.COMPLETED)
        else:
            mission.transition(S.FAILED, "verificação falhou")
        return RunResult(mission.state, results)
