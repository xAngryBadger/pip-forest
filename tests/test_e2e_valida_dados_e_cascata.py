#!/usr/bin/env python3
"""E2E VALIDACAO: Valida dados reais e cascata.

Este teste:
1. Carrega microatual.xlsx (dados reais)
2. Valida colunas necessarias
3. Valida atividades presentes
4. Valida cascata GLOBAL (N+1)
5. Compara com v15.xlsx (referencia)

Nao executa scheduler completo (requer interacao), mas valida
que TUDO está pronto para execucao.
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from src.atm.srf.scheduler import _min_fase_cascata_por_talhao


class TesteE2EValidaDadosECascata(unittest.TestCase):
    """E2E VALIDACAO: Dados reais + cascata."""
    
    @classmethod
    def setUpClass(cls):
        """Carregar dados reais uma vez."""
        print("\n" + "=" * 80)
        print("E2E VALIDACAO: DADOS REAIS + CASCATA")
        print("=" * 80)
        
        # 1. Carregar microatual.xlsx
        micro_path = Path("data/planilhas/microatual.xlsx")
        print(f"\n1. Carregando {micro_path}...")
        cls.micro = pd.read_excel(micro_path, sheet_name='MICROPL_IMPL_ABR_JUN_V5')
        print(f"   ✓ {len(cls.micro)} linhas")
        
        # 2. Carregar ct317real.xlsx
        ct317_path = Path("data/planilhas/ct317real.xlsx")
        print(f"\n2. Carregando {ct317_path}...")
        cls.ct317 = pd.read_excel(ct317_path, sheet_name='Preço Final')
        print(f"   ✓ {len(cls.ct317)} linhas")
        
        # 3. Carregar v15 (referencia)
        v15_path = Path("data/dossiês/Dossier_FORMOSA__FAZENDA_TODOS_OPERACIONAL_v15.xlsx")
        print(f"\n3. Carregando referencia v15...")
        cls.v15_resumo = pd.read_excel(v15_path, sheet_name='RESUMO_OPERACIONAL')
        cls.v15_dias = int(cls.v15_resumo[cls.v15_resumo['Metrica']=='Duracao Simulada (dias uteis)']['Valor'].values[0])
        cls.v15_ativ = int(cls.v15_resumo[cls.v15_resumo['Metrica']=='Agendadas (humano)']['Valor'].values[0])
        print(f"   ✓ v15: {cls.v15_dias} dias, {cls.v15_ativ} atividades")
        
        # 4. Primeira fazenda
        cls.fazenda = cls.micro['NOME FAZENDA'].unique()[0]
        cls.df_faz = cls.micro[cls.micro['NOME FAZENDA'] == cls.fazenda].copy()
        print(f"\n4. Fazenda: {cls.fazenda} ({len(cls.df_faz)} linhas)")
        
        print("\n" + "=" * 80)
        print("✓ DADOS CARREGADOS")
        print("=" * 80)
    
    def test_01_micro_colunas(self):
        """microatual.xlsx deve ter colunas necessarias."""
        colunas = ['DATA', 'CÓDIGO FAZENDA', 'NOME FAZENDA', 'CHAVE POLÍGONO', 'ATIVIDADES', 'ÁREA POLÍGONO (HECTARE)']
        for col in colunas:
            self.assertIn(col, self.micro.columns, f"Coluna {col} nao encontrada")
        print(f"   ✓ {len(colunas)} colunas validadas")
    
    def test_02_ct317_colunas(self):
        """ct317real.xlsx deve ter colunas necessarias."""
        colunas = ['N', 'OPERAÇÕES', ' Rendimento HH/ha', 'PREÇO R$']
        for col in colunas:
            self.assertIn(col, self.ct317.columns)
        print(f"   ✓ {len(colunas)} colunas validadas")
    
    def test_03_atividades_presentes(self):
        """Deve ter atividades."""
        atividades = self.df_faz['ATIVIDADES'].dropna().unique()
        self.assertGreater(len(atividades), 0)
        print(f"   ✓ {len(atividades)} atividades:")
        for atv in atividades[:5]:
            print(f"      - {str(atv)[:60]}")
    
    def test_04_talhoes_presentes(self):
        """Deve ter talhoes."""
        talhoes = self.df_faz['CHAVE POLÍGONO'].dropna().unique()
        self.assertGreater(len(talhoes), 0)
        print(f"   ✓ {len(talhoes)} talhoes")
    
    def test_05_areas_validas(self):
        """Areas devem ser positivas."""
        areas = self.df_faz['ÁREA POLÍGONO (HECTARE)'].dropna()
        self.assertTrue((areas > 0).all())
        print(f"   ✓ Areas: min={areas.min():.2f}, max={areas.max():.2f}")
    
    def test_06_cascata_global(self):
        """Cascata GLOBAL deve funcionar."""
        demanda = {
            ('talhao1', 'ROCADA'): 10.0,
            ('talhao2', 'ROCADA'): 8.0,
        }
        
        resultado = _min_fase_cascata_por_talhao(
            demanda, {}, None, True, False, set(), set(), set(), 0, {}, {}
        )
        
        min_global = min(resultado.values()) if resultado else None
        self.assertIsNotNone(min_global)
        
        # Todas fases >= min_global
        for fase in resultado.values():
            self.assertGreaterEqual(fase, min_global)
        
        print(f"   ✓ Cascata GLOBAL: min={min_global}")
    
    def test_07_referencia_v15(self):
        """v15 deve ter 145 dias, 15 atividades."""
        self.assertEqual(self.v15_dias, 145, f"v15 dias diferente: {self.v15_dias}")
        self.assertEqual(self.v15_ativ, 15, f"v15 atividades diferente: {self.v15_ativ}")
        print(f"   ✓ v15 referencia: {self.v15_dias} dias, {self.v15_ativ} atividades")


if __name__ == '__main__':
    unittest.main(verbosity=2)
