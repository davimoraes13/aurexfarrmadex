"""API mínima (FastAPI). NÃO VERIFICADA no ambiente de criação (sem FastAPI instalado)."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from backend.core.mission import InvalidTransition, Mission

app = FastAPI(title="JARVIS X ULTIMATE", version="0.1.0")
_missions: dict[str, Mission] = {}


class MissionIn(BaseModel):
    objective: str
    priority: int = 3


@app.get("/health")
def health():
    return {"status": "ok", "missions": len(_missions)}


@app.post("/missions")
def create_mission(body: MissionIn):
    m = Mission(objective=body.objective, priority=body.priority)
    _missions[m.id] = m
    return {"id": m.id, "state": m.state.value}


@app.get("/missions/{mid}")
def get_mission(mid: str):
    m = _missions.get(mid)
    if not m:
        raise HTTPException(404, "missão não encontrada")
    return {"id": m.id, "objective": m.objective, "state": m.state.value, "history": m.history}


@app.post("/missions/{mid}/cancel")
def cancel_mission(mid: str):
    m = _missions.get(mid)
    if not m:
        raise HTTPException(404, "missão não encontrada")
    try:
        m.cancel("cancelado pelo usuário")
    except InvalidTransition as e:
        raise HTTPException(409, str(e))
    return {"id": m.id, "state": m.state.value}
