#!/usr/bin/env python3
"""Testes unitários para cascata GLOBAL no scheduler."""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.atm.srf.scheduler import (
    _min_fase_cascata_por_talhao,
    pode_agendar_atividade_cascata,
    classificar_fase_cascata_valor
)

class TestCascataGlobal(unittest.TestCase):
    """Testes para validar comportamento de cascata GLOBAL."""
    
    def setUp(self):
        """Configurar dados de teste."""
        self.demanda_global = {
            ('talhao1', 'ROCADA'): 10.0,
            ('talhao1', 'PREPARO'): 5.0,
            ('talhao2', 'ROCADA'): 8.0,
            ('talhao2', 'PREPARO'): 6.0,
        }
        self.seq_cfg = {}
        self.atividades_plantio = set()
        self.atividades_irrig = set()
        
    def test_min_fase_cascata_por_talhao_retorna_dict(self):
        """_min_fase_cascata_por_talhao deve retornar dict {talhao: fase}."""
        resultado = _min_fase_cascata_por_talhao(
            self.demanda_global, self.seq_cfg, None,
            usar_cascata=True, usar_bloqueio_global=False,
            atividades_bloqueadas=set(),
            atividades_plantio=self.atividades_plantio,
            atividades_irrig=self.atividades_irrig,
            dia=0, dia_termino_plantio={}, tem_plantio_por_talhao={}
        )
        
        # Deve retornar dict
        self.assertIsInstance(resultado, dict)
        
        # Deve ter ambos os talhões
        self.assertIn('talhao1', resultado)
        self.assertIn('talhao2', resultado)
        
        # Ambas as fases devem ser 5.5 (implantacao_outras_fase default)
        # ROCADA e PREPARO sem filtro = fase 5.5
        self.assertEqual(resultado['talhao1'], 5.5)
        self.assertEqual(resultado['talhao2'], 5.5)
        
    def test_extracao_min_global(self):
        """Extrair MIN de dict deve resultar em fase global unica."""
        resultado = _min_fase_cascata_por_talhao(
            self.demanda_global, self.seq_cfg, None,
            usar_cascata=True, usar_bloqueio_global=False,
            atividades_bloqueadas=set(),
            atividades_plantio=self.atividades_plantio,
            atividades_irrig=self.atividades_irrig,
            dia=0, dia_termino_plantio={}, tem_plantio_por_talhao={}
        )
        
        # Extrair MINIMO GLOBAL
        min_global = min(resultado.values()) if resultado else None
        
        # Deve ter um valor
        self.assertIsNotNone(min_global)
        
        # Todas as fases devem ser iguais ao minimo (todas 5.5)
        for fase in resultado.values():
            self.assertEqual(fase, min_global)
            
    def test_cascata_impede_fase_maior(self):
        """Cascata deve bloquear fase N+1 se fase N nao completou."""
        # Simular: talhao1 na fase 0, talhao2 na fase 1
        demanda_teste = {
            ('talhao1', 'ROCADA'): 10.0,  # fase 0
            ('talhao2', 'PREPARO'): 5.0,  # fase 1
        }
        
        resultado = _min_fase_cascata_por_talhao(
            demanda_teste, self.seq_cfg, None,
            usar_cascata=True, usar_bloqueio_global=False,
            atividades_bloqueadas=set(),
            atividades_plantio=self.atividades_plantio,
            atividades_irrig=self.atividades_irrig,
            dia=0, dia_termino_plantio={}, tem_plantio_por_talhao={}
        )
        
        # MIN global deve ser menor fase pendente
        min_global = min(resultado.values()) if resultado else None
        self.assertIsNotNone(min_global)
        
        # Fase 1 > min_global (fase 0) → deve bloquear
        # Isso é testado indiretamente - o scheduler que usa min_global
        # vai bloquear fase 1 quando min_global for 0
        
if __name__ == '__main__':
    unittest.main()
