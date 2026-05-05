"""Application entry point — main menu, startup, and session cleanup."""

import os
import sys
import atexit

from .ui import (
    G, Y, C, DM, BL, RS,
    sub, cabecalho, subcabecalho, aviso, erro, ok, prompt,
    selecionar, confirmar,
)
from .config import (
    INPUT_DIR, STG_FILENAME, MODO_SOMENTE_HH,
    DEMO_MICRO_FILENAME, DEMO_MICRO_SOURCE_FILENAME,
    _is_demo_mode, _is_beta_mode, _is_legacy_mode, _is_demo_micro_path,
    DIR, carregar_config, salvar_config,
)
from .context import contexto_sessao, dashboard_header
from .monitor import _abrir_monitor_janela
from .tarifas import normalizar_ct313, carregar_stg_tarifas
from .territorio import (
    aviso_fazendas_micro_sem_cadastro_ct, modulo_validar_fazendas_ct,
)
from .io import (
    selecionar_arquivo, carregar_planilha_microplanejamento,
    _find_default_micro_path, _find_default_ct_path,
    _resolver_fazenda_demo_ulianopolis,
    garantir_fazenda_ulianopolis_no_ct,
    reconstruir_demo_ulianopolis_a_partir_da_fonte,
)
from .de_para import aplicar_depara_padrao_exame
from .app import (
    modulo_importar_tarifas, modulo_normalizar_ct,
    _aplicar_filtro_empresa_e_escopo,
)
from .scheduler_core import (
    calcular_cronograma_inteligente,
    _executar_lote_fazendas,
    _executar_multi_equipes,
    _executar_scheduler_fazenda_interativo,
)


