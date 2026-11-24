"""Agent Factory e Skill Factory. Agentes/skills novos nascem sem permissões; ferramentas pedidas
ficam como 'requested_tools' e só valem após grant humano no Tool Gateway. Importados nascem inativos."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field

_SLUG = re.compile(r"^[a-z0-9][a-z0-9_\-]{1,40}$")


class InvalidSpec(Exception):
    pass


@dataclass
class AgentSpec:
    name: str
    specialty: str
    instructions: str
    requested_tools: list[str] = field(default_factory=list)
    model_tier: int = 1
    version: int = 1
    active: bool = True


@dataclass
class Skill:
    name: str
    objective: str
    instructions: str
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    requested_tools: list[str] = field(default_factory=list)
    version: int = 1
    active: bool = False  # skill só é ativada após revisão


class Registry:
    kind = "item"
    cls: type = object

    def __init__(self, known_tools: set[str]) -> None:
        self.known_tools = set(known_tools)
        self._items: dict[str, object] = {}

    def _validate(self, spec) -> None:
        if not _SLUG.match(spec.name):
            raise InvalidSpec("nome inválido (use a-z, 0-9, _ ou -)")
        if not spec.instructions.strip():
            raise InvalidSpec("instruções vazias")
        unknown = set(spec.requested_tools) - self.known_tools
        if unknown:
            raise InvalidSpec(f"ferramentas desconhecidas: {sorted(unknown)}")
        if spec.name in self._items:
            raise InvalidSpec(f"'{spec.name}' já existe")

    def add(self, spec):
        self._validate(spec)
        self._items[spec.name] = spec
        return spec

    def get(self, name: str):
        return self._items[name]

    def names(self) -> list[str]:
        return sorted(self._items)

    def duplicate(self, name: str, new_name: str):
        data = asdict(self._items[name])
        data.update(name=new_name, version=1)
        return self.add(self.cls(**data))

    def set_active(self, name: str, active: bool) -> None:
        self._items[name].active = active

    def delete(self, name: str) -> None:
        del self._items[name]

    def export(self, name: str) -> str:
        return json.dumps(asdict(self._items[name]), ensure_ascii=False)

    def import_json(self, raw: str):
        data = json.loads(raw)
        data["active"] = False  # nunca ativar automaticamente algo importado
        return self.add(self.cls(**data))


class AgentFactory(Registry):
    kind, cls = "agent", AgentSpec

    def create(self, name: str, specialty: str, instructions: str,
               requested_tools: list[str] | None = None, model_tier: int = 1) -> AgentSpec:
        return self.add(AgentSpec(name, specialty, instructions, requested_tools or [], model_tier))


class SkillFactory(Registry):
    kind, cls = "skill", Skill
