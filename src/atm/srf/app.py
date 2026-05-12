"""Application layer — menu flows, farm selection, scope adjustment, path utilities."""

import os

import pandas as pd

from .config import (
    salvar_config, INPUT_DIR, OUTPUT_DIR, STG_FILENAME,
    carregar_config, modo_somente_hh,
)
from .constants import CT317_HARDCODE_HH_BASE
from .text_utils import normalizar_chave, _norm_atv, parse_intervalos_escolha
from .tarifas import (
    normalizar_ct313, carregar_stg_tarifas, resolver_rendimento_hh,
)
from .territorio import fazendas_unicas_micro
from .io import (
    selecionar_arquivo, encontrar_coluna,
    carregar_planilha_microplanejamento,
)
from .datas import _formatar_data_dia
from .ui import (
    G, Y, C, DM, BL, RS,
    console, sub, cabecalho, subcabecalho, aviso, erro, ok, prompt,
    pedir_float, pedir_int,
    confirmar, selecionar, selecionar_paginado, esperar,
)
from .context import contexto_sessao, dashboard_header
from .monitor import _emitir_monitor_atual
from .turmas import _catalogo_atividades_completo, _mostrar_catalogo_atividades


def modulo_normalizar_ct(cfg):
    """Menu: selecionar CT bruta, gerar STG, integrar em config.tarifas."""
    dashboard_header()
    subcabecalho("NORMALIZAR CT (CT317 REAL) -> STG_TARIFAS")
    caminho = selecionar_arquivo("CT BRUTA/REAL (.xlsm ou .xlsx)")
    if not caminho:
        return

    print(DM + "  Processando... pode demorar alguns segundos." + RS)
    stg_path, n, custo_h = normalizar_ct313(caminho)
    if not stg_path:
        erro("Aba 'Preco Final' nao encontrada neste arquivo.")
        esperar()
        return

    if modo_somente_hh(cfg):
        ok(f"Gerado {STG_FILENAME}: {n} atividades (modo somente HH).")
    else:
        ok(f"Gerado {STG_FILENAME}: {n} atividades | custo/hora TF = R${custo_h:.2f}")

    if confirmar(
        "Integrar STG_TARIFAS em config.json (substitui tarifas existentes)?",
        default=True,
    ):
        tarifas = carregar_stg_tarifas(stg_path)
        cfg["tarifas"] = tarifas
        cfg["custo_hora_tf"] = round(custo_h, 4)
        salvar_config(cfg)
        ok(f"{len(tarifas)} tarifas integradas no config.")
    esperar("ENTER para voltar")




# ──────────────────────────────────────────────
#  COLUMN MAPPING: KNOWN FIRST, THEN FALLBACK
# ──────────────────────────────────────────────


# ──────────────────────────────────────────────
#  FILE SELECTOR
# ──────────────────────────────────────────────










# ──────────────────────────────────────────────
#  MICROPLANEJAMENTO
# ──────────────────────────────────────────────


# ──────────────────────────────────────────────
#  IMPORTADOR CT_313
# ──────────────────────────────────────────────


