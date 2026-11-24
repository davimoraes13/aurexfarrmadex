import unittest

from backend.core.mission import (InvalidTransition, LoopLimitExceeded, Mission,
                                  MissionState as S)


class MissionTests(unittest.TestCase):
    def test_happy_path(self):
        m = Mission("teste")
        for s in (S.ANALYZING, S.PLANNING, S.EXECUTING, S.VERIFYING, S.COMPLETED):
            m.transition(s)
        self.assertEqual(m.state, S.COMPLETED)
        self.assertEqual(len(m.history), 5)

    def test_invalid_transition_rejected(self):
        m = Mission("teste")
        with self.assertRaises(InvalidTransition):
            m.transition(S.EXECUTING)

    def test_terminal_state_is_final(self):
        m = Mission("teste")
        m.cancel()
        with self.assertRaises(InvalidTransition):
            m.transition(S.ANALYZING)

    def test_pause_and_resume_restores_state(self):
        m = Mission("teste")
        m.transition(S.ANALYZING)
        m.transition(S.PLANNING)
        m.pause()
        self.assertEqual(m.state, S.PAUSED)
        m.resume()
        self.assertEqual(m.state, S.PLANNING)

    def test_replan_loop_is_stopped(self):
        m = Mission("teste", max_replans=2)
        m.transition(S.ANALYZING)
        m.transition(S.PLANNING)
        with self.assertRaises(LoopLimitExceeded):
            for _ in range(10):
                m.transition(S.EXECUTING)
                m.transition(S.PLANNING)
        self.assertEqual(m.state, S.FAILED)

    def test_transition_limit(self):
        m = Mission("teste", max_transitions=3, max_replans=99)
        m.transition(S.ANALYZING)
        m.transition(S.PLANNING)
        m.transition(S.EXECUTING)
        with self.assertRaises(LoopLimitExceeded):
            m.transition(S.PLANNING)
        self.assertEqual(m.state, S.FAILED)


if __name__ == "__main__":
    unittest.main()
