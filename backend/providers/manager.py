"""Model Manager: registro de modelos, roteamento (gratuito primeiro), fallback e contabilidade.
Modelos pagos só são usados com autorização explícita (allow_paid=True)."""
from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass
from typing import Protocol


@dataclass
class Completion:
    text: str
    tokens_in: int = 0
    tokens_out: int = 0


@dataclass(frozen=True)
class ModelInfo:
    provider: str
    name: str
    capability: int = 1          # 1 simples, 2 médio, 3 complexo
    cost_per_1k: float = 0.0     # 0 = gratuito/local
    max_context: int = 8192


class Provider(Protocol):
    name: str

    def complete(self, model: str, messages: list[dict]) -> Completion: ...


class NoModelAvailable(Exception):
    pass


class OllamaProvider:
    """Provedor local (Ollama). NÃO VERIFICADO aqui: o ambiente não tinha rede nem Ollama."""
    name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434", timeout: float = 120) -> None:
        self.base_url, self.timeout = base_url.rstrip("/"), timeout

    def complete(self, model: str, messages: list[dict]) -> Completion:
        body = json.dumps({"model": model, "messages": messages, "stream": False}).encode()
        req = urllib.request.Request(f"{self.base_url}/api/chat", body,
                                     {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            data = json.load(r)
        return Completion(data["message"]["content"], data.get("prompt_eval_count", 0),
                          data.get("eval_count", 0))


class ModelManager:
    def __init__(self) -> None:
        self._providers: dict[str, Provider] = {}
        self._models: list[ModelInfo] = []
        self.usage: list[dict] = []

    def register(self, provider: Provider, *models: ModelInfo) -> None:
        self._providers[provider.name] = provider
        self._models.extend(models)

    def candidates(self, complexity: int = 1, allow_paid: bool = False) -> list[ModelInfo]:
        ok = [m for m in self._models
              if m.capability >= complexity and (allow_paid or m.cost_per_1k == 0)]
        return sorted(ok, key=lambda m: (m.cost_per_1k, m.capability))

    def complete(self, messages: list[dict], complexity: int = 1,
                 allow_paid: bool = False) -> Completion:
        cands = self.candidates(complexity, allow_paid)
        if not cands:
            raise NoModelAvailable("nenhum modelo adequado (modelos pagos exigem autorização)")
        last: Exception | None = None
        for m in cands:
            t0 = time.time()
            try:
                out = self._providers[m.provider].complete(m.name, messages)
            except Exception as exc:  # fallback para o próximo candidato
                last = exc
                self.usage.append({"model": m.name, "ok": False, "error": type(exc).__name__})
                continue
            cost = (out.tokens_in + out.tokens_out) / 1000 * m.cost_per_1k
            self.usage.append({"model": m.name, "ok": True, "latency": time.time() - t0,
                               "tokens_in": out.tokens_in, "tokens_out": out.tokens_out,
                               "cost": cost})
            return out
        raise NoModelAvailable(f"todos os modelos falharam; último erro: {last!r}")