def modulo_importar_tarifas(cfg):
    dashboard_header()
    subcabecalho("IMPORTAR TARIFAS ORCADAS (CT_313)")
    caminho = selecionar_arquivo("PLANILHA DE ORCAMENTO (CT_313 ou Tarifas)")
    if not caminho:
        return

    try:
        print(DM + "  Carregando arquivo..." + RS)
        xls = pd.ExcelFile(caminho)
        aba = selecionar("SELECIONE A ABA (ex: Preco Final)", xls.sheet_names)
        if aba is None:
            return

        print(DM + f"  Lendo aba '{aba}'..." + RS)
        df = pd.read_excel(caminho, sheet_name=aba, nrows=1000)
        cols_ct = df.columns.tolist()

        # Tentar mapear automaticamente
        col_atv = encontrar_coluna(cols_ct, "atividade")
        sub()
        print(G + BL + "  MAPEAMENTO:" + RS)
        print(G + f"  Atividade: " + C + f"{col_atv or '???'}" + RS)
        sub()

        if not col_atv or not confirmar("Usar este mapeamento?", default=True):
            idx = selecionar_paginado("COLUNA DA ATIVIDADE", cols_ct)
            col_atv = cols_ct[idx] if idx >= 0 else None
            if not col_atv:
                aviso("Atividade obrigatoria.")
                return

        # Para HH e Preco, perguntar diretamente
        print(G + "\n  Selecione as colunas adicionais (0 = ignorar):\n" + RS)
        idx = selecionar_paginado("COLUNA DE HH/HA", cols_ct)
        col_hh = cols_ct[idx] if idx >= 0 else None
        idx = selecionar_paginado("COLUNA DE PRECO UNITARIO", cols_ct)
        col_preco = cols_ct[idx] if idx >= 0 else None

        tarifas = cfg.get("tarifas", {})
        importadas = 0
        for _, row in df.iterrows():
            nome = str(row.get(col_atv, "")).strip()
            if not nome or nome.lower() == "nan":
                continue
            hh = 0 if not col_hh else row.get(col_hh, 0)
            preco = 0 if not col_preco else row.get(col_preco, 0)
            if pd.notna(hh) and str(hh).strip() != "":
                hh_val = float(str(hh).replace(",", "."))
            else:
                hh_val = resolver_rendimento_hh(cfg, tarifas, nome)
            preco_val = float(str(preco).replace(",", ".")) if pd.notna(preco) else 0.0
            tarifas[nome] = {
                "rendimento_hh": hh_val,
                "preco_unit": preco_val,
                "recurso": "homem",
                "eficiencia": 1.0,
            }
            importadas += 1

        cfg["tarifas"] = tarifas
        salvar_config(cfg)
        ok(f"{importadas} tarifas integradas!")
        sem_hh = [
            k for k, v in tarifas.items() if float(v.get("rendimento_hh", 0) or 0) <= 0
        ]
        sem_preco = [
            k for k, v in tarifas.items() if float(v.get("preco_unit", 0) or 0) <= 0
        ]
        if sem_hh:
            print(Y + f"  Pos-import: {len(sem_hh)} tarifa(s) com HH zerado." + RS)
            for x in sem_hh[:5]:
                print(DM + f"    - {str(x)[:55]}" + RS)
        if sem_preco:
            print(
                Y + f"  Pos-import: {len(sem_preco)} tarifa(s) com preco zerado." + RS
            )
            for x in sem_preco[:5]:
                print(DM + f"    - {str(x)[:55]}" + RS)
    except Exception as e:
        erro(f"Erro ao importar: {e}")

    esperar("ENTER para voltar")


# ──────────────────────────────────────────────
#  DECLIVIDADE
# ──────────────────────────────────────────────



def avaliar_terreno(df_faz):
    print(G + BL + "\n  REFINAMENTO DE DECLIVIDADE\n" + RS)
    print(
        DM
        + "  Isto aplica um fator multiplicativo extra sobre HH/ha (1,0 / 1,15 / 1,30), "
        "independente da classe I–V da CT. Classe I vs V ja esta na linha de preco da CT; "
        "este passo e so para penalizar o cronograma se quiser simular declive geral."
        + RS
    )
    if not confirmar("Aplicar penalidade por declive?", default=False):
        df_faz["penalidade"] = 1.0
        return df_faz
    terrenos = ["Plano (Base x1.0)", "Misto (x1.15)", "Inclinado (x1.30)"]
    t = selecionar("DECLIVIDADE", terrenos)
    if t and "Inclinado" in t:
        df_faz["penalidade"] = 1.3
    elif t and "Misto" in t:
        df_faz["penalidade"] = 1.15
    else:
        df_faz["penalidade"] = 1.0
    return df_faz











