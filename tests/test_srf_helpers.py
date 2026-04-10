"""Testes unitarios para funcoes puras do atm_v5 (parsing, rendimento, financeiros)."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import atm_v5 as srf


class TestParseIntervalos(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(srf.parse_intervalos_escolha("1,3", 10), [0, 2])

    def test_range(self):
        self.assertEqual(srf.parse_intervalos_escolha("1-3", 10), [0, 1, 2])

    def test_range_reversed(self):
        self.assertEqual(srf.parse_intervalos_escolha("3-1", 5), [0, 1, 2])

    def test_mixed(self):
        self.assertEqual(srf.parse_intervalos_escolha("1, 5-7", 10), [0, 4, 5, 6])

    def test_dedup(self):
        self.assertEqual(srf.parse_intervalos_escolha("2,2,2", 5), [1])

    def test_out_of_bounds(self):
        self.assertEqual(srf.parse_intervalos_escolha("9-10", 5), [])

    def test_empty(self):
        self.assertEqual(srf.parse_intervalos_escolha("", 5), [])
        self.assertEqual(srf.parse_intervalos_escolha("   ", 5), [])


class TestMedianaRendimento(unittest.TestCase):
    def test_none(self):
        self.assertIsNone(srf.mediana_rendimento_hh({}))
        self.assertIsNone(srf.mediana_rendimento_hh(None))

    def test_median_odd(self):
        t = {"a": {"rendimento_hh": 10.0}, "b": {"rendimento_hh": 20.0}, "c": {"rendimento_hh": 30.0}}
        self.assertEqual(srf.mediana_rendimento_hh(t), 20.0)

    def test_even(self):
        t = {"a": {"rendimento_hh": 10.0}, "b": {"rendimento_hh": 20.0}}
        self.assertEqual(srf.mediana_rendimento_hh(t), 15.0)


class TestResolverRendimento(unittest.TestCase):
    def test_hit_in_tarifas(self):
        cfg = {}
        t = {"X": {"rendimento_hh": 12.5}}
        self.assertEqual(srf.resolver_rendimento_hh(cfg, t, "X"), 12.5)

    def test_fallback_median(self):
        cfg = {}
        t = {"a": {"rendimento_hh": 10.0}, "b": {"rendimento_hh": 20.0}}
        self.assertEqual(srf.resolver_rendimento_hh(cfg, t, "missing"), 15.0)

    def test_fallback_config(self):
        cfg = {"rendimento_hh_fallback": 7.5}
        t = {}
        self.assertEqual(srf.resolver_rendimento_hh(cfg, t, "missing"), 7.5)

    def test_last_resort_8(self):
        cfg = {}
        t = {}
        self.assertEqual(srf.resolver_rendimento_hh(cfg, t, "missing"), 8.0)


class TestResolverPrecoHa(unittest.TestCase):
    def test_hit(self):
        cfg = {}
        t = {"A": {"preco_ha": 950.0}}
        self.assertEqual(srf.resolver_preco_ha(cfg, t, "A"), 950.0)

    def test_fallback_preco_unit(self):
        cfg = {}
        t = {"A": {"preco_unit": 800.0}}
        self.assertEqual(srf.resolver_preco_ha(cfg, t, "A"), 800.0)

    def test_fallback_config(self):
        cfg = {"preco_ha_fallback": 500.0}
        t = {}
        self.assertEqual(srf.resolver_preco_ha(cfg, t, "missing"), 500.0)

    def test_median_fallback(self):
        cfg = {}
        t = {"a": {"preco_ha": 100.0}, "b": {"preco_ha": 200.0}, "c": {"preco_ha": 300.0}}
        self.assertEqual(srf.resolver_preco_ha(cfg, t, "missing"), 200.0)

    def test_zero_when_no_data(self):
        cfg = {}
        t = {}
        self.assertEqual(srf.resolver_preco_ha(cfg, t, "missing"), 0.0)


class TestResolverCustoHora(unittest.TestCase):
    def test_hit(self):
        cfg = {}
        t = {"A": {"custo_hora": 52.86}}
        self.assertAlmostEqual(srf.resolver_custo_hora(cfg, t, "A"), 52.86)

    def test_fallback_config(self):
        cfg = {"custo_hora_tf": 55.0}
        t = {}
        self.assertEqual(srf.resolver_custo_hora(cfg, t, "missing"), 55.0)

    def test_zero_when_empty(self):
        cfg = {}
        t = {}
        self.assertEqual(srf.resolver_custo_hora(cfg, t, "missing"), 0.0)


class TestCarregarStgTarifas(unittest.TestCase):
    def test_basic_load(self):
        import tempfile
        import pandas as pd
        df = pd.DataFrame([{
            "atividade": "ROCADA MANUAL I",
            "tipo": "Manual",
            "rendimento_hh": 12.0,
            "rendimento_hm": 0.0,
            "preco_ha": 947.66,
            "custo_hora": 52.86,
            "custo_ha": 634.32,
            "fonte_aba": "test",
        }])
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            p = tmp.name
        try:
            with pd.ExcelWriter(p, engine="openpyxl") as w:
                df.to_excel(w, sheet_name="STG_TARIFAS", index=False)
            t = srf.carregar_stg_tarifas(p)
            self.assertIn("ROCADA MANUAL I", t)
            self.assertEqual(t["ROCADA MANUAL I"]["rendimento_hh"], 12.0)
            self.assertAlmostEqual(t["ROCADA MANUAL I"]["preco_ha"], 947.66)
            self.assertAlmostEqual(t["ROCADA MANUAL I"]["custo_hora"], 52.86)
        finally:
            os.unlink(p)


if __name__ == "__main__":
    unittest.main()
