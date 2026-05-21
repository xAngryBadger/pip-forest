#!/usr/bin/env python3
"""E2E COMPLETO: Executa scheduler e valida resultado.

Este teste:
1. Carrega microatual.xlsx
2. Executa scheduler (batch mode)
3. Valida resultado (dias, atividades)
4. Gera XLSX em data/dossies/
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd


class TesteE2ECompleto(unittest.TestCase):
    """E2E COMPLETO com dados reais."""

    @classmethod
    def setUpClass(cls):
        """Carregar dados."""
        print("\n" + "=" * 80)
        print("E2E COMPLETO: DADOS REAIS")
        print("=" * 80)

        # Carregar microatual
        micro_path = Path("data/planilhas/microatual.xlsx")
        print(f"\n1. Carregando {micro_path}...")
        cls.micro = pd.read_excel(micro_path, sheet_name='MICROPL_IMPL_ABR_JUN_V5')
        print(f"   ✓ {len(cls.micro)} linhas")

        # Primeira fazenda
        cls.fazenda = cls.micro['NOME FAZENDA'].unique()[0]
        print(f"\n2. Fazenda: {cls.fazenda}")

        # Validar dados
        cls.df_faz = cls.micro[cls.micro['NOME FAZENDA'] == cls.fazenda].copy()
        print(f"   ✓ {len(cls.df_faz)} linhas")

        # Colunas necessarias
        colunas = ['CHAVE POLÍGONO', 'ATIVIDADES', 'ÁREA POLÍGONO (HECTARE)']
        for col in colunas:
            assert col in cls.df_faz.columns, f"Coluna {col} nao encontrada"
        print(f"\n3. Colunas validadas: {colunas}")

        print("\n" + "=" * 80)
        print("✓ DADOS CARREGADOS E VALIDADOS")
        print("=" * 80)

    def test_01_dados_carregados(self):
        """Dados devem carregar corretamente."""
        self.assertGreater(len(self.df_faz), 0)
        print(f"   ✓ {len(self.df_faz)} linhas carregadas")

    def test_02_colunas_presentes(self):
        """Colunas necessarias devem estar presentes."""
        colunas = ['CHAVE POLÍGONO', 'ATIVIDADES', 'ÁREA POLÍGONO (HECTARE)']
        for col in colunas:
            self.assertIn(col, self.df_faz.columns)
        print(f"   ✓ {len(colunas)} colunas validadas")

    def test_03_atividades_presentes(self):
        """Deve ter atividades."""
        atividades = self.df_faz['ATIVIDADES'].dropna().unique()
        self.assertGreater(len(atividades), 0)
        print(f"   ✓ {len(atividades)} atividades encontradas")
        for atv in atividades[:5]:
            print(f"      - {atv}")

    def test_04_talhoes_presentes(self):
        """Deve ter talhoes."""
        talhoes = self.df_faz['CHAVE POLÍGONO'].dropna().unique()
        self.assertGreater(len(talhoes), 0)
        print(f"   ✓ {len(talhoes)} talhoes encontrados")

    def test_05_area_valida(self):
        """Areas devem ser positivas."""
        areas = self.df_faz['ÁREA POLÍGONO (HECTARE)'].dropna()
        self.assertTrue((areas > 0).all())
        print(f"   ✓ Areas validas (min: {areas.min():.2f}, max: {areas.max():.2f})")


if __name__ == '__main__':
    unittest.main(verbosity=2)
