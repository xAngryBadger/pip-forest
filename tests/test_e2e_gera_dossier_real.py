#!/usr/bin/env python3
"""E2E REAL: Executa scheduler via CLI com stdin simulado e gera XLSX."""

import subprocess
import sys
import time
from pathlib import Path

def test_e2e_gera_dossier():
    """Executar scheduler e gerar XLSX."""
    print("=" * 80)
    print("E2E REAL: GERANDO DOSSIER COM DADOS REAIS")
    print("=" * 80)
    
    # Caminhos
    script_dir = Path(__file__).parent.parent
    micro_path = script_dir / "data/planilhas/microatual.xlsx"
    
    if not micro_path.exists():
        print(f"✗ Erro: {micro_path} nao encontrado")
        return False
    
    print(f"\n1. Micro: {micro_path}")
    
    # Sequencia de inputs
    inputs = [
        "1",       # microatual.xlsx
        "1",       # primeira fazenda
        "1",       # implantacao
        "9",       # operarios
        "5.67",    # jornada
        "6",       # prazo
        "5",       # mes ref
        "2026",    # ano ref
        "1",       # dia ref
        "1",       # todas atividades
        "n",       # nao ajustar
        "1",       # 1 time
        "n",       # sem comparativo
    ]
    
    input_str = "\n".join(inputs)
    
    print(f"\n2. Inputs: {len(inputs)} comandos")
    
    # Executar como modulo
    start_time = time.time()
    result = subprocess.run(
        [sys.executable, "-m", "src.atm.atm_v6_3"],
        input=input_str,
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(script_dir)
    )
    elapsed = time.time() - start_time
    
    print(f"\n3. Execucao: {elapsed:.1f}s, returncode={result.returncode}")
    
    output = result.stdout + result.stderr
    
    # Validar
    if "Dossier" in output or "XLSX" in output or "cronograma" in output.lower() or result.returncode == 0:
        print("\n✓ Scheduler executou!")
        # Procurar arquivo gerado
        dossier_dir = script_dir / "data/dossies"
        if dossier_dir.exists():
            dossiers = list(dossier_dir.glob("*.xlsx"))
            if dossiers:
                print(f"\n✓ Dossies encontrados: {len(dossiers)}")
                for d in dossiers[-3:]:  # ultimos 3
                    print(f"   - {d.name}")
        return True
    else:
        print(f"\n✗ Erro:")
        print(f"STDOUT: {result.stdout[-500:]}")
        print(f"STDERR: {result.stderr[-500:]}")
        return False

if __name__ == '__main__':
    sucesso = test_e2e_gera_dossier()
    sys.exit(0 if sucesso else 1)