def _aplicar_filtro_regiao(df):
    """Filtro opcional por regiao (municipio/estado). Retorna (df_filtrado, regiao_info ou None)."""
    tem_mun = "municipio" in df.columns
    tem_est = "estado" in df.columns
    if not tem_mun and not tem_est:
        return df, None
    df_filt = df.copy()
    regiao_info = {}
    estados_disp = []
    municipios_disp = []
    if tem_est:
        estados_disp = sorted(
            {str(x).strip() for x in df["estado"].dropna().tolist() if str(x).strip()}
        )
    if tem_mun:
        municipios_disp = sorted(
            {str(x).strip() for x in df["municipio"].dropna().tolist() if str(x).strip()}
        )
    n_est = len(estados_disp)
    n_mun = len(municipios_disp)
    print(G + BL + "\n FILTRO POR REGIAO" + RS)
    print(DM + f" {n_est} estado(s), {n_mun} municipio(s) detectado(s) no micro." + RS)
    if not confirmar("Filtrar por regiao (municipio/estado)?", default=False):
        ok("Filtro de regiao ignorado — todos os dados incluidos.")
        return df_filt, None
    sel_estado = None
    sel_municipio = None
    if tem_est and estados_disp:
        if n_est == 1:
            sel_estado = estados_disp[0]
            ok(f"Unico estado: {sel_estado}")
        else:
            op_est = ["TODOS"] + estados_disp
            sel_estado = selecionar("ESTADO", op_est)
            if sel_estado == "TODOS":
                sel_estado = None
    if sel_estado and tem_mun:
        mun_filtrados = sorted(
            {
                str(x).strip()
                for x in df_filt[df_filt["estado"].astype(str).str.strip() == sel_estado]["municipio"].dropna().tolist()
                if str(x).strip()
            }
        )
    elif tem_mun:
        mun_filtrados = municipios_disp
    else:
        mun_filtrados = []
    if mun_filtrados:
        if len(mun_filtrados) == 1:
            sel_municipio = mun_filtrados[0]
            ok(f"Unico municipio: {sel_municipio}")
        else:
            op_mun = ["TODOS"] + mun_filtrados
            sel_municipio = selecionar("MUNICIPIO", op_mun)
            if sel_municipio == "TODOS":
                sel_municipio = None
    if sel_estado:
        df_filt = df_filt[df_filt["estado"].astype(str).str.strip() == sel_estado]
        regiao_info["estado"] = sel_estado
    if sel_municipio:
        df_filt = df_filt[df_filt["municipio"].astype(str).str.strip() == sel_municipio]
        regiao_info["municipio"] = sel_municipio
    if regiao_info:
        loc_str = " / ".join(filter(None, [regiao_info.get("municipio"), regiao_info.get("estado")]))
        ok(
            f"Filtrado por regiao: {loc_str} ({len(df_filt)} registros, "
            f"{df_filt['fazenda'].nunique()} fazenda(s))"
        )
    else:
        ok("Nenhum filtro de regiao aplicado — todos os dados incluidos.")
    return df_filt, regiao_info or None


def _aplicar_filtro_empresa_e_escopo(df):
    """Filtro por EQUIPE (empresa) e escopo (uma fazenda / todas). Retorna (df_filtrado, empresa ou None)."""
    tem_equipe = "equipe" in df.columns
    df_filt = df.copy()
    empresa_filtro = None
    if tem_equipe:
        raw_eq = [
            str(x).strip() for x in df["equipe"].dropna().tolist() if str(x).strip()
        ]
        norm_to_raw = {}
        for e in raw_eq:
            nk = normalizar_chave(e)
            if nk and nk not in norm_to_raw:
                norm_to_raw[nk] = e
        equipes = sorted(norm_to_raw.values(), key=str)
        if equipes:
            print(G + BL + "\n FILTRO POR EMPRESA (EQUIPE)" + RS)
            print(DM + f" {len(equipes)} empresa(s) encontrada(s) no micro." + RS)
            if not confirmar("Filtrar por empresa?", default=False):
                ok("Filtro de empresa ignorado — todos os dados incluidos.")
                contexto_sessao.atualizar_equipe(None)
                _emitir_monitor_atual()
                return df_filt, None
            if len(equipes) == 1:
                empresa_filtro = equipes[0]
                ok(f"Unica empresa: {empresa_filtro}")
            else:
                eq = selecionar("EMPRESA / EQUIPE", equipes)
                if eq:
                    empresa_filtro = eq
            if empresa_filtro:
                nk_sel = normalizar_chave(empresa_filtro)
                sem_eq = df_filt["equipe"].isna() | (
                    df_filt["equipe"].astype(str).str.strip() == ""
                )
                n_sem = int(sem_eq.sum())
                if n_sem:
                    print(
                        DM
                        + f" Excluindo {n_sem} linha(s) sem EQUIPE preenchida (nao entram no filtro por empresa)."
                        + RS
                    )
                    df_filt = df_filt[~sem_eq]
                df_filt = df_filt[
                    df_filt["equipe"]
                    .astype(str)
                    .apply(lambda x: normalizar_chave(x.strip()) == nk_sel)
                ]
                ok(
                    f"Filtrado por equipe: {empresa_filtro} ({len(df_filt)} registros, "
                    f"{df_filt['atividade'].nunique()} atividade(s), {df_filt['fazenda'].nunique()} fazenda(s))"
                )
    if empresa_filtro:
        contexto_sessao.atualizar_equipe(empresa_filtro)
    else:
        contexto_sessao.atualizar_equipe(None)
    _emitir_monitor_atual()
    return df_filt, empresa_filtro




