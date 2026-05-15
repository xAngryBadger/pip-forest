"""De-para — auto-mapping e aplicacao de mapeamento padrao EXAME->CT317."""

from .config import salvar_config
from .constants import DEFAULT_DEPARA_EXAME_CT317
from .text_utils import normalizar_chave, _candidatos_chave_atividade

_SUFFIX_MARKERS = ("impl", "madap", "manut", "appn", "manl")


def _strip_micro_suffix(normalized):
    if not normalized:
        return normalized
    lowest = len(normalized)
    for m in _SUFFIX_MARKERS:
        idx = normalized.find(m)
        if 0 < idx < lowest:
            lowest = idx
    if lowest < len(normalized):
        return normalized[:lowest].strip()
    return normalized


def _depara_heuristico_ct317(kn, tarifas):
    if not kn or not tarifas:
        return None

    def pick(*names):
        for n in names:
            if n in tarifas:
                return n
        return None

    if "controle" in kn and "formiga" in kn:
        return pick(
            "COMBATE À FORMIGAS Impl. PL APP/ RL",
            "COMBATE À FORMIGAS Impl. CD APP/RL",
            "COMBATE À FORMIGAS MAdap. APP/RL",
            "COMBATE À FORMIGAS Manut. APP/RL",
            "COMBATE A FORMIGAS Impl. PL APP/ RL",
            "COMBATE A FORMIGAS Impl. CD APP/RL",
        )
    if "combate" in kn and "formiga" in kn:
        return pick(
            "COMBATE À FORMIGAS Impl. PL APP/ RL",
            "COMBATE À FORMIGAS Impl. CD APP/RL",
            "COMBATE À FORMIGAS MAdap. APP/RL",
            "COMBATE À FORMIGAS Manut. APP/RL",
            "COMBATE A FORMIGAS Impl. PL APP/ RL",
            "COMBATE A FORMIGAS Impl. CD APP/RL",
        )
    if "aplicacao" in kn and ("herbicida" in kn or "quim" in kn):
        return pick(
            "CAPINA QUÍM MAN TOTAL Manut. APP/RL",
            "CAPINA QUÍM MAN TOTAL MAdap. APP/RL",
            "LIMPEZA DE ÁREA QUIM. MAN APP/RL",
        )
    if "implantacao" in kn and "mecaniz" in kn:
        return pick(
            "PREPARO DE SOLO MEC C/ ADUB APP/RL",
            "PREPARO DE SOLO MEC C/ GRADE APP/RL",
            "PREPARO DE SOLO MEC S/ ADUB APP/RL",
        )
    if "preparo" in kn and "solo" in kn and ("mec" in kn or "mecaniz" in kn):
        return pick(
            "PREPARO DE SOLO MEC C/ ADUB APP/RL",
            "PREPARO DE SOLO MEC C/ GRADE APP/RL",
            "PREPARO DE SOLO MEC S/ ADUB APP/RL",
            "PREPARO SOLO MEC CABEC COV C/ADUB APP/RL",
        )
    if "suprimento" in kn and "muda" in kn:
        return pick("PLANTIO MANUAL APP/RL")
    if "adubacao" in kn and "quim" in kn and "cobertura" in kn:
        return pick("ADUBAÇÃO QUÍM MAN 3 MESES APP/RL")
    if "adubacao" in kn and ("quim" in kn or "quimica" in kn):
        return pick(
            "ADUBAÇÃO QUÍM MAN DE BASE Impl. PL - APP/ RL",
            "ADUBAÇÃO QUÍM MAN DE BASE Impl.PL-APP/RL",
            "ADUBAÇÃO QUÍM MAN DE BASE MAdap. APP/RL",
        )
    if "plantio" in kn and "manual" in kn:
        return pick("PLANTIO MANUAL APP/RL")
    if "replantio" in kn and "manual" in kn:
        return pick("REPLANTIO APP/RL I")
    if "rocada" in kn and "manual" in kn:
        return pick("ROÇADA MANUAL Impl. PL APP/RL I", "ROÇADA MANUAL Impl. CD APP/RL I")
    if "capina" in kn:
        if "quim" in kn or "quimica" in kn:
            return pick(
                "CAPINA QUÍM MAN TOTAL Manut. APP/RL",
                "CAPINA QUÍM MAN TOTAL MAdap. APP/RL",
            )
        return pick("CAPINA MANUAL COROA Impl. PL - APP/ RL I")
    if "irrigacao" in kn:
        return pick(
            "IRRIGAÇÃO INICIAL MAN Impl. PL - APP/ RL",
            "IRRIGAÇÃO INICIAL MAN APP/RL",
        )
    if "limpeza" in kn and "area" in kn:
        if "quim" in kn or "quimica" in kn:
            return pick(
                "LIMPEZA DE ÁREA QUIM. MAN APP/RL",
                "LIMPEZA DE AREA QUIM. MAN APP/RL",
            )
        return pick("ROÇADA MANUAL Impl. PL APP/RL I")
    if "eliminacao" in kn and "exotica" in kn:
        return pick(
            "ELIMINAÇÃO DE EXÓTICAS Impl. PL - APP/RL",
            "ELIMINAÇÃO DE EXÓTICAS Impl. CD - APP/RL",
        )
    if "coveamento" in kn or "coveam" in kn:
        return pick(
            "COVEAMENTO - MOTOCOVEADOR PL APP/RL",
            "COVEAM ÁREA NÃO SUBSOL Impl. PL APP/ RL",
        )
    if "nucleacao" in kn:
        return pick("NUCLEAÇÃO EM FAIXAS APP/RL")
    if "conducao" in kn and "regeneracao" in kn:
        return pick("CONDUÇÃO DE REGENERAÇÃO")
    if "controle" in kn and "invasora" in kn:
        return pick("CONTROLE DE INVASORAS APP/RL I")
    return None


def _root_match_tarifas(atv_norm, tarifas):
    root = _strip_micro_suffix(atv_norm)
    if not root or len(root) < 5:
        return None
    root_len = len(root)
    best = None
    best_score = 0
    for tk in tarifas:
        tn = normalizar_chave(tk)
        t_root = _strip_micro_suffix(tn)
        if t_root == root:
            return tk
        if root in t_root or t_root in root:
            score = min(root_len, len(t_root))
            if score > best_score:
                best_score = score
                best = tk
    return best


def auto_mapear_de_para(cfg, atividades_reais):
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
            alvo = _depara_heuristico_ct317(kn, tarifas)
            if alvo:
                break
        if not alvo:
            alvo = _root_match_tarifas(normalizar_chave(atv), tarifas)
        if alvo and alvo in tarifas and de_para.get(atv) != alvo:
            de_para[atv] = alvo
            novo += 1
    if novo:
        salvar_config(cfg)
    return novo
