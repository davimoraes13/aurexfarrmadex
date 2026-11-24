"""Tool Gateway: único caminho para agentes executarem ferramentas.

Regras (seções 29 e 35 do master prompt):
- Agente novo não tem nenhuma permissão (deny-by-default).
- Ferramentas de ALTO RISCO exigem aprovação humana explícita, de uso único,
  vinculada ao agente, à ferramenta e aos argumentos exatos.
- Botão global de parada (kill switch) bloqueia tudo.
- Toda tentativa (permitida ou negada) é registrada na auditoria.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Callable


class RiskLevel(IntEnum):
    LOW = 1
    MODERATE = 2
    HIGH = 3


@dataclass(frozen=True)
class ToolSpec:
    name: str
    risk: RiskLevel
    description: str = ""


class GatewayError(Exception):
    pass


class UnknownTool(GatewayError):
    pass


class PermissionDenied(GatewayError):
    pass


class ApprovalRequired(GatewayError):
    pass


class KillSwitchActive(GatewayError):
    pass


def _args_hash(args: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(args, sort_keys=True, default=str).encode()).hexdigest()


class ToolGateway:
    def __init__(self) -> None:
        self._specs: dict[str, ToolSpec] = {}
        self._handlers: dict[str, Callable[..., Any]] = {}
        self._grants: dict[str, set[str]] = {}
        self._approvals: dict[str, dict] = {}
        self._kill = False
        self.audit: list[dict] = []

    # --- registro e permissões -------------------------------------------
    def register_tool(self, spec: ToolSpec, handler: Callable[..., Any]) -> None:
        self._specs[spec.name] = spec
        self._handlers[spec.name] = handler

    def risk_of(self, tool: str) -> RiskLevel:
        if tool not in self._specs:
            raise UnknownTool(tool)
        return self._specs[tool].risk

    def has_tool(self, tool: str) -> bool:
        return tool in self._specs

    def grant(self, agent: str, tool: str) -> None:
        if tool not in self._specs:
            raise UnknownTool(tool)
        self._grants.setdefault(agent, set()).add(tool)

    def revoke(self, agent: str, tool: str) -> None:
        self._grants.get(agent, set()).discard(tool)

    # --- kill switch -------------------------------------------------------
    def engage_kill_switch(self) -> None:
        self._kill = True

    def release_kill_switch(self) -> None:
        self._kill = False

    # --- aprovações (chamadas pela interface humana, nunca por agentes) ---
    def request_approval(self, agent: str, tool: str, args: dict[str, Any]) -> str:
        if tool not in self._specs:
            raise UnknownTool(tool)
        aid = uuid.uuid4().hex
        self._approvals[aid] = {
            "agent": agent, "tool": tool, "hash": _args_hash(args), "approved": False,
        }
        return aid

    def approve(self, approval_id: str) -> None:
        self._approvals[approval_id]["approved"] = True

    # --- execução ------------------------------------------------------------
    def _log(self, agent: str, tool: str, outcome: str) -> None:
        self.audit.append({"ts": time.time(), "agent": agent, "tool": tool, "outcome": outcome})

    def execute(self, agent: str, tool: str, args: dict[str, Any] | None = None,
                approval_id: str | None = None) -> Any:
        args = args or {}
        if self._kill:
            self._log(agent, tool, "denied:kill_switch")
            raise KillSwitchActive("execução interrompida pelo botão global de parada")
        spec = self._specs.get(tool)
        if spec is None:
            self._log(agent, tool, "denied:unknown_tool")
            raise UnknownTool(tool)
        if tool not in self._grants.get(agent, set()):
            self._log(agent, tool, "denied:not_granted")
            raise PermissionDenied(f"agente '{agent}' não tem permissão para '{tool}'")
        if spec.risk >= RiskLevel.HIGH:
            ap = self._approvals.get(approval_id or "")
            valid = (
                ap is not None and ap["approved"] and ap["agent"] == agent
                and ap["tool"] == tool and ap["hash"] == _args_hash(args)
            )
            if not valid:
                self._log(agent, tool, "denied:approval_required")
                raise ApprovalRequired(f"'{tool}' é de alto risco e exige aprovação explícita")
            del self._approvals[approval_id]  # uso único
        try:
            result = self._handlers[tool](**args)
        except Exception as exc:  # erro da ferramenta não pode ser escondido
            self._log(agent, tool, f"error:{type(exc).__name__}")
            raise
        self._log(agent, tool, "allowed")
        return result
