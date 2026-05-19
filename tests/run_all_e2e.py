#!/usr/bin/env python3
"""Executar todos os testes E2E permanentes.

Uso:
    python3 tests/run_all_e2e.py

Saída:
    - Relatório detalhado de cada teste
    - Status: Aprovado/Reprovado
    - Tempo de execução
"""

import unittest
import sys
import time
from pathlib import Path

# Adicionar path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_e2e_permanente import (
    TesteValidacaoDados,
    TesteCascataGlobal,
    TesteTimeUnico,
    TesteDoisTimes,
    TesteBloqueioGlobal,
    TesteMultiplasFazendas
)


def format_time(seconds):
    """Formatar segundos para MM:SS."""
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes}:{seconds:02d}"


def run_tests():
    """Executar todos os testes E2E."""
    print("=" * 80)
    print("TESTES E2E PERMANENTES - SRF CLI")
    print("=" * 80)
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    
    # Configurar loader
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Adicionar testes na ordem
    print("Carregando testes...")
    suite.addTests(loader.loadTestsFromTestCase(TesteValidacaoDados))
    print("  ✓ Validação de dados")
    
    suite.addTests(loader.loadTestsFromTestCase(TesteCascataGlobal))
    print("  ✓ Cascata GLOBAL")
    
    suite.addTests(loader.loadTestsFromTestCase(TesteTimeUnico))
    print("  ✓ Time único")
    
    suite.addTests(loader.loadTestsFromTestCase(TesteDoisTimes))
    print("  ✓ Dois times")
    
    suite.addTests(loader.loadTestsFromTestCase(TesteBloqueioGlobal))
    print("  ✓ Bloqueio global")
    
    suite.addTests(loader.loadTestsFromTestCase(TesteMultiplasFazendas))
    print("  ✓ Múltiplas fazendas")
    
    print()
    print("Executando testes...")
    print("-" * 80)
    
    # Executar
    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    elapsed_time = time.time() - start_time
    
    # Relatório
    print()
    print("=" * 80)
    print("RELATÓRIO DE TESTES E2E")
    print("=" * 80)
    print(f"Total de testes: {result.testsRun}")
    print(f"Aprovados: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Falhas: {len(result.failures)}")
    print(f"Erros: {len(result.errors)}")
    print(f"Tempo: {format_time(elapsed_time)}")
    print()
    
    # Detalhes de falhas
    if result.failures:
        print("FALHAS:")
        for test, traceback in result.failures:
            print(f"  ✗ {test}")
            print(f"    {traceback[:200]}...")
        print()
    
    # Detalhes de erros
    if result.errors:
        print("ERROS:")
        for test, traceback in result.errors:
            print(f"  ✗ {test}")
            print(f"    {traceback[:200]}...")
        print()
    
    # Status final
    print("=" * 80)
    if result.wasSuccessful():
        print("✅ TODOS OS TESTES APROVADOS!")
    else:
        print("❌ ALGUNS TESTES FALHARAM")
    print("=" * 80)
    
    # Exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    from datetime import datetime
    sys.exit(run_tests())
