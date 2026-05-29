"""Testes para funcoes extraidas do scheduler_core (lote, multi-equipes, validacao)."""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import datetime
import calendar

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.atm.orca.scheduler_core import (
    _validar_input,
    _build_resultado_final,
    _construir_atividade_remap,
    _perguntar_data_fim_equipe,
)


class TestValidarInput(unittest.TestCase):
    def test_valid_input_passes(self):
        df = pd.DataFrame({"fazenda": ["F1"], "atividade": ["PLANTIO"], "area_ha": [1.0]})
        err, df_out = _validar_input(df)
        self.assertIsNone(err)

    def test_missing_fazenda_returns_error(self):
        df = pd.DataFrame({"atividade": ["PLANTIO"], "area_ha": [1.0]})
        err, df_out = _validar_input(df)
        self.assertEqual(err, "colunas")

    def test_missing_atividade_returns_error(self):
        df = pd.DataFrame({"fazenda": ["F1"], "area_ha": [1.0]})
        err, df_out = _validar_input(df)
        self.assertIsNotNone(err)

    def test_negative_area_fixup(self):
        df = pd.DataFrame({"fazenda": ["F1"], "atividade": ["PLANTIO"], "area_ha": [-5.0]})
        err, df_out = _validar_input(df)
        self.assertIsNone(err)
        self.assertEqual(df_out["area_ha"].iloc[0], 0.0)

    def test_empty_df_returns_error(self):
        df = pd.DataFrame()
        err, df_out = _validar_input(df)
        self.assertIsNotNone(err)


class TestBuildResultadoFinal(unittest.TestCase):
    def test_returns_dict_with_expected_keys(self):
        result = _build_resultado_final(
            esperar_enter=False,
            fazenda="TESTE",
            dias_simulado=10,
            meses_simulado=0.5,
            prazo_meses=6,
            dias_meta=132,
            total_hh=100.0,
            total_custo=5000.0,
            total_hm=0.0,
            cronograma_base=[],
            turmas=[{"nome": "Turma1", "operarios": 5}],
            resultado_mecanizado=None,
            resultado_mecanizado_valido=False,
            substituicoes_comparativo=None,
            recursos_mec=None,
            cronograma_com_mec=None,
            demandas={},
        )
        self.assertIn("fazenda", result)
        self.assertEqual(result["fazenda"], "TESTE")
        self.assertEqual(result["dias_simulado"], 10)
        self.assertEqual(result["total_hh"], 100.0)
        self.assertEqual(result["total_custo"], 5000.0)

    def test_includes_turmas_snapshot(self):
        turmas = [{"nome": "A", "operarios": 3}, {"nome": "B", "operarios": 5}]
        result = _build_resultado_final(
            esperar_enter=False,
            fazenda="X",
            dias_simulado=5,
            meses_simulado=0.25,
            prazo_meses=6,
            dias_meta=132,
            total_hh=50.0,
            total_custo=2500.0,
            total_hm=0.0,
            cronograma_base=[],
            turmas=turmas,
            resultado_mecanizado=None,
            resultado_mecanizado_valido=False,
            substituicoes_comparativo=None,
            recursos_mec=None,
            cronograma_com_mec=None,
            demandas={},
        )
        self.assertEqual(len(result["turmas_snapshot"]), 2)
        self.assertEqual(result["turmas_snapshot"][0]["nome"], "A")

    def test_with_mecanizado(self):
        result = _build_resultado_final(
            esperar_enter=False,
            fazenda="X",
            dias_simulado=10,
            meses_simulado=0.5,
            prazo_meses=6,
            dias_meta=132,
            total_hh=100.0,
            total_custo=5000.0,
            total_hm=20.0,
            cronograma_base=[],
            turmas=[],
            resultado_mecanizado={"dias_simulado": 8, "total_hh": 60.0, "total_hm": 30.0, "total_custo": 3000.0},
            resultado_mecanizado_valido=True,
            substituicoes_comparativo={"MANUAL": "MECANIZADO"},
            recursos_mec=[{"nome": "Trator"}],
            cronograma_com_mec=[{"Dia": 1}],
            demandas={},
        )
        self.assertIn("comparativo_mecanizado", result)
        self.assertEqual(result["comparativo_mecanizado"]["dias_simulado"], 8)


class TestConstruirAtividadeRemap(unittest.TestCase):
    def test_returns_dict(self):
        result = _construir_atividade_remap({})
        self.assertIsInstance(result, dict)

    def test_empty_cfg_returns_empty_dict(self):
        result = _construir_atividade_remap({})
        self.assertEqual(result, {})


class TestPerguntarDataFimEquipe(unittest.TestCase):
    @patch("src.atm.orca.scheduler_core.confirmar", return_value=False)
    def test_calculated_date_returns_formatted(self, mock_c):
        result = _perguntar_data_fim_equipe("TestEq", 1, 2024, 1, 6)
        self.assertIsNotNone(result)
        self.assertIn("/", result)

    @patch("src.atm.orca.scheduler_core.confirmar", return_value=False)
    def test_calculated_date_6_months(self, mock_c):
        result = _perguntar_data_fim_equipe("TestEq", 1, 2024, 1, 6)
        self.assertEqual(result, "01/06/2024")

    @patch("src.atm.orca.scheduler_core.confirmar", return_value=False)
    def test_calculated_date_3_months(self, mock_c):
        result = _perguntar_data_fim_equipe("TestEq", 3, 2024, 15, 3)
        self.assertEqual(result, "15/05/2024")

    @patch("src.atm.orca.scheduler_core.confirmar", return_value=True)
    @patch("src.atm.orca.scheduler_core.pedir_int")
    def test_manual_date(self, mock_pedir_int, mock_confirmar):
        mock_pedir_int.side_effect = [6, 2024, 15]
        result = _perguntar_data_fim_equipe("TestEq", 1, 2024, 1, 6)
        self.assertEqual(result, "15/06/2024")

    @patch("src.atm.orca.scheduler_core.confirmar", return_value=True)
    @patch("src.atm.orca.scheduler_core.pedir_int")
    def test_manual_date_clamps_values(self, mock_pedir_int, mock_confirmar):
        mock_pedir_int.side_effect = [13, 2024, 32]
        result = _perguntar_data_fim_equipe("TestEq", 1, 2024, 1, 6)
        self.assertEqual(result, "31/12/2024")

    @patch("src.atm.orca.scheduler_core.confirmar", return_value=True)
    @patch("src.atm.orca.scheduler_core.pedir_int")
    def test_manual_date_february(self, mock_pedir_int, mock_confirmar):
        mock_pedir_int.side_effect = [2, 2024, 30]
        result = _perguntar_data_fim_equipe("TestEq", 1, 2024, 1, 6)
        self.assertEqual(result, "29/02/2024")


if __name__ == "__main__":
    unittest.main()