def menu_principal(cfg, df, nome_arquivo_micro="", demo_mode=False):
    opcoes = [
        ("1", "Smart Scheduler (Operacional HH/HM)"),
        ("2", "Importar Tarifas (CT real/manual)"),
        ("3", "Normalizar CT317/CT -> STG (auto)"),
        ("4", "Mapeamentos de_para (micro -> tarifa)"),
        ("5", "Trocar planilha de microplanejamento (.xlsx)"),
        ("6", "Fazendas micro vs CT (lista fazendas_ct)"),
        ("M", "Abrir Monitor em Janela Separada"),
        ("0", "Sair"),
    ]
    while True:
        dashboard_header()
        subcabecalho()
        contexto_sessao.atualizar_configuracoes(cfg)
        nf = df["fazenda"].nunique()
        nu = df["chave"].nunique()
        na = df["atividade"].nunique()
        stg_existe = os.path.exists(os.path.join(INPUT_DIR, STG_FILENAME))
        nt = len(cfg.get("tarifas", {}))
        print(
            G
            + f"  Base: "
            + C
            + f"{nf} fazendas  |  {nu} talhoes  |  {na} atividades"
            + RS
        )
        print(
            G
            + f"  Tarifas: "
            + C
            + f"{nt} carregadas"
            + G
            + f"  |  STG: "
            + C
            + f"{'Sim' if stg_existe else 'Nao'}"
            + RS
        )
        print(
            G
            + f"  Orcamento estrito: "
            + C
            + ("Sim" if cfg.get("orcamento_estrito", True) else "Nao")
            + RS
        )
        if "equipe" in df.columns:
            eq_list = sorted(df["equipe"].dropna().unique().tolist(), key=str)
            print(
                G
                + f"  Empresas (EQUIPE): "
                + C
                + f"{len(eq_list)} ({', '.join(str(e)[:20] for e in eq_list[:5])}{'...' if len(eq_list) > 5 else ''})"
                + RS
            )
        if nome_arquivo_micro:
            print(
                G
                + f"  Microplanejamento: "
                + C
                + os.path.basename(nome_arquivo_micro)
                + RS
            )
        if demo_mode and _is_demo_micro_path(nome_arquivo_micro):
            print(
                Y
                + f"  DEMO: opcao [1] = maior fazenda do micro (municipio Ulianopolis), tarifas = CT 313."
                + RS
            )
        sub()
        for cod, desc in opcoes:
            print(G + f"  [{cod}] " + C + desc + RS)
        sub()
        v = prompt("Opcao").strip()
        if v == "1":
            contexto_sessao.atualizar_modo("single")
            if demo_mode and _is_demo_micro_path(nome_arquivo_micro):
                faz = _resolver_fazenda_demo_ulianopolis(df)
                if not faz:
                    aviso(
                        "DEMO: nenhuma fazenda com 'Ulianópolis' na coluna fazenda do micro."
                    )
                else:
                    ok(f"DEMO: fazenda {faz}")
                    df_faz = df[df["fazenda"] == faz].copy()
                    contexto_sessao.atualizar_fazenda(faz, df_faz)
                    resultado = calcular_cronograma_inteligente(
                        cfg,
                        df_faz,
                        faz,
                        atividades_catalogo=sorted(
                            {
                                str(x).strip()
                                for x in df["atividade"].dropna().unique().tolist()
                                if str(x).strip()
                            },
                            key=str,
                        ),
                    )
                    if isinstance(resultado, dict) and resultado.get("acao") == "retroceder_escopo":
                        aviso("Retornando ao seletor de fazenda/escopo.")
            else:
                df_scope, empresa_filtro = _aplicar_filtro_empresa_e_escopo(df)
                if df_scope is None or df_scope.empty:
                    aviso("Nenhum dado apos filtros.")
                    continue
                catalogo_scope = sorted(
                    {
                        str(x).strip()
                        for x in df_scope["atividade"].dropna().unique().tolist()
                        if str(x).strip()
                    },
                    key=str,
                )
                fazendas = sorted(df_scope["fazenda"].unique().tolist())
                if len(fazendas) == 1:
                    faz = fazendas[0]
                    ok(f"Fazenda unica no escopo: {faz}")
                    _executar_scheduler_fazenda_interativo(
                        cfg,
                        df_scope,
                        faz,
                        catalogo_scope,
                    )
                else:
                    op_faz = [
                        "TODAS AS FAZENDAS (equipe unica)",
                        "MULTI-EQUIPES (carteiras separadas)",
                    ] + fazendas
                    faz = selecionar("SELECIONE A FAZENDA OU MODO", op_faz)
                    if faz == "TODAS AS FAZENDAS (equipe unica)":
                        contexto_sessao.atualizar_modo("lote")
                        _executar_lote_fazendas(
                            cfg,
                            df_scope,
                            fazendas,
                            empresa_filtro=empresa_filtro,
                            nome_arquivo_micro=nome_arquivo_micro,
                        )
                    elif faz == "MULTI-EQUIPES (carteiras separadas)":
                        contexto_sessao.atualizar_modo("multi_equipes")
                        _executar_multi_equipes(
                            cfg,
                            df_scope,
                            fazendas,
                            empresa_filtro=empresa_filtro,
                            nome_arquivo_micro=nome_arquivo_micro,
                        )
                    elif faz:
                        _executar_scheduler_fazenda_interativo(
                            cfg,
                            df_scope,
                            faz,
                            catalogo_scope,
                        )
        elif v == "2":
            modulo_importar_tarifas(cfg)
        elif v == "3":
            modulo_normalizar_ct(cfg)
        elif v == "4":
            modulo_mapeamentos_de_para(cfg, df)
        elif v == "5":
            p = selecionar_arquivo("NOVO MICROPLANEJAMENTO (.xlsx)")
            if p:
                ndf = carregar_planilha_microplanejamento(
                    cfg, caminho=p, modo_auto=True
                )
                if ndf is None:
                    aviso(
                        "Nao foi possivel carregar automaticamente. Tente de novo sem modo_auto (o app pedira colunas)."
                    )
                    ndf = carregar_planilha_microplanejamento(
                        cfg, caminho=p, modo_auto=False
                    )
                if ndf is not None:
                    df = ndf
                    nome_arquivo_micro = p
                    cfg["arquivo_micro"] = os.path.basename(p)
                    salvar_config(cfg)
                    atividades_reais = sorted(
                        str(x).strip()
                        for x in df["atividade"].dropna().unique()
                        if str(x).strip()
                    )
                    novos = aplicar_depara_padrao_exame(cfg, atividades_reais)
                    ok(
                        f"Micro atualizado: {os.path.basename(p)} | {len(df)} registros | "
                        f"{df['fazenda'].nunique()} fazendas | de_para +{novos} novos mapeamentos."
                    )
                    if demo_mode and _is_demo_micro_path(p):
                        n = garantir_fazenda_ulianopolis_no_ct(cfg, df)
                        if n:
                            salvar_config(cfg)
                            ok(f"DEMO: +{n} fazenda(s) em fazendas_ct.")
                    aviso_fazendas_micro_sem_cadastro_ct(cfg, df)
                    input(DM + "  [ENTER] " + RS)
        elif v == "6":
            modulo_validar_fazendas_ct(cfg, df)
        elif v.upper() == "M":
            dashboard_header()
            subcabecalho("ABRIR MONITOR EXTERNO")
            print(G + BL + " Tipo de Feed:" + RS)
            print(DM + " [1] meta - Operacao e metas" + RS)
            print(DM + " [2] rendimentos - HH/ha por atividade" + RS)
            print(DM + " [3] relatorios - Buffer de relatorios" + RS)
            sub()
            feed_op = prompt("Opcao", "1").strip()
            feed_map = {"1": "meta", "2": "rendimentos", "3": "relatorios"}
            feed_escolhido = feed_map.get(feed_op, "meta")
            ok(f"Abrindo monitor com feed '{feed_escolhido}'...")
            _abrir_monitor_janela(feed=feed_escolhido)
            input(DM + "\n [ENTER para voltar] " + RS)
        elif v == "0":
            print(G + "\n Sistema encerrado.\n" + RS)
            break
        else:
            aviso("Opcao invalida.")


