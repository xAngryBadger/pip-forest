#!/usr/bin/env python3
"""Teste mínimo para debug do scheduler bug."""
import sys
sys.path.insert(0, '.')

from src.atm.srf.config import carregar_config
from src.atm.srf.io import carregar_planilha_microplanejamento
from src.atm.srf.scheduler_core import calcular_cronograma_inteligente

def test_scheduler():
    cfg = carregar_config()
    cfg['orcamento_estrito'] = False
    
    df = carregar_planilha_microplanejamento(cfg, caminho='data/planilhas/formosa.xlsx', modo_auto=True)
    df_faz = df[df['fazenda'] == 'FORMOSA'].copy()
    
    atividades_catalogo = sorted({str(x).strip() for x in df['atividade'].dropna().unique() if str(x).strip()})
    
    ctx = {
        'modo_seq': 'implantacao', 
        'usar_bloqueio_global': True, 
        'usar_reforco_automatico': True,
        'usar_pool_pos_bloqueio': False, 
        'prazo_meses': 6.0, 
        'mes_ref': 1, 
        'ano_ref': 2026,
        'jornada': 5.6, 
        'executores': 9, 
        'turmas': [{'nome': 'SVG_001', 'operarios': 9, 'atividades': 'todas'}],
        'penalidade': 1.0, 
        'preencher_orfas_template': False,
    }
    
    r = calcular_cronograma_inteligente(cfg, df_faz, 'FORMOSA', esperar_enter=False, ctx=ctx, atividades_catalogo=atividades_catalogo)
    crono = r.get('cronograma', [])
    
    total_hh = sum(c["HH"] for c in crono)
    dias = r.get("dias_simulado")
    
    print(f"\n{'='*60}")
    print(f"RESULTADO: {len(crono)} entries, {dias} dias, {total_hh:.2f} HH")
    print(f"{'='*60}")
    
    # Critérios de sucesso
    success = True
    if len(crono) < 100:
        print(f"❌ FAIL: Esperado >100 entries, got {len(crono)}")
        success = False
    if total_hh < 1000:
        print(f"❌ FAIL: Esperado >1000 HH, got {total_hh:.2f}")
        success = False
    if dias < 10:
        print(f"❌ FAIL: Esperado >10 dias, got {dias}")
        success = False
    
    if success:
        print("✅ PASS: Scheduler funcionando corretamente")
    
    return success

if __name__ == '__main__':
    success = test_scheduler()
    sys.exit(0 if success else 1)
