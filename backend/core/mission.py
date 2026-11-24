"""Máquina de estados de missões do JARVIS CORE.

Estados conforme o master prompt (seção 4). Inclui proteção contra loops
infinitos: limite de transições e de replanejamentos por missão.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


class MissionState(str, Enum):
    RECEIVED = "RECEIVED"
    ANALYZING = "ANALYZING"
    PLANNING = "PLANNING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PAUSED = "PAUSED"


S = MissionState
TERMINAL = frozenset({S.COMPLETED, S.FAILED, S.CANCELLED})

# PAUSED é tratado à parte (pause/resume), pois retoma o estado anterior.
_ALLOWED: dict[MissionState, frozenset[MissionState]] = {
    S.RECEIVED: frozenset({S.ANALYZING, S.CANCELLED}),
    S.ANALYZING: frozenset({S.PLANNING, S.FAILED, S.CANCELLED}),
    S.PLANNING: frozenset({S.AWAITING_APPROVAL, S.EXECUTING, S.FAILED, S.CANCELLED}),
    S.AWAITING_APPROVAL: frozenset({S.EXECUTING, S.PLANNING, S.FAILED, S.CANCELLED}),
    S.EXECUTING: frozenset({S.VERIFYING, S.AWAITING_APPROVAL, S.PLANNING, S.FAILED, S.CANCELLED}),
    S.VERIFYING: frozenset({S.COMPLETED, S.EXECUTING, S.PLANNING, S.FAILED, S.CANCELLED}),
    S.PAUSED: frozenset({S.CANCELLED}),
    S.COMPLETED: frozenset(),
    S.FAILED: frozenset(),
    S.CANCELLED: frozenset(),
}
_REPLAN_FROM = frozenset({S.AWAITING_APPROVAL, S.EXECUTING, S.VERIFYING})


class InvalidTransition(Exception):
    pass


class LoopLimitExceeded(Exception):
    pass


@dataclass
class Mission:
    objective: str
    priority: int = 3
    max_transitions: int = 50
    max_replans: int = 3
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    state: MissionState = MissionState.RECEIVED
    history: list[dict] = field(default_factory=list)
    _paused_from: MissionState | None = None
    _transitions: int = 0
    _replans: int = 0

    def _record(self, frm: MissionState, to: MissionState, reason: str) -> None:
        self.history.append({"ts": time.time(), "from": frm.value, "to": to.value, "reason": reason})

    def _fail_for_loop(self, reason: str) -> None:
        self._record(self.state, S.FAILED, reason)
        self.state = S.FAILED
        raise LoopLimitExceeded(reason)

    def transition(self, to: MissionState, reason: str = "") -> None:
        if self.state in TERMINAL:
            raise InvalidTransition(f"missão já finalizada ({self.state.value})")
        if to == S.PAUSED or (self.state == S.PAUSED and to != S.CANCELLED):
            raise InvalidTransition("use pause()/resume() para pausar e retomar")
        if to not in _ALLOWED[self.state]:
            raise InvalidTransition(f"{self.state.value} -> {to.value} não é permitido")
        self._transitions += 1
        if self._transitions > self.max_transitions:
            self._fail_for_loop("limite de transições excedido")
        if to == S.PLANNING and self.state in _REPLAN_FROM:
            self._replans += 1
            if self._replans > self.max_replans:
                self._fail_for_loop("limite de replanejamentos excedido")
        self._record(self.state, to, reason)
        self.state = to

    def pause(self, reason: str = "") -> None:
        if self.state in TERMINAL or self.state in (S.PAUSED, S.RECEIVED):
            raise InvalidTransition(f"não é possível pausar em {self.state.value}")
        self._paused_from = self.state
        self._record(self.state, S.PAUSED, reason)
        self.state = S.PAUSED

    def resume(self, reason: str = "") -> None:
        if self.state != S.PAUSED or self._paused_from is None:
            raise InvalidTransition("missão não está pausada")
        self._record(S.PAUSED, self._paused_from, reason)
        self.state = self._paused_from
        self._paused_from = None

    def cancel(self, reason: str = "") -> None:
        self.transition(S.CANCELLED, reason)