def _selecionar_talhoes_fazenda(df_faz, fazenda):
    """Permite recorte por metodologia e talhao dentro da fazenda selecionada."""
    if df_faz is None or df_faz.empty:
        contexto_sessao.definir_escopo_talhoes([], [])
        return df_faz, {
            "fazenda": fazenda,
            "modo_metodologia": "vazio",
            "metodologias": [],
            "modo_talhao": "vazio",
            "talhoes": [],
        }
    if "chave" not in df_faz.columns:
        contexto_sessao.definir_escopo_talhoes([], [])
        return df_faz, {
            "fazenda": fazenda,
            "modo_metodologia": "sem_coluna",
            "metodologias": [],
            "modo_talhao": "sem_coluna",
            "talhoes": [],
        }

    df_work = df_faz.copy()
    meta = {
        "fazenda": fazenda,
        "modo_metodologia": "sem_coluna",
        "metodologias": [],
    }

    if "metodologia" in df_work.columns:
        metodologias = sorted(
            {
                str(x).strip()
                for x in df_work["metodologia"].dropna().tolist()
                if str(x).strip()
            },
            key=str,
        )
        print(G + BL + "\n  ESCOPO POR METODOLOGIA" + RS)
        print(DM + f"  Fazenda: {fazenda}" + RS)
        if metodologias:
            print(DM + f"  Metodologias presentes ({len(metodologias)}):" + RS)
            for i, m in enumerate(metodologias, 1):
                print(G + f"  [{i:2}] " + C + str(m) + RS)
        else:
            print(DM + "  Nenhuma metodologia preenchida no escopo atual." + RS)
        if not metodologias:
            meta["modo_metodologia"] = "sem_valores"
            meta["metodologias"] = []
        elif len(metodologias) == 1:
            meta["modo_metodologia"] = "unica"
            meta["metodologias"] = metodologias[:]
            ok(f"Metodologia unica no escopo: {metodologias[0]}")
        else:
            op_met = selecionar(
                "ESCOPO DAS METODOLOGIAS",
                [
                    "TODAS AS METODOLOGIAS",
                    "SELECIONAR METODOLOGIAS POR LISTA",
                    "SELECIONAR METODOLOGIAS POR NOME",
                    "FILTRAR METODOLOGIAS POR TEXTO",
                ],
            )

            selecionadas_met = []
            if not op_met or op_met == "TODAS AS METODOLOGIAS":
                meta["modo_metodologia"] = "todas"
                meta["metodologias"] = metodologias[:]
            elif op_met == "SELECIONAR METODOLOGIAS POR LISTA":
                print(
                    DM
                    + "  Digite indices separados por virgula (ex.: 1,2,4) ou intervalo (ex.: 1-3)."
                    + RS
                )
                for i, m in enumerate(metodologias, 1):
                    print(G + f"  [{i:2}] " + C + str(m) + RS)
                raw = prompt("Metodologias", "")
                idxs = parse_intervalos_escolha(raw, len(metodologias))
                selecionadas_met = [metodologias[i] for i in idxs]
            elif op_met == "SELECIONAR METODOLOGIAS POR NOME":
                raw = prompt(
                    "Nomes das metodologias (separados por virgula)",
                    "",
                )
                partes = [
                    normalizar_chave(p)
                    for p in str(raw).replace(";", ",").split(",")
                    if normalizar_chave(p)
                ]
                if partes:
                    for m in metodologias:
                        nm = normalizar_chave(m)
                        if any(p == nm or p in nm for p in partes):
                            selecionadas_met.append(m)
            else:
                filtro = normalizar_chave(prompt("Texto para filtrar metodologia", ""))
                if filtro:
                    selecionadas_met = [
                        m for m in metodologias if filtro in normalizar_chave(m)
                    ]

            if op_met and op_met != "TODAS AS METODOLOGIAS":
                selecionadas_met = sorted(set(selecionadas_met), key=str)
                if not selecionadas_met:
                    aviso(
                        "Nenhuma metodologia selecionada; mantendo TODAS as metodologias da fazenda."
                    )
                    meta["modo_metodologia"] = "fallback_todas"
                    meta["metodologias"] = metodologias[:]
                else:
                    sel_norm = {normalizar_chave(x) for x in selecionadas_met}
                    df_filtrado = df_work[
                        df_work["metodologia"].astype(str).apply(
                            lambda x: normalizar_chave(str(x).strip()) in sel_norm
                        )
                    ].copy()
                    if df_filtrado.empty:
                        aviso(
                            "Filtro de metodologia nao retornou linhas; mantendo TODAS as metodologias da fazenda."
                        )
                        meta["modo_metodologia"] = "fallback_todas"
                        meta["metodologias"] = metodologias[:]
                    else:
                        df_work = df_filtrado
                        meta["modo_metodologia"] = "parcial"
                        meta["metodologias"] = selecionadas_met
                        ok(
                            f"Escopo por metodologia aplicado: {len(selecionadas_met)} selecionada(s), "
                            f"{len(df_work)} linha(s) no micro."
                        )

    talhoes = sorted(
        {
            str(x).strip()
            for x in df_work["chave"].dropna().tolist()
            if str(x).strip()
        },
        key=str,
    )
    if not talhoes:
        contexto_sessao.definir_escopo_talhoes([], [])
        out_meta = dict(meta)
        out_meta.update({"modo_talhao": "sem_talhoes", "talhoes": []})
        _emitir_monitor_atual()
        return df_work, out_meta
    if len(talhoes) == 1:
        ok(f"Talhao unico na fazenda: {talhoes[0]}")
        contexto_sessao.definir_escopo_talhoes(talhoes[:], talhoes[:])
        out_meta = dict(meta)
        out_meta.update({"modo_talhao": "unico", "talhoes": talhoes[:]})
        _emitir_monitor_atual()
        return df_work, out_meta

    print(G + BL + "\n  ESCOPO POR TALHAO" + RS)
    print(DM + f"  Fazenda: {fazenda}" + RS)
    print(DM + f"  {len(talhoes)} talhao(oes) disponivel(is)." + RS)
    op = selecionar(
        "ESCOPO DOS TALHOES",
        [
            "TODOS OS TALHOES",
            "SELECIONAR TALHOES POR LISTA",
            "FILTRAR TALHOES POR TEXTO",
        ],
    )
    if not op or op == "TODOS OS TALHOES":
        contexto_sessao.definir_escopo_talhoes(talhoes[:], talhoes[:])
        out_meta = dict(meta)
        out_meta.update({"modo_talhao": "todos", "talhoes": talhoes[:]})
        _emitir_monitor_atual()
        return df_work, out_meta

    selecionados = []
    if op == "SELECIONAR TALHOES POR LISTA":
        print(
            DM
            + "  Digite numeros separados por virgula (ex.: 1,3,7) ou intervalo (ex.: 1-4)."
            + RS
        )
        for i, t in enumerate(talhoes, 1):
            print(G + f"  [{i:2}] " + C + str(t) + RS)
        raw = prompt("Talhoes", "")
        idxs = parse_intervalos_escolha(raw, len(talhoes))
        selecionados = [talhoes[i] for i in idxs]
    else:
        filtro = normalizar_chave(prompt("Texto para filtrar talhoes", ""))
        if filtro:
            selecionados = [t for t in talhoes if filtro in normalizar_chave(t)]

    if not selecionados:
        aviso("Nenhum talhao selecionado; mantendo TODOS os talhoes da fazenda.")
        contexto_sessao.definir_escopo_talhoes(talhoes[:], talhoes[:])
        out_meta = dict(meta)
        out_meta.update({"modo_talhao": "fallback_todos", "talhoes": talhoes[:]})
        _emitir_monitor_atual()
        return df_work, out_meta

    df_sel = df_work[df_work["chave"].astype(str).isin(set(selecionados))].copy()
    ok(
        f"Escopo por talhao aplicado: {len(selecionados)} selecionado(s), {len(df_sel)} linha(s) no micro."
    )
    contexto_sessao.definir_escopo_talhoes(selecionados, talhoes[:])
    out_meta = dict(meta)
    out_meta.update({"modo_talhao": "parcial", "talhoes": selecionados})
    _emitir_monitor_atual()
    return df_sel, out_meta




