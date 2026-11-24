import unittest

from backend.agents.factory import AgentFactory, InvalidSpec, SkillFactory
from backend.core.mission import Mission, MissionState as S
from backend.database.db import Database
from backend.memory.engine import MemoryEngine, SecretDetected
from backend.orchestrator.runner import Orchestrator, Step
from backend.providers.manager import Completion, ModelInfo, ModelManager, NoModelAvailable
from backend.security.gateway import RiskLevel, ToolGateway, ToolSpec


class Fake:  # provedor de TESTE, nunca registrado em produção
    def __init__(self, name, fail=False):
        self.name, self.fail = name, fail

    def complete(self, model, messages):
        if self.fail:
            raise RuntimeError("indisponível")
        return Completion(f"{model}:ok", 10, 20)


class PersistenceTests(unittest.TestCase):
    def test_mission_roundtrip(self):
        db = Database()
        m = Mission("x")
        m.transition(S.ANALYZING); m.transition(S.PLANNING); m.pause("p")
        db.save_mission(m)
        r = db.load_mission(m.id)
        self.assertEqual((r.state, r.history, r._paused_from), (S.PAUSED, m.history, S.PLANNING))
        r.resume()
        self.assertEqual(r.state, S.PLANNING)
        self.assertIsNone(db.load_mission("nao-existe"))


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.mem = MemoryEngine(Database())

    def test_add_search_update_delete(self):
        a = self.mem.add("Prefere respostas em português brasileiro", ["idioma"])
        self.mem.add("Projeto de revista gamer")
        self.assertEqual(self.mem.search("português")[0]["id"], a)
        self.assertTrue(self.mem.update(a, "Prefere respostas curtas"))
        self.assertEqual(self.mem.search("curtas")[0]["id"], a)
        self.assertTrue(self.mem.delete(a))
        self.assertEqual(self.mem.search("curtas"), [])
        self.assertIn("revista", self.mem.export())

    def test_rejects_credentials(self):
        for bad in ("minha senha: abc123", "key sk-abcdefghijklmnop1234", "api_key=xyz"):
            with self.assertRaises(SecretDetected):
                self.mem.add(bad)


class ModelManagerTests(unittest.TestCase):
    def test_free_first_and_fallback(self):
        mm = ModelManager()
        mm.register(Fake("a", fail=True), ModelInfo("a", "free-bad", 1))
        mm.register(Fake("b"), ModelInfo("b", "free-good", 2))
        self.assertEqual(mm.complete([], 1).text, "free-good:ok")
        self.assertEqual([u["ok"] for u in mm.usage], [False, True])

    def test_paid_requires_authorization(self):
        mm = ModelManager()
        mm.register(Fake("p"), ModelInfo("p", "paid", 3, cost_per_1k=0.01))
        with self.assertRaises(NoModelAvailable):
            mm.complete([], 3)
        out = mm.complete([], 3, allow_paid=True)
        self.assertEqual(out.text, "paid:ok")
        self.assertAlmostEqual(mm.usage[-1]["cost"], 0.0003)

    def test_complexity_filter(self):
        mm = ModelManager()
        mm.register(Fake("a"), ModelInfo("a", "small", 1))
        with self.assertRaises(NoModelAvailable):
            mm.complete([], 3)


class FactoryTests(unittest.TestCase):
    def setUp(self):
        self.f = AgentFactory({"web_search", "send_email"})

    def test_create_validates(self):
        a = self.f.create("roblox-dev", "jogos Roblox", "Ajude com Luau", ["web_search"])
        self.assertTrue(a.active)
        for bad in (dict(name="Nome Ruim", instructions="x"), dict(name="ok-agent", instructions=" "),
                    dict(name="ok-agent", instructions="x", requested_tools=["rm_rf"]),
                    dict(name="roblox-dev", instructions="x")):
            with self.assertRaises(InvalidSpec):
                self.f.create(bad["name"], "e", bad["instructions"], bad.get("requested_tools"))

    def test_new_agent_has_no_real_permissions(self):
        g = ToolGateway()
        g.register_tool(ToolSpec("web_search", RiskLevel.LOW), lambda q: q)
        self.f.create("a1", "e", "i", ["web_search"])
        from backend.security.gateway import PermissionDenied
        with self.assertRaises(PermissionDenied):
            g.execute("a1", "web_search", {"q": "x"})

    def test_duplicate_export_import(self):
        self.f.create("a1", "e", "i", ["web_search"])
        self.f.duplicate("a1", "a2")
        raw = self.f.export("a1")
        other = AgentFactory({"web_search"})
        imp = other.import_json(raw)
        self.assertFalse(imp.active)
        self.f.delete("a2")
        self.assertEqual(self.f.names(), ["a1"])

    def test_skills_start_inactive(self):
        sf = SkillFactory({"web_search"})
        s = sf.add(sf.cls("analisar-planilha", "analisar", "passos", requested_tools=["web_search"]))
        self.assertFalse(s.active)


class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.g = ToolGateway()
        self.g.register_tool(ToolSpec("search", RiskLevel.LOW), lambda q: f"r:{q}")
        self.g.register_tool(ToolSpec("email", RiskLevel.HIGH), lambda to: f"sent:{to}")
        self.g.grant("a", "search")
        self.g.grant("a", "email")
        self.o = Orchestrator(self.g)

    def test_low_risk_completes(self):
        m = Mission("m")
        r = self.o.run(m, [Step("a", "search", {"q": "x"})])
        self.assertEqual((r.state, r.results), (S.COMPLETED, ["r:x"]))

    def test_high_risk_waits_then_runs_with_approval(self):
        m = Mission("m")
        steps = [Step("a", "search", {"q": "x"}), Step("a", "email", {"to": "u@x.com"})]
        r = self.o.run(m, steps)
        self.assertEqual((r.state, r.pending_approval, r.results), (S.AWAITING_APPROVAL, [1], []))
        aid = self.g.request_approval("a", "email", {"to": "u@x.com"})
        self.g.approve(aid)
        r = self.o.run(m, steps, {1: aid})
        self.assertEqual((r.state, r.results), (S.COMPLETED, ["r:x", "sent:u@x.com"]))

    def test_unauthorized_agent_fails_mission(self):
        m = Mission("m")
        r = self.o.run(m, [Step("intruso", "search", {"q": "x"})])
        self.assertEqual(r.state, S.FAILED)

    def test_kill_switch_pauses_and_resumes(self):
        m = Mission("m")
        self.g.engage_kill_switch()
        r = self.o.run(m, [Step("a", "search", {"q": "x"})])
        self.assertEqual(r.state, S.PAUSED)
        self.g.release_kill_switch()
        r = self.o.run(m, [Step("a", "search", {"q": "x"})])
        self.assertEqual(r.state, S.COMPLETED)

    def test_failed_verification(self):
        o = Orchestrator(self.g, verifier=lambda res: False)
        r = o.run(Mission("m"), [Step("a", "search", {"q": "x"})])
        self.assertEqual(r.state, S.FAILED)


if __name__ == "__main__":
    unittest.main()
