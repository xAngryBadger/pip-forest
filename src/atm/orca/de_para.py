"""De-para — auto-mapping e aplicacao de mapeamento padrao EXAME->CT317."""

from .config import salvar_config
from .constants import DEFAULT_DEPARA_EXAME_CT317
from .text_utils import _candidatos_chave_atividade, normalizar_chave


def auto_mapear_de_para(cfg, atividades_reais):
    """
    Mapeia automaticamente atividades do micro para chaves de tarifa por similaridade textual.
    Usa normalizar_chave para comparacao robusta.
    """
    tarifas = cfg.get("tarifas", {})
    if not tarifas:
        return 0
    de_para = cfg.setdefault("de_para", {})
    tarif_norm = {k: normalizar_chave(k) for k in tarifas.keys()}
    novos = 0
    for atv in atividades_reais:
        if atv in de_para:
            continue
        cands = _candidatos_chave_atividade(atv)
        an = cands[-1] if cands else normalizar_chave(atv)
        melhor = None
        melhor_score = 0
        for tk, tn in tarif_norm.items():
            score = 0
            if an == tn:
                score = 1000
            elif an in tn or tn in an:
                score = min(len(an), len(tn))
            else:
                toks_a = set(x for x in an.split() if len(x) > 2)
                toks_t = set(x for x in tn.split() if len(x) > 2)
                inter = len(toks_a & toks_t)
                if inter >= 3:
                    score = inter
            if score > melhor_score:
                melhor_score = score
                melhor = tk
        if melhor and melhor_score >= 3:
            de_para[atv] = melhor
            novos += 1
    if novos > 0:
        salvar_config(cfg)
    return novos

def aplicar_depara_padrao_exame(cfg, atividades_reais):
    """
    Aplica mapeamento fixo (hardcoded) do prototipo EXAME->CT_317.
    1) Dicionario exato por normalizar_chave; 2) heuristica por palavras-chave (APPN, parenteses, etc.).
    """
    tarifas = cfg.get("tarifas", {})
    if not tarifas:
        return 0
    de_para = cfg.setdefault("de_para", {})
    novo = 0
    for atv in atividades_reais:
        alvo = None
        for kn in _candidatos_chave_atividade(atv):
            if kn in DEFAULT_DEPARA_EXAME_CT317:
                alvo = DEFAULT_DEPARA_EXAME_CT317[kn]
                break
        if alvo and alvo in tarifas and de_para.get(atv) != alvo:
            de_para[atv] = alvo
            novo += 1
    if novo:
        salvar_config(cfg)
    return novo