def _metodologias_presentes(df_faz):
    if df_faz is None or df_faz.empty or "metodologia" not in df_faz.columns:
        return []
    return sorted(
        {
            str(x).strip()
            for x in df_faz["metodologia"].dropna().tolist()
            if str(x).strip()
        },
        key=str,
    )




def _prompt_proximas_metodologias(df_faz_base, meta_escopo, metodologias_executadas):
    """
    Mostra prompt para continuar com metodologias restantes na mesma fazenda.
    Retorna True quando o usuario deseja seguir para as proximas metodologias.
    """
    todas = _metodologias_presentes(df_faz_base)
    if not todas:
        return False

    meta_escopo = meta_escopo or {}
    usadas = list(meta_escopo.get("metodologias") or [])
    for m in usadas:
        nm = normalizar_chave(m)
        if nm:
            metodologias_executadas.add(nm)

    restantes = [m for m in todas if normalizar_chave(m) not in metodologias_executadas]
    if not restantes:
        return False

    sub()
    print(C + BL + "  PROXIMAS METODOLOGIAS DISPONIVEIS" + RS)
    print(DM + f"  Restantes: {len(restantes)}" + RS)
    for i, m in enumerate(restantes[:12], 1):
        print(G + f"  [{i:2}] " + C + str(m) + RS)
    if len(restantes) > 12:
        print(DM + f"  ... +{len(restantes) - 12} metodologia(s)" + RS)
    return confirmar(
        "Executar outra metodologia desta fazenda agora?",
        default=True,
    )




