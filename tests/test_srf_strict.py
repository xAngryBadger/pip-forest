"""Testes modo orcamento_estrito e helpers de bloqueio."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.atm.orca import tarifas, scheduler_core, text_utils, config


class TestResolverStrict(unittest.TestCase):
    def test_rendimento_strict_miss_returns_none(self):
        cfg = {}
        t = {"a": {"rendimento_hh": 10.0}}
        self.assertIsNone(tarifas.resolver_rendimento_hh(cfg, t, "missing", strict=True))

    def test_rendimento_strict_zero_returns_none(self):
        cfg = {}
        t = {"a": {"rendimento_hh": 0.0}}
        self.assertIsNone(tarifas.resolver_rendimento_hh(cfg, t, "a", strict=True))

    def test_rendimento_strict_hit(self):
        cfg = {}
        t = {"a": {"rendimento_hh": 3.5}}
        self.assertEqual(tarifas.resolver_rendimento_hh(cfg, t, "a", strict=True), 3.5)

    def test_somente_bloqueado(self):
        dg = {("T1", "PLANTIO"): 5.0, ("T2", "ROCADA"): 0.0}
        bloq = {"PLANTIO"}
        self.assertTrue(scheduler._somente_bloqueado_restante(dg, bloq))
        dg2 = {("T1", "PLANTIO"): 5.0, ("T2", "ROCADA"): 1.0}
        self.assertFalse(scheduler._somente_bloqueado_restante(dg2, bloq))

    def test_rendimento_strict_mecanizada_returns_zero(self):
        cfg = {}
        t = {"SUBSOL": {"rendimento_hh": 0.0, "rendimento_hm": 1.2, "tipo": "Mecanizada"}}
        self.assertEqual(tarifas.resolver_rendimento_hh(cfg, t, "SUBSOL", strict=True), 0.0)

    def test_rendimento_strict_zero_non_mecanizada_returns_none(self):
        cfg = {}
        t = {"MANUAL": {"rendimento_hh": 0.0, "tipo": "Manual"}}
        self.assertIsNone(tarifas.resolver_rendimento_hh(cfg, t, "MANUAL", strict=True))


class TestNormalizarChave(unittest.TestCase):
    def test_removes_accents_and_punct(self):
        self.assertEqual(text_utils.normalizar_chave("ROÇADA MANUAL Impl. PL APP/RL I"),
                         "rocada manual impl pl app rl i")

    def test_collapses_spaces(self):
        self.assertEqual(text_utils.normalizar_chave(" FOO BAR - BAZ "),
                         "foo bar baz")

    def test_empty_string(self):
        self.assertEqual(text_utils.normalizar_chave(""), "")

    def test_matches_depara_key(self):
        raw = "IRRIGAÇÃO INICIAL MAN Impl. PL - APP/ RL"
        expected = "irrigacao inicial man impl pl app rl"
        self.assertEqual(text_utils.normalizar_chave(raw), expected)
        self.assertIn(expected, constants.DEFAULT_DEPARA_EXAME_CT317)


if __name__ == "__main__":
    unittest.main()
