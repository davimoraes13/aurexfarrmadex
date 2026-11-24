import unittest

from backend.security.gateway import (ApprovalRequired, KillSwitchActive, PermissionDenied,
                                      RiskLevel, ToolGateway, ToolSpec, UnknownTool)


def make():
    g = ToolGateway()
    g.register_tool(ToolSpec("web_search", RiskLevel.LOW), lambda q: f"res:{q}")
    g.register_tool(ToolSpec("send_email", RiskLevel.HIGH), lambda to: f"sent:{to}")
    return g


class GatewayTests(unittest.TestCase):
    def test_new_agent_has_no_permissions(self):
        g = make()
        with self.assertRaises(PermissionDenied):
            g.execute("coder", "web_search", {"q": "x"})
        self.assertEqual(g.audit[-1]["outcome"], "denied:not_granted")

    def test_granted_low_risk_tool_runs(self):
        g = make()
        g.grant("coder", "web_search")
        self.assertEqual(g.execute("coder", "web_search", {"q": "x"}), "res:x")
        self.assertEqual(g.audit[-1]["outcome"], "allowed")

    def test_unknown_tool(self):
        g = make()
        with self.assertRaises(UnknownTool):
            g.execute("coder", "rm_rf")

    def test_grant_does_not_leak_between_agents(self):
        g = make()
        g.grant("a", "web_search")
        with self.assertRaises(PermissionDenied):
            g.execute("b", "web_search", {"q": "x"})

    def test_revoke(self):
        g = make()
        g.grant("a", "web_search")
        g.revoke("a", "web_search")
        with self.assertRaises(PermissionDenied):
            g.execute("a", "web_search", {"q": "x"})

    def test_high_risk_needs_approval_even_if_granted(self):
        g = make()
        g.grant("a", "send_email")
        with self.assertRaises(ApprovalRequired):
            g.execute("a", "send_email", {"to": "x@y.com"})

    def test_pending_approval_is_not_enough(self):
        g = make()
        g.grant("a", "send_email")
        aid = g.request_approval("a", "send_email", {"to": "x@y.com"})
        with self.assertRaises(ApprovalRequired):
            g.execute("a", "send_email", {"to": "x@y.com"}, approval_id=aid)

    def test_approval_is_bound_to_exact_args(self):
        g = make()
        g.grant("a", "send_email")
        aid = g.request_approval("a", "send_email", {"to": "x@y.com"})
        g.approve(aid)
        with self.assertRaises(ApprovalRequired):
            g.execute("a", "send_email", {"to": "outro@y.com"}, approval_id=aid)

    def test_approval_is_bound_to_agent(self):
        g = make()
        g.grant("a", "send_email")
        g.grant("b", "send_email")
        aid = g.request_approval("a", "send_email", {"to": "x@y.com"})
        g.approve(aid)
        with self.assertRaises(ApprovalRequired):
            g.execute("b", "send_email", {"to": "x@y.com"}, approval_id=aid)

    def test_approval_is_single_use(self):
        g = make()
        g.grant("a", "send_email")
        aid = g.request_approval("a", "send_email", {"to": "x@y.com"})
        g.approve(aid)
        self.assertEqual(g.execute("a", "send_email", {"to": "x@y.com"}, aid), "sent:x@y.com")
        with self.assertRaises(ApprovalRequired):
            g.execute("a", "send_email", {"to": "x@y.com"}, aid)

    def test_kill_switch_blocks_everything(self):
        g = make()
        g.grant("a", "web_search")
        g.engage_kill_switch()
        with self.assertRaises(KillSwitchActive):
            g.execute("a", "web_search", {"q": "x"})
        g.release_kill_switch()
        self.assertEqual(g.execute("a", "web_search", {"q": "x"}), "res:x")

    def test_tool_errors_are_audited_not_hidden(self):
        g = ToolGateway()
        g.register_tool(ToolSpec("boom", RiskLevel.LOW), lambda: 1 / 0)
        g.grant("a", "boom")
        with self.assertRaises(ZeroDivisionError):
            g.execute("a", "boom")
        self.assertEqual(g.audit[-1]["outcome"], "error:ZeroDivisionError")


if __name__ == "__main__":
    unittest.main()
