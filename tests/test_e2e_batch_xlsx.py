import glob
import os
import shutil
import tempfile
import unittest

import src.atm.orca.ui as _ui

_ui.confirmar = lambda msg, default=True, **kw: default
_ui.pedir_float = lambda msg, default=0.0, **kw: float(default)
_ui.pedir_int = lambda msg, default=1, **kw: int(float(default))
_ui.selecionar = lambda msg, options, **kw: 1
_ui.selecionar_paginado = lambda msg, items, **kw: 0
_ui.prompt = lambda msg, default="", **kw: str(default)
_ui.escolha = lambda msg, default="1", **kw: str(default)
_ui.esperar = lambda msg, **kw: None
_ui.pedir_jornada = lambda msg, default=8.0, **kw: float(default)

import pandas as pd
from src.atm.orca.config import OUTPUT_DIR, carregar_config
from src.atm.orca.io import carregar_planilha_microplanejamento
from src.atm.orca.scheduler_core import calcular_cronograma_inteligente

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
_PLANILHAS_DIR = os.path.join(_DATA_DIR, "planilhas")
_FORMOSA_XLSX = os.path.join(_PLANILHAS_DIR, "formosa.xlsx")


def _ctx_batch(jornada=5.6, operarios=9, turma_nome="SVG_001"):
    return {
        "modo_seq": "implantacao",
        "usar_bloqueio_global": True,
        "usar_reforco_automatico": True,
        "usar_pool_pos_bloqueio": True,
        "prazo_meses": 6.0,
        "mes_ref": 1,
        "ano_ref": 2026,
        "jornada": jornada,
        "executores": operarios,
        "turmas": [
            {"nome": turma_nome, "operarios": operarios, "atividades": "todas"}
        ],
        "penalidade": 1.0,
        "preencher_orfas_template": False,
    }


class TestE2EBatchXlsx(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cfg = carregar_config()
        cls._orcamento_backup = cfg.get("orcamento_estrito", True)
        cfg["orcamento_estrito"] = False
        xlsx_path = _FORMOSA_XLSX
        if not os.path.exists(xlsx_path):
            raise unittest.SkipTest(f"Planilha nao encontrada: {xlsx_path}")
        df = carregar_planilha_microplanejamento(cfg, caminho=xlsx_path, modo_auto=True)
        if df is None or df.empty:
            raise unittest.SkipTest("carregar_planilha_microplanejamento retornou None/vazio")
        cls.cfg = cfg
        cls.df = df
        cls.fazenda = "FORMOSA"
        cls.atividades_catalogo = sorted(
            {str(x).strip() for x in df["atividade"].dropna().unique() if str(x).strip()}
        )
        cls._output_backup = OUTPUT_DIR

    @classmethod
    def tearDownClass(cls):
        cls.cfg["orcamento_estrito"] = cls._orcamento_backup

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="srf_e2e_")
        import src.atm.orca.scheduler_core as _sc
        _sc.OUTPUT_DIR = self._tmpdir

    def tearDown(self):
        import src.atm.orca.scheduler_core as _sc
        _sc.OUTPUT_DIR = self._output_backup
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _run_batch(self, jornada=5.6, operarios=9):
        df_faz = self.df[self.df["fazenda"] == self.fazenda].copy()
        ctx = _ctx_batch(jornada=jornada, operarios=operarios)
        return calcular_cronograma_inteligente(
            self.cfg,
            df_faz,
            self.fazenda,
            esperar_enter=False,
            ctx=ctx,
            atividades_catalogo=self.atividades_catalogo,
        )

    def _find_xlsx(self):
        xlsx_files = glob.glob(os.path.join(self._tmpdir, "Dossier_*_OPERACIONAL*.xlsx"))
        return sorted(xlsx_files)

    def test_batch_produces_xlsx(self):
        r = self._run_batch(jornada=5.6, operarios=9)
        self.assertIsNotNone(r, "calcular_cronograma_inteligente retornou None")
        if isinstance(r, dict) and r.get("acao") == "orcamento_invalido":
            self.skipTest("orcamento_estrito bloqueou (sem tarifas)")
        xlsx_files = self._find_xlsx()
        self.assertGreaterEqual(
            len(xlsx_files), 1, f"Nenhum xlsx operacional em {self._tmpdir}"
        )
        caminho = xlsx_files[-1]
        xls = pd.ExcelFile(caminho)
        self.assertIn("RESUMO_OPERACIONAL", xls.sheet_names)
        self.assertIn("CRONOGRAMA_DETALHADO", xls.sheet_names)
        df_resumo = pd.read_excel(caminho, sheet_name="RESUMO_OPERACIONAL")
        resumo_dict = dict(zip(df_resumo["Metrica"], df_resumo["Valor"]))
        self.assertEqual(str(resumo_dict.get("Fazenda", "")), self.fazenda)
        self.assertIn("Executores", resumo_dict)
        self.assertIn("Jornada (h/dia)", resumo_dict)
        df_crono = pd.read_excel(caminho, sheet_name="CRONOGRAMA_DETALHADO")
        self.assertFalse(df_crono.empty, "CRONOGRAMA_DETALHADO vazio")
        for col in ("Dia", "Fazenda", "Talhao", "Atividade", "Turma", "HH"):
            self.assertIn(col, df_crono.columns, f"Coluna '{col}' ausente no cronograma")
        self.assertTrue(
            (df_crono["HH"] > 0).any(), "Nenhum HH positivo no cronograma"
        )
        dias = df_crono["Dia"].dropna().unique()
        self.assertGreater(len(dias), 0, "Nenhum dia agendado")

    def test_batch_9ops_5_6h_schedule_params(self):
        r = self._run_batch(jornada=5.6, operarios=9)
        self.assertIsNotNone(r)
        self.assertEqual(r["fazenda"], self.fazenda)
        self.assertGreater(r["total_hh"], 0, "total_hh deve ser > 0")
        self.assertGreater(len(r["cronograma"]), 0, "cronograma vazio")
        crono = r["cronograma"]
        turmas_snap = {t["nome"]: t["operarios"] for t in r["turmas_snapshot"]}
        self.assertIn("SVG_001", turmas_snap)
        self.assertEqual(turmas_snap["SVG_001"], 9)

    def test_batch_xlsx_hh_matches_cronograma(self):
        r = self._run_batch(jornada=5.6, operarios=9)
        self.assertIsNotNone(r)
        xlsx_files = self._find_xlsx()
        self.assertGreaterEqual(len(xlsx_files), 1)
        df_crono = pd.read_excel(xlsx_files[-1], sheet_name="CRONOGRAMA_DETALHADO")
        hh_xlsx = float(df_crono["HH"].sum())
        hh_crono = sum(float(c["HH"]) for c in r["cronograma"])
        self.assertAlmostEqual(
            hh_xlsx, hh_crono, delta=0.5,
            msg=f"HH xlsx={hh_xlsx:.1f} != cronograma={hh_crono:.1f}"
        )

    def test_batch_xlsx_dia_within_prazo(self):
        r = self._run_batch(jornada=5.6, operarios=9)
        self.assertIsNotNone(r)
        dias_uteis_meta = r.get("dias_simulado", 0)
        prazo_meses = 6.0
        dias_prazo_aprox = prazo_meses * 22
        self.assertLessEqual(
            dias_uteis_meta,
            dias_prazo_aprox * 2,
            f"Simulacao usou {dias_uteis_meta} dias, muito alem do prazo de ~{dias_prazo_aprox} dias uteis"
        )