def main():
    demo = _is_demo_mode()
    beta = _is_beta_mode()
    legacy = _is_legacy_mode()
    sub_titulo = (
        f"DEMO Ulianópolis ({DEMO_MICRO_SOURCE_FILENAME} -> {DEMO_MICRO_FILENAME} + CT317)"
        if demo
        else ""
    )
    if MODO_SOMENTE_HH:
        sub_titulo = (sub_titulo + " | " if sub_titulo else "") + "MODO SOMENTE HH"
    if beta:
        if sub_titulo:
            sub_titulo += " | PADRAO"
        else:
            sub_titulo = "PADRAO - carga robusta micro + comparativos operacionais"
    if legacy:
        if sub_titulo:
            sub_titulo += " | LEGACY"
        else:
            sub_titulo = "LEGACY - comportamento anterior sem comparativos padrao"
    cabecalho(sub_titulo)
    print(DM + "  Inicializando sistema...\n" + RS)
    cfg = carregar_config()
    salvar_config(cfg)

    if demo:
        rebuilt = reconstruir_demo_ulianopolis_a_partir_da_fonte()
        if rebuilt:
            ok(
                f"DEMO: {DEMO_MICRO_FILENAME} atualizado a partir de {DEMO_MICRO_SOURCE_FILENAME} "
                f"({rebuilt[0]} linhas, {rebuilt[1]} atividades unicas)."
            )
        micro_padrao = os.path.join(INPUT_DIR, DEMO_MICRO_FILENAME)
        if not os.path.exists(micro_padrao):
            erro(
                f"Modo DEMO: coloque {DEMO_MICRO_SOURCE_FILENAME} (gera {DEMO_MICRO_FILENAME}) "
                f"ou o proprio {DEMO_MICRO_FILENAME} em:\n {INPUT_DIR}"
            )
            sys.exit(1)
    else:
        micro_padrao = _find_default_micro_path(cfg)
    ct_padrao = _find_default_ct_path()
    if ct_padrao:
        try:
            stg_path, n, custo_h = normalizar_ct313(ct_padrao)
            if stg_path and n > 0:
                cfg["tarifas"] = carregar_stg_tarifas(stg_path)
                cfg["custo_hora_tf"] = round(custo_h, 4)
                salvar_config(cfg)
                ok(
                    f"CT auto: {os.path.basename(ct_padrao)} -> {n} atividades (modo operacional)"
                )
        except Exception as ex:
            aviso(f"Falha no auto-carregamento CT: {ex}")

    if micro_padrao:
        df = carregar_planilha_microplanejamento(
            cfg, caminho=micro_padrao, modo_auto=True
        )
        if df is None:
            aviso("Falha no auto-carregamento do micro padrao; abrindo modo manual.")
            df = carregar_planilha_microplanejamento(cfg)
    else:
        df = carregar_planilha_microplanejamento(cfg)

    if df is not None:
        if micro_padrao:
            cfg["arquivo_micro"] = os.path.basename(micro_padrao)
            salvar_config(cfg)
        atividades_reais = sorted(
            str(x).strip() for x in df["atividade"].dropna().unique() if str(x).strip()
        )
        novos = aplicar_depara_padrao_exame(cfg, atividades_reais)
        if demo and micro_padrao and _is_demo_micro_path(micro_padrao):
            n = garantir_fazenda_ulianopolis_no_ct(cfg, df)
            if n:
                salvar_config(cfg)
                ok(f"DEMO: +{n} fazenda(s) em fazendas_ct.")
        aviso_fazendas_micro_sem_cadastro_ct(cfg, df)
        dp = {
            k: v
            for k, v in cfg.get("de_para", {}).items()
            if not str(k).startswith("_")
        }
        ok(
            f"{len(df)} registros | "
            f"{df['fazenda'].nunique()} fazendas | {df['chave'].nunique()} talhoes | "
            f"{len(dp)} de_para mapeados ({novos} novos)"
        )
        input(DM + "  [ENTER para continuar] " + RS)
        menu_principal(cfg, df, micro_padrao or "", demo_mode=demo)
    else:
        aviso("Nenhuma planilha selecionada.")


def _cleanup_estado_sessao():
    """Remove arquivos estado_sessao_*.json antigos ao sair."""
    try:
        import glob
        pattern = os.path.join(DIR, "estado_sessao_*.json")
        files = glob.glob(pattern)
        removed = 0
        for f in files:
            try:
                os.remove(f)
                removed += 1
            except Exception:
                pass
        if removed > 0:
            print(DM + f" [Limpo: {removed} arquivo(s) de estado removidos]" + RS)
    except Exception:
        pass


# Registrar cleanup ao sair
atexit.register(_cleanup_estado_sessao)
