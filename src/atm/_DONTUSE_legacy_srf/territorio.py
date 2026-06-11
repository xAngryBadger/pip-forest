"""Territorio — validacao de fazendas CT vs microplanejamento."""

from .config import salvar_config
from .ui import sub, aviso, ok, prompt, confirmar, selecionar_paginado, G, C, Y, DM, RS, esperar
from .text_utils import normalizar_chave
from .ui import subcabecalho
from .context import dashboard_header

def _indice_fazendas_ct(cfg):
    """Chave normalizada -> nome canonico (ultimo da lista)."""
    d = {}
    for x in cfg.get("fazendas_ct") or []:
        s = str(x).strip()
        if not s:
            continue
        k = normalizar_chave(s)
        if k:
            d[k] = s
    return d

def micro_fazendas_ausentes_na_lista_ct(cfg, df):
    """
    Fazendas que aparecem no micro mas nao em config.fazendas_ct (comparacao por normalizar_chave).
    Se fazendas_ct vazia, retorna None (validacao desativada).
    """
    idx = _indice_fazendas_ct(cfg)
    if not idx:
        return None
    out = []
    for m in fazendas_unicas_micro(df):
        if normalizar_chave(m) not in idx:
            out.append(m)
    return out

def aviso_fazendas_micro_sem_cadastro_ct(cfg, df):
    """Aviso no startup / apos recarregar micro."""
    falta = micro_fazendas_ausentes_na_lista_ct(cfg, df)
    if falta is None:
        sub()
        print(
            DM + "  [Fazendas vs CT] Lista `fazendas_ct` vazia no config — "
            "cadastre em menu [6] as fazendas cobertas pelo orcamento CT (ex.: todas menos Ulianopolis)."
            + RS
        )
        return
    if not falta:
        return
    sub()
    print(
        Y
        + "  !  Fazendas no MICRO sem correspondencia na lista `fazendas_ct` (orcamento CT): "
        + RS
    )
    for x in falta:
        print(Y + f"      - {str(x)[:72]}" + RS)
    print(
        DM
        + "  Corrija o CT no escritorio ou adicione excecao em [6] se a fazenda estiver coberta."
        + RS
    )

def modulo_validar_fazendas_ct(cfg, df):
    """
    CRUD de `fazendas_ct`: nomes de fazenda que o orcamento CT considera cadastrados.
    O micro pode ter fazendas a mais (esquecimento no CT) — o scan compara por nome normalizado.
    """
    while True:
        dashboard_header()
        subcabecalho("FAZENDAS — micro vs lista CT (orcamento)")
        micro_list = fazendas_unicas_micro(df)
        ct_list = list(cfg.get("fazendas_ct") or [])
        idx = _indice_fazendas_ct(cfg)
        print(G + f"  No micro agora: {len(micro_list)} fazenda(s)" + RS)
        print(G + f"  Na lista fazendas_ct: {len(ct_list)}" + RS)
        falta = micro_fazendas_ausentes_na_lista_ct(cfg, df)
        if falta is None:
            print(Y + "  Lista CT vazia — nenhuma comparacao possivel." + RS)
        elif falta:
            print(Y + f"  Ausentes na lista CT ({len(falta)}):" + RS)
            for x in falta[:25]:
                print(Y + f"    - {str(x)[:68]}" + RS)
            if len(falta) > 25:
                print(DM + f"    ... +{len(falta) - 25}" + RS)
        else:
            ok("  Todas as fazendas do micro constam em fazendas_ct.")
        sub()
        print(DM + "  [1] Ver / listar fazendas_ct" + RS)
        print(DM + "  [2] Adicionar uma fazenda a fazendas_ct" + RS)
        print(
            DM
            + "  [3] Importar TODAS as fazendas do micro para fazendas_ct (substitui lista)"
            + RS
        )
        print(DM + "  [4] Remover uma fazenda da lista" + RS)
        print(DM + "  [5] Colar varios nomes (virgula ou ponto-e-virgula)" + RS)
        print(DM + "  [6] Limpar lista (fazendas_ct = [])" + RS)
        print(DM + "  [0] Voltar" + RS)
        op = prompt("Opcao").strip()
        if op == "0":
            return
        if op == "1":
            if not ct_list:
                aviso("Lista vazia.")
            else:
                for i, x in enumerate(ct_list, 1):
                    print(G + f"  {i:2}. " + C + str(x)[:68] + RS)
            esperar()
        elif op == "2":
            nome = prompt("Nome EXATO como no micro ou na CT", "")
            if nome.strip():
                k = normalizar_chave(nome)
                if k in idx:
                    aviso("Ja consta (mesma chave normalizada).")
                else:
                    cfg.setdefault("fazendas_ct", []).append(nome.strip())
                    salvar_config(cfg)
                    ok("Adicionado.")
        elif op == "3":
            if not confirmar(
                "Substituir fazendas_ct pelas "
                f"{len(micro_list)} fazendas unicas do micro? (nao altera a planilha CT .xlsm)",
                default=False,
            ):
                continue
            cfg["fazendas_ct"] = micro_list[:]
            salvar_config(cfg)
            ok(f"fazendas_ct = {len(micro_list)} nomes (copia do micro).")
        elif op == "4":
            if not ct_list:
                aviso("Lista vazia.")
                continue
            idx_r = selecionar_paginado("REMOVER", ct_list, page_size=10)
            if idx_r >= 0:
                cfg["fazendas_ct"].pop(idx_r)
                salvar_config(cfg)
                ok("Removido.")
        elif op == "5":
            txt = prompt("Nomes separados por virgula ou ;", "")
            partes = []
            for chunk in txt.replace(";", ",").split(","):
                s = str(chunk).strip()
                if s:
                    partes.append(s)
            ad = 0
            seen = _indice_fazendas_ct(cfg)
            for s in partes:
                k = normalizar_chave(s)
                if k and k not in seen:
                    cfg.setdefault("fazendas_ct", []).append(s)
                    seen[k] = s
                    ad += 1
            if ad:
                salvar_config(cfg)
                ok(f"+{ad} nome(s) novos.")
            else:
                aviso("Nenhum nome novo.")
        elif op == "6":
            if confirmar("Zerar fazendas_ct?", default=False):
                cfg["fazendas_ct"] = []
                salvar_config(cfg)
                ok("Lista limpa.")
        else:
            aviso("Opcao invalida.")


def fazendas_unicas_micro(df):
    """Nomes unicos da coluna fazenda (micro), ordenados."""
    return sorted(
        {str(x).strip() for x in df["fazenda"].dropna().unique() if str(x).strip()},
        key=lambda s: normalizar_chave(s),
    )