class TestE2EBatchMultipleTeams(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cfg = carregar_config()
        cls._orcamento_backup = cfg.get("orcamento_estrito", True)
        cfg["orcamento_estrito"] = False
        xlsx_path = _FORMOSA_XLSX
        if not os.path.exists(xlsx_path):
            raise unittest.SkipTest(f"Planilha nao encontrada: {xlsx_path}")
        df = carregar_planilha_microplanejamento(cfg, caminho=xlsx_path, modo_auto=True)
        if df is None or df.empty:
            raise unittest.SkipTest("carregar_planilha_microplanejamento retornou None/vazio")
        cls.cfg = cfg
        cls.df = df
        cls.fazenda = "FORMOSA"
        cls.atividades_catalogo = sorted(
            {str(x).strip() for x in df["atividade"].dropna().unique() if str(x).strip()}
        )
        cls._output_backup = OUTPUT_DIR

    @classmethod
    def tearDownClass(cls):
        cls.cfg["orcamento_estrito"] = cls._orcamento_backup

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="srf_e2e_multi_")
        import src.atm.orca.scheduler_core as _sc
        _sc.OUTPUT_DIR = self._tmpdir

    def tearDown(self):
        import src.atm.orca.scheduler_core as _sc
        _sc.OUTPUT_DIR = self._output_backup
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_batch_two_teams(self):
        df_faz = self.df[self.df["fazenda"] == self.fazenda].copy()
        ctx = {
            "modo_seq": "implantacao",
            "usar_bloqueio_global": True,
            "usar_reforco_automatico": True,
            "usar_pool_pos_bloqueio": True,
            "prazo_meses": 6.0,
            "mes_ref": 1,
            "ano_ref": 2026,
            "jornada": 5.6,
            "executores": 9,
            "turmas": [
                {"nome": "Rocadores", "operarios": 5, "atividades": "todas"},
                {"nome": "Geral", "operarios": 4, "atividades": "todas"},
            ],
            "penalidade": 1.0,
            "preencher_orfas_template": False,
        }
        r = calcular_cronograma_inteligente(
            self.cfg,
            df_faz,
            self.fazenda,
            esperar_enter=False,
            ctx=ctx,
            atividades_catalogo=self.atividades_catalogo,
        )
        self.assertIsNotNone(r)
        self.assertGreater(len(r["cronograma"]), 0)
        turma_names = {t["nome"] for t in r["turmas_snapshot"]}
        self.assertIn("Rocadores", turma_names)
        self.assertIn("Geral", turma_names)


if __name__ == "__main__":
    unittest.main()