def _executar_scheduler_fazenda_interativo(cfg, df_scope, faz, catalogo_scope):
    from .scheduler_core import calcular_cronograma_inteligente
    metodologias_executadas = set()
    while True:
        df_faz_base = df_scope[df_scope["fazenda"] == faz].copy()
        if df_faz_base.empty:
            aviso("Sem linhas para a fazenda selecionada neste escopo.")
            return

        contexto_sessao.atualizar_fazenda(faz, df_faz_base)
        df_faz, meta_escopo = _selecionar_talhoes_fazenda(df_faz_base, faz)
        resultado = calcular_cronograma_inteligente(
            cfg,
            df_faz,
            faz,
            escopo_meta=meta_escopo,
            atividades_catalogo=catalogo_scope,
        )
        if isinstance(resultado, dict) and resultado.get("acao") == "retroceder_escopo":
            aviso("Checkpoint retroativo: reselecione fazenda/escopo.")
            continue

        if _prompt_proximas_metodologias(
            df_faz_base,
            meta_escopo,
            metodologias_executadas,
        ):
            aviso("Abrindo selecao para as proximas metodologias desta fazenda.")
            continue
        break




def _menu_ajustar_escopo_atividades(df_faz, cfg=None, atividades_catalogo=None):
    """
    Ajustes por execucao no escopo atual:
      - substituir atividade
      - remover atividade
      - adicionar atividade em talhao(es)
    """
    if df_faz is None or df_faz.empty:
        return df_faz

    if "atividade" not in df_faz.columns or "chave" not in df_faz.columns:
        aviso("Escopo sem colunas necessarias para ajuste de atividade.")
        return df_faz

    out = df_faz.copy()
    if "area_ha" not in out.columns:
        out["area_ha"] = 0.0
    if "penalidade" not in out.columns:
        out["penalidade"] = 1.0

    def _atividades():
        return sorted(
            {
                str(x).strip()
                for x in out["atividade"].dropna().tolist()
                if str(x).strip()
            },
            key=str,
        )

    def _talhoes():
        return sorted(
            {str(x).strip() for x in out["chave"].dropna().tolist() if str(x).strip()},
            key=str,
        )

    while True:
        atvs = _atividades()
        catalogo_all = _catalogo_atividades_completo(
            atvs,
            cfg=cfg,
            atividades_catalogo=atividades_catalogo,
        )
        tls = _talhoes()
        sub()
        print(G + BL + "  AJUSTE DE ATIVIDADES (APENAS NESTA EXECUCAO)" + RS)
        print(
            DM
            + f"  Atividades no escopo: {len(atvs)} | Catalogo completo: {len(catalogo_all)} | Talhoes no escopo: {len(tls)}"
            + RS
        )
        op = selecionar(
            "OPERACAO DE AJUSTE",
            [
                "Substituir atividade",
                "Remover atividade",
                "Adicionar atividade",
                "Ver listas completas (escopo x catalogo)",
                "Concluir ajustes",
            ],
        )
        if not op or op == "Concluir ajustes":
            break

        if op == "Ver listas completas (escopo x catalogo)":
            _mostrar_catalogo_atividades(atvs, catalogo_all)
            esperar()
            continue

        if op == "Substituir atividade":
            if not atvs:
                aviso("Sem atividades para substituir.")
                continue
            print(DM + " Origens (ex: 1,3,5-8 ou ENTER para selecionar uma)" + RS)
            for i, a in enumerate(atvs, 1):
                print(G + f" [{i:2}] " + C + str(a)[:70] + RS)
            raw = prompt("Origens", "")
            if str(raw).strip():
                idxs = parse_intervalos_escolha(raw, len(atvs))
                if not idxs:
                    aviso("Nenhum indice valido.")
                    continue
                srcs = [atvs[i] for i in idxs]
            else:
                src = selecionar("ATIVIDADE ORIGEM", atvs)
                if not src:
                    continue
                srcs = [src]
            destinos = [x for x in catalogo_all if x not in srcs]
            dst_opt = selecionar(
                "DESTINO", destinos + ["[DIGITAR NOVA ATIVIDADE]"]
            )
            if not dst_opt:
                continue
            dst = (
                prompt("Nova atividade", "")
                if dst_opt == "[DIGITAR NOVA ATIVIDADE]"
                else dst_opt
            )
            dst = _norm_atv(dst)
            if not dst:
                aviso("Destino invalido.")
                continue
            n_sub = 0
            for src in srcs:
                mask = out["atividade"].astype(str) == str(src)
                n_sub += int(mask.sum())
                out.loc[mask, "atividade"] = dst
            ok(f"{len(srcs)} atividade(s) substituida(s) -> '{dst}' ({n_sub} linhas).")
            continue

        if op == "Remover atividade":
            if not atvs:
                aviso("Sem atividades para remover.")
                continue
            print(DM + " Remover (ex: 1,3,5-8 ou ENTER para selecionar uma)" + RS)
            for i, a in enumerate(atvs, 1):
                print(G + f" [{i:2}] " + C + str(a)[:70] + RS)
            raw = prompt("Remover", "")
            if str(raw).strip():
                idxs = parse_intervalos_escolha(raw, len(atvs))
                if not idxs:
                    aviso("Nenhum indice valido.")
                    continue
                rms = [atvs[i] for i in idxs]
            else:
                rm = selecionar("ATIVIDADE PARA REMOVER", atvs)
                if not rm:
                    continue
                rms = [rm]
            n0 = len(out)
            mask = out["atividade"].astype(str).isin([str(r) for r in rms])
            out = out[~mask].copy()
            ok(f"{len(rms)} atividade(s) removida(s) ({n0 - len(out)} linha(s)).")
            continue

        if op == "Adicionar atividade":
            print(DM + " Atividades (ex: 1,3,5-8 ou ENTER para selecionar uma)" + RS)
            for i, a in enumerate(catalogo_all, 1):
                print(G + f" [{i:2}] " + C + str(a)[:70] + RS)
            print(G + f" [{len(catalogo_all)+1:2}] " + C + "[DIGITAR NOVA ATIVIDADE]" + RS)
            raw = prompt("Atividades", "")
            if str(raw).strip():
                idxs = parse_intervalos_escolha(raw, len(catalogo_all) + 1)
                novas = []
                for i in idxs:
                    if i < len(catalogo_all):
                        novas.append(catalogo_all[i])
                    else:
                        t = prompt("Nome da atividade", "")
                        t = _norm_atv(t)
                        if t:
                            novas.append(t)
                if not novas:
                    aviso("Nenhuma atividade valida.")
                    continue
            else:
                base_opt = selecionar(
                    "NOVA ATIVIDADE",
                    catalogo_all + ["[DIGITAR NOVA ATIVIDADE]"],
                )
                if not base_opt:
                    continue
                nova = (
                    prompt("Nome da atividade", "")
                    if base_opt == "[DIGITAR NOVA ATIVIDADE]"
                    else base_opt
                )
                nova = _norm_atv(nova)
                if not nova:
                    aviso("Atividade invalida.")
                    continue
                novas = [nova]
            op_t = selecionar(
                "APLICAR EM",
                [
                    "Todos os talhoes do escopo",
                    "Talhoes por lista",
                    "Talhoes por texto",
                ],
            )
            if not op_t:
                continue
            sel_talhoes = tls[:]
            if op_t == "Talhoes por lista":
                print(DM + "  Digite numeros separados por virgula (ex.: 1,3,7)." + RS)
                for i, t in enumerate(tls, 1):
                    print(G + f"  [{i:2}] " + C + str(t) + RS)
                raw = prompt("Talhoes", "")
                idxs = []
                for p in str(raw).replace(";", ",").split(","):
                    p = p.strip()
                    if p.isdigit():
                        iv = int(p)
                        if 1 <= iv <= len(tls):
                            idxs.append(iv - 1)
                idxs = sorted(set(idxs))
                sel_talhoes = [tls[i] for i in idxs]
            elif op_t == "Talhoes por texto":
                fx = normalizar_chave(prompt("Texto no talhao", ""))
                sel_talhoes = [t for t in tls if fx and fx in normalizar_chave(t)]

            if not sel_talhoes:
                aviso("Nenhum talhao selecionado para adicionar atividade.")
                continue

        area_def = float(out["area_ha"].median() or 1.0)
        area_nova = pedir_float(
            "Area/ha para nova atividade (por talhao)", round(area_def, 2),
            allow_zero=True,
        )
        pen_def = float(out["penalidade"].median() or 1.0)
        pen_nova = pedir_float(
            "Penalidade de terreno da nova atividade", round(pen_def, 2),
            allow_zero=False,
        )

        add_rows = []
        for nova in novas:
            for th in sel_talhoes:
                ja = out[
                    (out["chave"].astype(str) == str(th))
                    & (out["atividade"].astype(str) == str(nova))
                ]
                if not ja.empty:
                    continue
                ref = out[out["chave"].astype(str) == str(th)].head(1)
                row = ref.iloc[0].to_dict() if not ref.empty else {}
                row["chave"] = th
                row["atividade"] = nova
                row["area_ha"] = float(area_nova)
                row["penalidade"] = float(pen_nova)
                add_rows.append(row)
        if add_rows:
            out = pd.concat([out, pd.DataFrame(add_rows)], ignore_index=True)
            ok(f"{len(novas)} atividade(s) adicionada(s) em {len(add_rows)} linha(s).")

    return out




def _proximo_caminho_livre(pasta, nome_arquivo):
    """
    Retorna nome/caminho sem colisao:
    - se nao existe, usa o nome original
    - se existe, gera sufixo _v2, _v3...
    """
    base, ext = os.path.splitext(str(nome_arquivo))
    candidato_nome = str(nome_arquivo)
    candidato_path = os.path.join(pasta, candidato_nome)
    if not os.path.exists(candidato_path):
        return candidato_nome, candidato_path
    i = 2
    while True:
        candidato_nome = f"{base}_v{i}{ext}"
        candidato_path = os.path.join(pasta, candidato_nome)
        if not os.path.exists(candidato_path):
            return candidato_nome, candidato_path
        i += 1


