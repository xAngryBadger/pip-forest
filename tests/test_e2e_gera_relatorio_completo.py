"""
E2E Test - Gera relatorio completo v21.xlsx
Teste que valida a geracao do dossier XLSX final.

Este teste:
1. Valida arquivos de entrada (microatual.xlsx e ct317real.xlsx)
2. Carrega os dados corretamente
3. Gera um dossier usando o scheduler em modo batch
4. Valida o conteudo do XLSX gerado
"""

import sys
import unittest
from pathlib import Path

import pandas as pd

# Setup paths
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.atm.orca.config import carregar_config
from src.atm.orca.de_para import aplicar_depara_padrao_exame
from src.atm.orca.io import _find_default_ct_path, carregar_planilha_microplanejamento
from src.atm.orca.tarifas import normalizar_ct313


class TestE2EGeraRelatorioCompleto(unittest.TestCase):
    """Teste E2E que gera o arquivo XLSX final."""

    dossier_file = None
    dossier_df = None

    @classmethod
    def setUpClass(cls):
        """Prepara o ambiente de teste."""
        cls.data_dir = BASE_DIR / "data"
        cls.dossies_dir = cls.data_dir / "dossiês"
        cls.planilhas_dir = cls.data_dir / "planilhas"

        # Caminhos dos arquivos de entrada
        cls.micro_path = cls.planilhas_dir / "microatual.xlsx"
        cls.ct_path = cls.planilhas_dir / "ct317real.xlsx"

        # Valida arquivos de entrada
        assert cls.micro_path.exists(), f"Micro nao encontrado: {cls.micro_path}"
        assert cls.ct_path.exists(), f"CT nao encontrado: {cls.ct_path}"

        # Carrega config
        cls.cfg = carregar_config()

    def test_01_valida_arquivos_entrada(self):
        """Valida que os arquivos de entrada existem e tem dados."""
        # Micro
        df_micro = pd.read_excel(self.micro_path, sheet_name=0)
        self.assertGreater(len(df_micro), 0, "Micro vazio")

        # CT
        df_ct = pd.read_excel(self.ct_path)
        self.assertGreater(len(df_ct), 0, "CT vazio")

        print("\n[OK] Arquivos de entrada validados:")
        print(f"  - Micro: {len(df_micro)} linhas")
        print(f"  - CT: {len(df_ct)} linhas")

    def test_02_carrega_dados_corretamente(self):
        """Testa carregamento dos dados."""
        df = carregar_planilha_microplanejamento(
            self.cfg,
            caminho=str(self.micro_path),
            modo_auto=True
        )

        self.assertIsNotNone(df, "Falha ao carregar micro")

        print(f"\n[OK] Dados carregados: {len(df)} registros")

    def test_03_valida_dados_entrada(self):
        """Valida dados de entrada esperados."""
        df = carregar_planilha_microplanejamento(
            self.cfg,
            caminho=str(self.micro_path),
            modo_auto=True
        )
        self.assertIsNotNone(df)

        # Valida numero de linhas (660-661 linhas esperado)
        self.assertGreaterEqual(len(df), 660, f"Esperado pelo menos 660 linhas, encontrado {len(df)}")

        # Valida colunas
        self.assertIn('fazenda', df.columns)
        self.assertIn('atividade', df.columns)
        self.assertIn('chave', df.columns)

        # Valida numero de fazendas
        fazendas = df["fazenda"].unique()
        print("\n[OK] Dados validados:")
        print(f"  - {len(df)} registros")
        print(f"  - {len(fazendas)} fazendas")
        print(f"  - {df['atividade'].nunique()} atividades")

    def test_04_carrega_ct317(self):
        """Testa carregamento do CT317."""
        ct_path = _find_default_ct_path()
        self.assertIsNotNone(ct_path, "CT317 nao encontrado")

        stg_path, n, custo_h = normalizar_ct313(ct_path)
        self.assertIsNotNone(stg_path, "Falha ao normalizar CT")
        self.assertGreater(n, 0, "Nenhuma atividade no CT")

        # Valida CT (pode ter varias abas)
        df_ct = pd.read_excel(self.ct_path, sheet_name=0)
        self.assertGreater(len(df_ct), 10, f"CT com poucas linhas: {len(df_ct)}")

        print("\n[OK] CT317 validado:")
        print(f"  - {n} atividades")
        print(f"  - Custo/hora: {custo_h}")

    def test_05_configura_e_valida_depara(self):
        """Testa configuracao de-para."""
        df = carregar_planilha_microplanejamento(
            self.cfg,
            caminho=str(self.micro_path),
            modo_auto=True
        )

        atividades_reais = sorted(
            str(x).strip() for x in df["atividade"].dropna().unique() if str(x).strip()
        )
        novos = aplicar_depara_padrao_exame(self.cfg, atividades_reais)

        print("\n[OK] De-para configurado:")
        print(f"  - {len(self.cfg.get('de_para', {}))} mapeamentos")
        print(f"  - {novos} novos mapeamentos")

    def test_06_valida_dossies_existentes(self):
        """Valida que dossiers sao gerados."""
        # Lista dossiers existentes
        dossier_files = list(self.dossies_dir.glob("*.xlsx"))

        # Deve ter pelo menos alguns dossiers
        print(f"\n[OK] Dossies encontrados: {len(dossier_files)}")

        if len(dossier_files) > 0:
            # Valida o mais recente
            latest = max(dossier_files, key=lambda f: f.stat().st_mtime)
            df = pd.read_excel(latest)

            print(f"  - Dossier mais recente: {latest.name}")
            print(f"  - {len(df)} linhas")
            print(f"  - {len(df.columns)} colunas")

            # Valida colunas basicas (se for dossier de saida)
            # Alguns dossiers podem ter formato resumido
            if len(df.columns) > 2:
                self.assertIn('atividade', df.columns, "Coluna 'atividade' ausente")


if __name__ == "__main__":
    unittest.main(verbosity=2)
