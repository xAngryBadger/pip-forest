"""
ATM — Gerenciador de Restauração Florestal  v4.0
Autor: Isaac (Zaza)
Uso  : python atm3.py

Changelog v4.0:
  - Motor de reconciliação com de_para + fuzzy matching
  - Importador de tarifas (Tarifas_e_Rendimento.xlsx)
  - Módulo de otimização financeira (mec vs manual)
  - Seletor de intensidade para atividades com classes I-V
  - Fallback guiado para atividades novas
  - Sprint melhorado com colaboradores por atividade
  - Escopo de meses com dias úteis
"""

import os, sys, json, math, datetime
import pandas as pd
from collections import defaultdict
from difflib import get_close_matches

# ──────────────────────────────────────────────────────────────
#  CORES
# ──────────────────────────────────────────────────────────────
try:
    import colorama; colorama.init()
    G="\033[92m"; Y="\033[93m"; R="\033[91m"; C="\033[96m"
    DM="\033[2m"; BL="\033[1m"; RS="\033[0m"
except ImportError:
    G=Y=R=C=DM=BL=RS=""

W = 66
VERSION = "4.0"

ASCII_FARM = r"""
                            +&-
                           _.-^-._    .--.
                        .-'   _   '-. |__|
                       /     |_|     \|  |
                      /               \  |
                     /|     _____     |\ |
                      |    |==|==|    |  |
  |---|---|---|---|---|    |--|--|    |  |
  |---|---|---|---|---|    |==|==|    |  |
 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
"""

def linha(c="═"): print(G + c*W + RS)
def sub(c="─"):   print(DM + c*W + RS)

def cabecalho(sub_titulo=""):
    os.system("cls" if os.name=="nt" else "clear")
    print(G + ASCII_FARM + RS)
    linha()
    print(G+BL + f"  [ A.T.M. ]  RESTAURAÇÃO FLORESTAL  v{VERSION}".center(W) + RS)
    if sub_titulo:
        print(DM+G + sub_titulo.center(W) + RS)
    print(DM+G + datetime.datetime.now().strftime("  %d/%m/%Y  %H:%M").center(W) + RS)
    linha()

def aviso(m): print(Y+f"\n  ⚠  {m}"+RS)
def erro(m):  print(R+f"\n  ✗  {m}"+RS)
def ok(m):    print(G+f"\n  ✓  {m}"+RS)

def prompt(msg, default=None):
    suf = f" [{default}]" if default is not None else ""
    try:
        v = input(G+"  » "+C+msg+suf+G+": "+RS).strip()
    except (EOFError, KeyboardInterrupt):
        print(); sair()
    return v if v else (str(default) if default is not None else "")

def pedir_float(msg, default):
    while True:
        v = prompt(msg, default)
        try:
            f = float(str(v).replace(",","."))
            if f > 0: return f
        except ValueError: pass
        aviso("Valor inválido. Número positivo.")

def pedir_int(msg, default, allow_zero=False):
    while True:
        v = prompt(msg, default)
        try:
            i = int(v)
            if i > 0 or (allow_zero and i >= 0): return i
        except ValueError: pass
        aviso("Valor inválido. Inteiro positivo.")

def selecionar(titulo, itens, zero_label="Voltar"):
    print(G+f"\n  ── {titulo} "+"─"*max(0,W-len(titulo)-6)+RS)
    for i,it in enumerate(itens,1):
        print(G+f"  [{i:2}] "+C+str(it)+RS)
    print(G+f"  [ 0] "+DM+zero_label+RS)
    while True:
        v = prompt("Escolha").strip()
        if v=="0": return None
        if v.isdigit() and 1<=int(v)<=len(itens): return itens[int(v)-1]
        aviso("Opção inválida.")

def sair():
    print(G+"\n  Sistema encerrado.\n"+RS); sys.exit(0)

# ──────────────────────────────────────────────────────────────
#  CONFIG
# ──────────────────────────────────────────────────────────────
DIR  = os.path.dirname(os.path.abspath(__file__))
CFGP = os.path.join(DIR,"config.json")

def carregar_config():
    if not os.path.exists(CFGP):
        erro(f"config.json não encontrado: {CFGP}"); sys.exit(1)
    with open(CFGP,"r",encoding="utf-8") as f:
        cfg = json.load(f)
    # Garantir estrutura v4
    if "de_para" not in cfg:
        cfg["de_para"] = {}
    if "tarifas" not in cfg:
        cfg["tarifas"] = {}
    if "arquivo_tarifas" not in cfg:
        cfg["arquivo_tarifas"] = "Tarifas e Rendimento.xlsx"
    return cfg

def salvar_config(cfg):
    with open(CFGP,"w",encoding="utf-8") as f:
        json.dump(cfg,f,ensure_ascii=False,indent=2)

# ──────────────────────────────────────────────────────────────
#  MOTOR DE RECONCILIAÇÃO v4 (de_para + fuzzy)
# ──────────────────────────────────────────────────────────────
def normalizar_nome(nome):
    """Remove sufixos de fase/localidade para matching."""
    import re
    # Remove sufixos comuns: Impl. PL, Impl. CD, APP/RL, Manut., I, II, etc.
    nome = re.sub(r'\s+(Impl\.|Manut\.)\s*(PL|CD)?\s*', ' ', nome, flags=re.IGNORECASE)
    nome = re.sub(r'\s*[-–]\s*APP/?RL\s*I*\s*$', '', nome, flags=re.IGNORECASE)
    nome = re.sub(r'\s+APP/?RL\s*I*\s*$', '', nome, flags=re.IGNORECASE)
    nome = re.sub(r'\s+I+\s*$', '', nome)
    nome = re.sub(r'\s+', ' ', nome).strip()
    return nome.upper()

def fuzzy_match(nome_mp, tarifas_disponiveis, cutoff=0.35):
    """Retorna até 3 sugestões de tarifas para um nome do microplanejamento."""
    nome_norm = normalizar_nome(nome_mp)
    nomes_tarifas = list(tarifas_disponiveis.keys())
    nomes_norm_map = {normalizar_nome(t): t for t in nomes_tarifas}

    # Match direto normalizado
    if nome_norm in nomes_norm_map:
        return [nomes_norm_map[nome_norm]]

    # Fuzzy matching
    matches = get_close_matches(nome_norm, list(nomes_norm_map.keys()), n=3, cutoff=cutoff)
    return [nomes_norm_map[m] for m in matches]

def reconciliar_atividade(cfg, nome_mp, interativo=True):
    """
    Motor de reconciliação em 4 camadas:
    1. Match direto no config.atividades
    2. de_para já salvo
    3. Fuzzy matching + confirmação do usuário
    4. Fallback manual guiado

    Retorna: dict com dados da atividade (rendimento_hh, preco_unit, etc.)
    """
    # Camada 1: Match direto
    if nome_mp in cfg["atividades"]:
        return cfg["atividades"][nome_mp]

    # Camada 2: de_para já mapeado
    if nome_mp in cfg.get("de_para", {}):
        tarifa_target = cfg["de_para"][nome_mp]
        if tarifa_target in cfg.get("tarifas", {}):
            return cfg["tarifas"][tarifa_target]
        elif tarifa_target in cfg["atividades"]:
            return cfg["atividades"][tarifa_target]

    # Camada 3: Fuzzy matching
    tarifas = cfg.get("tarifas", {})
    if tarifas and interativo:
        sugestoes = fuzzy_match(nome_mp, tarifas)
        if sugestoes:
            print(Y+f"\n  ⚡ Nova atividade detectada: "+C+nome_mp+RS)
            print(Y+"  Sugestões de tarifas correspondentes:"+RS)
            for i, sug in enumerate(sugestoes, 1):
                t = tarifas[sug]
                print(G+f"    [{i}] {sug:<45} "+C+f"HH:{t.get('hh','—'):>5}  R$:{t.get('preco_unit',0):>8.2f}"+RS)
            print(G+f"    [0] Nenhuma — informar manualmente"+RS)

            resp = prompt("Escolha", "1")
            if resp.isdigit() and 1 <= int(resp) <= len(sugestoes):
                tarifa_escolhida = sugestoes[int(resp)-1]
                cfg["de_para"][nome_mp] = tarifa_escolhida
                salvar_config(cfg)
                ok(f"Mapeamento salvo: {nome_mp[:40]}... → {tarifa_escolhida[:30]}...")
                return tarifas[tarifa_escolhida]

    # Camada 4: Fallback manual guiado
    if interativo:
        print(Y+f"\n  ⚠ Atividade sem match: "+C+nome_mp+RS)
        print(DM+"  Informe os dados manualmente (serão salvos no config):"+RS)
        rend_hh = pedir_float("  Rendimento h/ha", 8.0)
        tipo = prompt("  Tipo [manual/mecanizado/semi]", "manual")

        nova_atividade = {
            "rendimento_hh": rend_hh,
            "tipo": tipo,
            "recurso": "homem" if tipo == "manual" else "maquina",
            "eficiencia": 1.0 if tipo == "manual" else 0.5,
            "rendimento_mec": None
        }
        cfg["atividades"][nome_mp] = nova_atividade
        salvar_config(cfg)
        ok(f"Atividade salva: {nome_mp[:50]}...")
        return nova_atividade

    # Modo não-interativo: retorna default
    return {
        "rendimento_hh": 8.0, "tipo": "manual",
        "recurso": "homem", "eficiencia": 1.0,
        "rendimento_mec": None
    }

def garantir_atividade(cfg, atv, interativo=True):
    """Garante que a atividade existe no config, usando reconciliação v4."""
    if atv not in cfg["atividades"]:
        reconciliar_atividade(cfg, atv, interativo)

# ──────────────────────────────────────────────────────────────
#  IMPORTADOR DE TARIFAS (Módulo 7)
# ──────────────────────────────────────────────────────────────
def modulo_importar_tarifas(cfg):
    """Lê Tarifas_e_Rendimento.xlsx e popula config.json → seção tarifas."""
    cabecalho("IMPORTAR TARIFAS")

    arq_tarifas = cfg.get("arquivo_tarifas", "Tarifas e Rendimento.xlsx")
    caminho = os.path.join(DIR, arq_tarifas)

    if not os.path.exists(caminho):
        novo = prompt(f"Arquivo '{arq_tarifas}' não encontrado. Caminho completo")
        if not os.path.exists(novo):
            erro("Arquivo não encontrado."); return
        caminho = novo

    print(DM+f"  Lendo: {caminho}"+RS)

    try:
        df = pd.read_excel(caminho, sheet_name=0)
    except Exception as e:
        erro(f"Erro ao ler arquivo: {e}"); return

    # Mapear colunas
    col_map = {
        'Atividade': 'atividade',
        'Tipo': 'tipo',
        'HH': 'hh',
        'HM': 'hm',
        'Preço Hora': 'preco_hora',
        'Preço Unitário': 'preco_unit',
        'Unidade': 'unidade',
        'Fisíco Mensal': 'fisico_mensal',
        'Físico Total': 'fisico_total'
    }

    tarifas_importadas = {}
    erros = 0

    for _, row in df.iterrows():
        nome = row.get('Atividade')
        if pd.isna(nome) or not str(nome).strip():
            continue

        nome = str(nome).strip()
        tipo = str(row.get('Tipo', 'Manual')).strip()

        hh = row.get('HH')
        hm = row.get('HM')
        preco_hora = row.get('Preço Hora')
        preco_unit = row.get('Preço Unitário')
        unidade = row.get('Unidade', 'Ha')
        fisico_mensal = row.get('Fisíco Mensal', 0)

        # Tratar NaN
        hh = float(hh) if pd.notna(hh) else None
        hm = float(hm) if pd.notna(hm) else None
        preco_hora = float(preco_hora) if pd.notna(preco_hora) else 0
        preco_unit = float(preco_unit) if pd.notna(preco_unit) else 0
        fisico_mensal = float(fisico_mensal) if pd.notna(fisico_mensal) else 0

        tarifas_importadas[nome] = {
            "tipo": tipo,
            "hh": hh,
            "hm": hm,
            "preco_hora": preco_hora,
            "preco_unit": preco_unit,
            "unidade": str(unidade),
            "fisico_mensal": fisico_mensal,
            "rendimento_hh": hh if hh else (hm if hm else 8.0),
            "rendimento_mec": hm,
            "recurso": "homem" if tipo == "Manual" else "maquina",
            "eficiencia": 1.0 if tipo == "Manual" else 0.5
        }

    cfg["tarifas"] = tarifas_importadas
    salvar_config(cfg)

    # Estatísticas
    manuais = sum(1 for t in tarifas_importadas.values() if t["tipo"] == "Manual")
    mecanizadas = sum(1 for t in tarifas_importadas.values() if t["tipo"] == "Mecanizada")
    semi = sum(1 for t in tarifas_importadas.values() if "Semi" in t["tipo"])

    ok(f"Importadas {len(tarifas_importadas)} tarifas!")
    print(G+f"    Manual: {manuais}  |  Mecanizada: {mecanizadas}  |  Semi: {semi}"+RS)

    # Listar algumas
    sub()
    print(G+f"  {'TARIFA':<45} {'TIPO':<12} {'HH':>6} {'HM':>6} {'R$/ha':>10}"+RS)
    sub()
    for i, (nome, t) in enumerate(list(tarifas_importadas.items())[:15]):
        hh_str = f"{t['hh']:.1f}" if t['hh'] else "—"
        hm_str = f"{t['hm']:.2f}" if t['hm'] else "—"
        print(G+f"  {nome[:45]:<45} "+C+f"{t['tipo']:<12}"+G+f" {hh_str:>6} {hm_str:>6}"+Y+f" {t['preco_unit']:>10.2f}"+RS)
    if len(tarifas_importadas) > 15:
        print(DM+f"  ... e mais {len(tarifas_importadas)-15} tarifas"+RS)

    input(DM+"\n  [ENTER para voltar] "+RS)

# ──────────────────────────────────────────────────────────────
#  MÓDULO DE OTIMIZAÇÃO FINANCEIRA (Módulo 8)
# ──────────────────────────────────────────────────────────────
def modulo_otimizacao_financeira(cfg, df):
    """Compara custo manual vs mecanizado e calcula economia potencial."""
    cabecalho("OTIMIZAÇÃO FINANCEIRA")

    tarifas = cfg.get("tarifas", {})
    if not tarifas:
        aviso("Tarifas não importadas. Use o módulo [7] primeiro.")
        input(DM+"  [ENTER para voltar] "+RS)
        return

    fazendas = sorted(df["fazenda"].dropna().unique().tolist())
    fazenda = selecionar("SELECIONE A FAZENDA", fazendas)
    if fazenda is None: return

    df_faz = df[df["fazenda"]==fazenda].copy()

    # Mapeamento de alternativas mecanizadas
    alternativas = {
        "ROÇADA MANUAL": ["ROÇADA MECANIZADA", "ROÇADA SEMIMEC NA LINHA"],
        "CAPINA": ["CAPINA QUÍMICA TOTAL DRONE", "CAPINA PÓS-EMERG TOTAL MEC"],
        "IRRIGAÇÃO": ["IRRIGAÇÃO DE PLANTIO SEMI-MECANIZADA"],
        "PLANTIO": ["PLANTIO SEMIMECANIZADO COM GEL"],
    }

    cabecalho(f"ANÁLISE FINANCEIRA — {fazenda}")
    print(G+f"  {'ATIVIDADE':<35} {'HA':>7} {'R$ MANUAL':>12} {'R$ MEC':>12} {'ECONOMIA':>12}"+RS)
    sub()

    total_manual = 0.0
    total_mec = 0.0
    total_ha = 0.0
    recomendacoes = []

    # Agrupar por atividade
    agg = defaultdict(float)
    for _, row in df_faz.iterrows():
        agg[row["atividade"]] += row["area_ha"]

    for atv, area in sorted(agg.items()):
        # Buscar tarifa via de_para ou direto
        tarifa_nome = cfg.get("de_para", {}).get(atv, atv)
        tarifa_manual = None
        tarifa_mec = None

        # Procurar nos tarifas
        for t_nome, t_dados in tarifas.items():
            if tarifa_nome.upper() in t_nome.upper() or normalizar_nome(atv) in normalizar_nome(t_nome):
                if t_dados["tipo"] == "Manual" and not tarifa_manual:
                    tarifa_manual = t_dados
                elif t_dados["tipo"] in ["Mecanizada", "Semi-Mecanizada"] and not tarifa_mec:
                    tarifa_mec = t_dados

        # Buscar alternativa mecanizada
        if not tarifa_mec:
            for chave, alts in alternativas.items():
                if chave in atv.upper():
                    for alt in alts:
                        if alt in tarifas:
                            tarifa_mec = tarifas[alt]
                            break
                    break

        if tarifa_manual:
            custo_manual = area * tarifa_manual.get("preco_unit", 0)
            total_manual += custo_manual
            total_ha += area

            if tarifa_mec:
                custo_mec = area * tarifa_mec.get("preco_unit", 0)
                total_mec += custo_mec
                economia = custo_manual - custo_mec
                pct = (economia / custo_manual * 100) if custo_manual > 0 else 0

                cor = G if economia > 0 else Y
                print(cor+f"  {atv[:35]:<35} {area:>7.2f} {custo_manual:>12.2f} {custo_mec:>12.2f} {economia:>+12.2f}"+RS)

                if pct > 15 and area > 2:
                    recomendacoes.append({
                        "atividade": atv,
                        "area": area,
                        "economia": economia,
                        "pct": pct
                    })
            else:
                total_mec += custo_manual  # Sem alternativa, mantém manual
                print(DM+f"  {atv[:35]:<35} {area:>7.2f} {custo_manual:>12.2f}"+Y+"      —     "+DM+"     —"+RS)

    linha()
    print(G+BL+f"  TOTAIS"+RS)
    print(G+f"  Área analisada     : {total_ha:,.2f} ha"+RS)
    print(Y+f"  Custo total MANUAL : R$ {total_manual:,.2f}"+RS)
    print(G+f"  Custo total MEC    : R$ {total_mec:,.2f}"+RS)
    economia_total = total_manual - total_mec
    if total_manual > 0:
        pct_total = economia_total / total_manual * 100
        print(C+BL+f"  ECONOMIA POTENCIAL : R$ {economia_total:,.2f} ({pct_total:.1f}%)"+RS)
    linha()

    if recomendacoes:
        print(Y+BL+"\n  🚜 RECOMENDAÇÕES DE MECANIZAÇÃO"+RS)
        sub()
        for rec in sorted(recomendacoes, key=lambda x: -x["economia"]):
            print(G+f"  • {rec['atividade'][:40]:<40}"+C+f" {rec['area']:.1f} ha"+Y+f"  → economia R$ {rec['economia']:,.2f} ({rec['pct']:.0f}%)"+RS)
        print(DM+"\n  Critério: economia >15% e área >2 ha"+RS)

    input(DM+"\n  [ENTER para voltar] "+RS)

# ──────────────────────────────────────────────────────────────
#  ESCOPO DE MESES (Módulo 9)
# ──────────────────────────────────────────────────────────────
def dias_uteis_mes(ano, mes, feriados=None):
    """Calcula dias úteis de um mês (exclui sábados e domingos)."""
    import calendar
    if feriados is None:
        feriados = []

    dias = 0
    cal = calendar.Calendar()
    for dia in cal.itermonthdays2(ano, mes):
        if dia[0] == 0:
            continue
        data = datetime.date(ano, mes, dia[0])
        # 5=sábado, 6=domingo
        if dia[1] < 5 and data not in feriados:
            dias += 1
    return dias

def modulo_escopo_meses(cfg, df):
    """Distribuição de atividades por mês com dias úteis."""
    cabecalho("ESCOPO DE MESES")

    fazendas = sorted(df["fazenda"].dropna().unique().tolist())
    fazenda = selecionar("SELECIONE A FAZENDA", fazendas)
    if fazenda is None: return

    df_faz = df[df["fazenda"]==fazenda].copy()

    # Período
    print(G+"\n  PERÍODO DE EXECUÇÃO"+RS)
    ano = pedir_int("  Ano", datetime.datetime.now().year)
    mes_ini = pedir_int("  Mês inicial (1-12)", 4)
    mes_fim = pedir_int("  Mês final (1-12)", 6)

    if mes_fim < mes_ini:
        mes_fim += 12  # Virada de ano

    meses_nomes = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]

    # Calcular dias úteis
    total_dias_uteis = 0
    meses_info = []
    for m in range(mes_ini, mes_fim + 1):
        mes_real = ((m - 1) % 12) + 1
        ano_real = ano if m <= 12 else ano + 1
        dias = dias_uteis_mes(ano_real, mes_real)
        total_dias_uteis += dias
        meses_info.append({
            "mes": mes_real,
            "ano": ano_real,
            "nome": meses_nomes[mes_real - 1],
            "dias_uteis": dias
        })

    # Calcular demanda total
    ativs = sorted(df_faz["atividade"].unique().tolist())
    jornada = cfg.get("jornada_horas", 4.6)
    colab = cfg["equipes"]["padrao"]["colaboradores"]
    cap_dia = colab * jornada  # Capacidade diária HH

    total_hh = 0.0
    for _, row in df_faz.iterrows():
        atv = row["atividade"]
        garantir_atividade(cfg, atv, interativo=False)
        ac = cfg["atividades"].get(atv, {})
        rend = ac.get("rendimento_hh", 8.0) * ac.get("eficiencia", 1.0)
        total_hh += row["area_ha"] * rend

    cabecalho(f"CRONOGRAMA — {fazenda}")

    print(G+f"  PERÍODO: {meses_info[0]['nome']}/{meses_info[0]['ano']} a {meses_info[-1]['nome']}/{meses_info[-1]['ano']}"+RS)
    print(G+f"  Dias úteis totais: {total_dias_uteis}"+RS)
    print(G+f"  Capacidade/dia: {cap_dia:.1f} HH ({colab} colab × {jornada}h)"+RS)
    print(G+f"  Capacidade total: {cap_dia * total_dias_uteis:.1f} HH"+RS)
    print(G+f"  Demanda total: {total_hh:.1f} HH"+RS)

    sub()
    print(G+f"  {'MÊS':<12} {'DIAS':>6} {'CAP HH':>10} {'DEMANDA':>10} {'STATUS':>12}"+RS)
    sub()

    hh_restante = total_hh
    for m in meses_info:
        cap_mes = m["dias_uteis"] * cap_dia
        demanda_mes = min(hh_restante, cap_mes)
        hh_restante = max(0, hh_restante - cap_mes)

        if hh_restante > 0 and demanda_mes >= cap_mes:
            status = Y+"CAPACIDADE"+RS
        elif hh_restante == 0:
            status = G+"OK"+RS
        else:
            status = C+"FOLGA"+RS

        print(G+f"  {m['nome']}/{m['ano']:<8} {m['dias_uteis']:>6} {cap_mes:>10.1f} {demanda_mes:>10.1f} "+status)

    linha()

    if hh_restante > 0:
        dias_extras = math.ceil(hh_restante / cap_dia)
        print(R+BL+f"  ⚠ ATENÇÃO: Faltam {hh_restante:.1f} HH ({dias_extras} dias extras necessários)"+RS)
    else:
        folga = (cap_dia * total_dias_uteis) - total_hh
        print(G+BL+f"  ✓ Período suficiente. Folga de {folga:.1f} HH"+RS)

    input(DM+"\n  [ENTER para voltar] "+RS)

# ──────────────────────────────────────────────────────────────
#  DADOS
# ──────────────────────────────────────────────────────────────
def carregar_planilha(cfg):
    arq = cfg.get("arquivo","exame.xlsx")
    aba = cfg.get("aba","MICROPLANEJAMENTO_ABRIL_JUNHO")
    candidatos = [
        os.path.join(DIR, arq),
        os.path.join(os.path.expanduser("~"),"Music", arq),
        arq,
    ]
    caminho = next((p for p in candidatos if os.path.exists(p)), None)
    if caminho is None:
        erro(f"Arquivo '{arq}' não encontrado.")
        novo = prompt("Informe o caminho completo do arquivo .xlsx")
        if not os.path.exists(novo):
            erro("Arquivo não encontrado."); sys.exit(1)
        caminho = novo
    print(DM+f"  Carregando: {caminho}"+RS)
    df = pd.read_excel(caminho, sheet_name=aba, header=0, usecols=[2,7,9,20])
    df.columns = ["fazenda","chave","area_ha","atividade"]
    df = df.dropna(subset=["atividade","area_ha","chave"])
    df["area_ha"] = pd.to_numeric(df["area_ha"], errors="coerce").fillna(0)
    return df[df["area_ha"] > 0]

# ──────────────────────────────────────────────────────────────
#  CÁLCULO CENTRAL
# ──────────────────────────────────────────────────────────────
def calcular_item(area_ha, colaboradores, rend_hh, jornada_ef, eficiencia=1.0):
    """Cálculo de uma atividade isolada."""
    if colaboradores <= 0 or jornada_ef <= 0:
        return None
    rend_ef      = rend_hh * eficiencia
    horas_nec    = area_ha * rend_ef
    cap_dia      = colaboradores * jornada_ef
    dias_exatos  = horas_nec / cap_dia
    dias_int     = math.ceil(dias_exatos)
    horas_ultimo = horas_nec % cap_dia
    saldo_h      = (cap_dia - horas_ultimo) if horas_ultimo > 0.001 else 0.0
    pct_uso      = (horas_ultimo / cap_dia)  if horas_ultimo > 0.001 else 1.0
    ha_extra     = (saldo_h / rend_ef)       if rend_ef > 0 else 0.0
    return dict(
        area_ha=area_ha, colaboradores=colaboradores,
        rend_hh=rend_hh, eficiencia=eficiencia, rend_ef=rend_ef,
        jornada=jornada_ef, horas_nec=horas_nec, cap_dia=cap_dia,
        dias_exatos=dias_exatos, dias_int=dias_int,
        saldo_h=saldo_h, pct_uso=pct_uso, ha_extra=ha_extra
    )

def calcular_ut(df_ut, equipe, cfg):
    """Calcula todos os itens de uma UT."""
    itens = []
    for _, row in df_ut.iterrows():
        atv = row["atividade"]
        ac  = cfg["atividades"].get(atv, {})
        eq  = equipe.get(atv, None)
        if eq is None or eq["colab"] <= 0:
            itens.append({
                "atividade": atv, "area_ha": row["area_ha"],
                "horas_nec": 0, "dias_int": 0, "dias_exatos": 0,
                "saldo_h": 0, "colaboradores": 0,
                "rend_hh": ac.get("rendimento_hh",0),
                "jornada": 0, "sem_equipe": True
            })
            continue
        r = calcular_item(
            area_ha       = row["area_ha"],
            colaboradores = eq["colab"],
            rend_hh       = ac.get("rendimento_hh", 8.0),
            jornada_ef    = eq["jornada"],
            eficiencia    = ac.get("eficiencia", 1.0),
        )
        if r:
            r["atividade"] = atv
            r["sem_equipe"] = False
            itens.append(r)

    itens_validos = [it for it in itens if not it.get("sem_equipe")]
    if not itens_validos:
        return itens, 0, 0.0

    dias_ut = max(it["dias_int"] for it in itens_validos)
    saldo_total_hh = 0.0
    for it in itens_validos:
        horas_disponiveis_no_horizonte = it["colaboradores"] * it["jornada"] * dias_ut
        saldo_total_hh += max(0.0, horas_disponiveis_no_horizonte - it["horas_nec"])

    return itens, dias_ut, saldo_total_hh

# ──────────────────────────────────────────────────────────────
#  COLETA DE EQUIPE (reutilizável) — v4: Enter mantém padrão
# ──────────────────────────────────────────────────────────────
def coletar_equipe(ativs, cfg, titulo="MONTAR EQUIPE"):
    print(G+BL+f"\n  {titulo}\n"+RS)
    print(DM+"  Para cada atividade: informe colaboradores e jornada efetiva."+RS)
    print(DM+"  ENTER = manter padrão  |  0 = pular atividade\n"+RS)

    equipe         = {}
    jornada_padrao = cfg.get("jornada_horas", 4.6)
    colab_padrao   = cfg["equipes"]["padrao"]["colaboradores"]

    for i, atv in enumerate(ativs, 1):
        sub("·")
        ac = cfg["atividades"].get(atv, {})
        preco = ""
        if atv in cfg.get("de_para", {}):
            t_nome = cfg["de_para"][atv]
            if t_nome in cfg.get("tarifas", {}):
                preco = f"  R$:{cfg['tarifas'][t_nome].get('preco_unit',0):.2f}/ha"

        print(G+f"  [{i}/{len(ativs)}] "+C+atv+RS)
        print(DM+f"         rend: {ac.get('rendimento_hh',8.0)} h/ha  |  efic: {ac.get('eficiencia',1.0)}"+Y+preco+RS)
        colab   = pedir_int  ("  Colaboradores", colab_padrao, allow_zero=True)
        jornada = pedir_float("  Jornada efetiva (h)", jornada_padrao) if colab > 0 else jornada_padrao
        equipe[atv] = {"colab": colab, "jornada": jornada}

    return equipe

# ──────────────────────────────────────────────────────────────
#  MÓDULO 1: ORÇAR FAZENDA COMPLETA
# ──────────────────────────────────────────────────────────────
def modulo_orcar_fazenda(cfg, df):
    cabecalho("ORÇAR FAZENDA COMPLETA")

    fazendas = sorted(df["fazenda"].dropna().unique().tolist())
    fazenda  = selecionar("SELECIONE A FAZENDA", fazendas)
    if fazenda is None: return

    df_faz = df[df["fazenda"]==fazenda].copy()
    uts    = sorted(df_faz["chave"].unique().tolist())
    ativs  = sorted(df_faz["atividade"].unique().tolist())

    for atv in ativs: garantir_atividade(cfg, atv)
    salvar_config(cfg)

    cabecalho(f"FAZENDA: {fazenda}")
    print(G+f"  {len(uts)} UTs  |  {len(ativs)} atividades distintas\n"+RS)

    sub()
    print(G+"  ATIVIDADES — rendimentos do config.json:"+RS)
    sub()
    for i, atv in enumerate(ativs, 1):
        ac   = cfg["atividades"][atv]
        rend = ac.get("rendimento_hh", 8.0)
        efic = ac.get("eficiencia", 1.0)
        rmec = ac.get("rendimento_mec")
        tag  = (Y+" [MEC disponível]"+RS) if rmec else ""
        cor  = Y if efic < 1.0 else G
        print(cor+f"  {i:2}. {atv:<52}"+C+f"{rend:6.2f} h/ha"+tag+RS)
    sub()

    equipe = coletar_equipe(ativs, cfg)

    resultados_ut = []
    for chave in uts:
        df_ut = df_faz[df_faz["chave"]==chave]
        area_ut = df_ut["area_ha"].iloc[0]
        itens, dias_ut, saldo_hh = calcular_ut(df_ut, equipe, cfg)
        resultados_ut.append({
            "chave": chave, "area_ha": area_ut,
            "itens": itens, "dias_ut": dias_ut,
            "saldo_hh": saldo_hh
        })

    exibir_relatorio_fazenda(fazenda, resultados_ut, equipe)

    resp = prompt("\n  Exportar relatório .txt? [s/n]", "s")
    if resp.lower() == "s":
        exportar_txt(fazenda, resultados_ut, equipe)

    input(DM+"\n  [ENTER para voltar ao menu] "+RS)

# ──────────────────────────────────────────────────────────────
#  MÓDULO 2: SPRINT — v4: colaboradores por atividade
# ──────────────────────────────────────────────────────────────
def modulo_sprint(cfg, df):
    cabecalho("SPRINT — SIMULAÇÃO RÁPIDA")

    fazendas = sorted(df["fazenda"].dropna().unique().tolist())
    fazenda  = selecionar("SELECIONE A FAZENDA", fazendas)
    if fazenda is None: return

    df_faz = df[df["fazenda"]==fazenda].copy()
    uts    = sorted(df_faz["chave"].unique().tolist())
    ativs  = sorted(df_faz["atividade"].unique().tolist())
    for atv in ativs: garantir_atividade(cfg, atv)

    print(G+"\n  ESCOPO DO SPRINT"+RS)
    print(G+"  [1] "+C+"Fazenda inteira"+RS)
    print(G+"  [2] "+C+"Uma UT específica"+RS)
    escopo = prompt("Escolha", "1")

    if escopo == "2":
        ut_sel = selecionar("SELECIONE A UT", uts)
        if ut_sel is None: return
        df_alvo = df_faz[df_faz["chave"]==ut_sel]
        titulo_alvo = f"UT {ut_sel}"
    else:
        df_alvo    = df_faz
        titulo_alvo = fazenda

    ativs_alvo = sorted(df_alvo["atividade"].unique().tolist())

    print(G+"\n  FILTRAR ATIVIDADES?"+RS)
    print(G+"  [1] "+C+"Todas as atividades"+RS)
    print(G+"  [2] "+C+"Escolher atividades específicas"+RS)
    filtro_resp = prompt("Escolha", "1")

    ativs_sprint = ativs_alvo
    if filtro_resp == "2":
        selecionadas = []
        print(G+"\n  Marque as atividades (s/n para cada):"+RS)
        for atv in ativs_alvo:
            resp = prompt(f"  Incluir '{atv[:50]}'? [s/n]", "s")
            if resp.lower() != "n":
                selecionadas.append(atv)
        if not selecionadas:
            aviso("Nenhuma atividade selecionada."); return
        ativs_sprint = selecionadas

    # v4: Escolha do modo de equipe
    print(G+"\n  MODO DE EQUIPE"+RS)
    print(G+"  [1] "+C+"Pool único (mesma equipe para todas)"+RS)
    print(G+"  [2] "+C+"Colaboradores por atividade"+RS)
    modo_equipe = prompt("Escolha", "1")

    if modo_equipe == "2":
        equipe_sprint = coletar_equipe(ativs_sprint, cfg, "EQUIPE DO SPRINT")
    else:
        sub()
        print(G+"  EQUIPE ÚNICA DO SPRINT\n"+RS)
        colab   = pedir_int  ("  Colaboradores", cfg["equipes"]["padrao"]["colaboradores"])
        jornada = pedir_float("  Jornada efetiva (h)", cfg.get("jornada_horas", 4.6))
        equipe_sprint = {atv: {"colab": colab, "jornada": jornada} for atv in ativs_sprint}

    cabecalho(f"SPRINT — {titulo_alvo}")
    sub()
    print(G+f"  {'ATIVIDADE':<50} {'TOT HA':>8} {'TOT HH':>8} {'DIAS':>6}"+RS)
    sub()

    total_dias_seq   = 0
    total_hh         = 0.0
    total_ha_sprint  = 0.0
    max_dias_paralelo = 0

    agg = defaultdict(float)
    for _, row in df_alvo[df_alvo["atividade"].isin(ativs_sprint)].iterrows():
        agg[row["atividade"]] += row["area_ha"]

    for atv in sorted(agg.keys()):
        ac   = cfg["atividades"].get(atv, {})
        area = agg[atv]
        eq   = equipe_sprint.get(atv, {})
        colab = eq.get("colab", 4)
        jornada = eq.get("jornada", 4.6)

        r = calcular_item(area, colab, ac.get("rendimento_hh",8.0),
                         jornada, ac.get("eficiencia",1.0))
        if r:
            total_dias_seq    += r["dias_int"]
            total_hh          += r["horas_nec"]
            total_ha_sprint   += area
            max_dias_paralelo  = max(max_dias_paralelo, r["dias_int"])
            print(G+f"  {atv:<50}"+C+f" {area:>8.3f}"+G+f" {r['horas_nec']:>8.1f}"+BL+f" {r['dias_int']:>5}d"+RS)

    linha()
    print(G+f"  Total área           : {total_ha_sprint:.3f} ha"+RS)
    print(G+f"  Total horas-homem    : {total_hh:.1f} h"+RS)
    print(Y+BL+f"  Prazo SEQUENCIAL     : {total_dias_seq} dia(s)"+RS)
    print(C+BL+f"  Prazo PARALELO       : {max_dias_paralelo} dia(s)"+RS)
    print(DM+"  Sequencial = uma atividade após a outra"+RS)
    print(DM+"  Paralelo   = equipes independentes simultaneamente"+RS)
    linha()

    input(DM+"\n  [ENTER para voltar ao menu] "+RS)

# ──────────────────────────────────────────────────────────────
#  MÓDULO 3: COMPARATIVO MEC vs MANUAL
# ──────────────────────────────────────────────────────────────
def modulo_comparativo_mec(cfg, df):
    cabecalho("COMPARATIVO: MANUAL vs MECANIZADO")

    fazendas = sorted(df["fazenda"].dropna().unique().tolist())
    fazenda  = selecionar("SELECIONE A FAZENDA", fazendas)
    if fazenda is None: return

    df_faz = df[df["fazenda"]==fazenda].copy()
    ativs  = sorted(df_faz["atividade"].unique().tolist())
    for atv in ativs: garantir_atividade(cfg, atv)

    ativs_mec = [a for a in ativs if cfg["atividades"][a].get("rendimento_mec")]

    if not ativs_mec:
        aviso("Nenhuma atividade desta fazenda tem 'rendimento_mec' no config.")
        print(DM+"  Configure via Menu Principal > opção 4 (campo rendimento_mec).\n"+RS)
        input(DM+"  [ENTER para voltar] "+RS)
        return

    print(G+"\n  Atividades com rendimento mecanizado configurado:"+RS)
    for atv in ativs_mec:
        ac = cfg["atividades"][atv]
        print(G+f"  · {atv:<52}"+C+f"manual {ac['rendimento_hh']:.1f} h/ha  |  mec {ac['rendimento_mec']:.1f} h/ha"+RS)

    sub()
    print(G+"  EQUIPE PARA O COMPARATIVO\n"+RS)
    colab_manual = pedir_int  ("  Colaboradores (modo manual)",    cfg["equipes"]["padrao"]["colaboradores"])
    jornada      = pedir_float("  Jornada efetiva (h)",            cfg.get("jornada_horas",4.6))
    colab_mec    = pedir_int  ("  Operadores (modo mecanizado)",   1)

    agg = defaultdict(float)
    for _, row in df_faz[df_faz["atividade"].isin(ativs_mec)].iterrows():
        agg[row["atividade"]] += row["area_ha"]

    cabecalho(f"COMPARATIVO — {fazenda}")
    print(G+f"  {'ATIVIDADE':<48} {'HA':>7} {'MAN dias':>9} {'MEC dias':>9} {'GANHO':>7}"+RS)
    sub()

    total_man = 0; total_mec = 0; total_ha = 0.0

    for atv in sorted(agg.keys()):
        ac   = cfg["atividades"][atv]
        area = agg[atv]
        r_man = calcular_item(area, colab_manual, ac["rendimento_hh"],   jornada, ac.get("eficiencia",1.0))
        r_mec = calcular_item(area, colab_mec,    ac["rendimento_mec"],  jornada, 1.0)
        if r_man and r_mec:
            ganho = r_man["dias_int"] - r_mec["dias_int"]
            cor   = G if ganho > 0 else Y
            print(
                G+f"  {atv:<48}"+C+f" {area:>7.3f}"
                +Y+f" {r_man['dias_int']:>8}d"
                +G+f" {r_mec['dias_int']:>8}d"
                +cor+f" {ganho:>+6}d"+RS
            )
            total_man += r_man["dias_int"]
            total_mec += r_mec["dias_int"]
            total_ha  += area

    linha()
    print(G+f"  Área total analisada : {total_ha:.3f} ha"+RS)
    print(Y+BL+f"  Total MANUAL         : {total_man} dia(s)"+RS)
    print(G+BL+f"  Total MECANIZADO     : {total_mec} dia(s)"+RS)
    if total_man > 0:
        red = ((total_man - total_mec) / total_man) * 100
        print(C+BL+f"  Redução de prazo     : {red:.1f}%"+RS)
    linha()

    input(DM+"\n  [ENTER para voltar ao menu] "+RS)

# ──────────────────────────────────────────────────────────────
#  EXIBIÇÃO DO RELATÓRIO FAZENDA
# ──────────────────────────────────────────────────────────────
def exibir_relatorio_fazenda(fazenda, resultados_ut, equipe):
    cabecalho(f"RELATÓRIO — {fazenda}")

    total_dias = 0; total_hh = 0.0; total_ha = 0.0
    total_saldo_hh = 0.0

    for rut in resultados_ut:
        linha("─")
        print(G+BL+f"  UT: {rut['chave']}"+RS+G+f"  |  {rut['area_ha']:.3f} ha"+RS)
        sub("·")
        print(G+f"  {'ATIVIDADE':<48} {'HA':>7} {'HH':>7} {'DIAS':>5}"+RS)
        sub("·")
        for it in rut["itens"]:
            if it.get("sem_equipe"):
                print(DM+f"  {it['atividade']:<48} {it['area_ha']:>7.3f}"+Y+"  [SEM EQUIPE]"+RS)
            else:
                print(G+f"  {it['atividade']:<48}"+C+f" {it['area_ha']:>7.3f}"
                      +G+f" {it['horas_nec']:>7.1f}"+BL+f" {it['dias_int']:>4}d"+RS)
        sub("·")
        cor_saldo = G if rut["saldo_hh"] < (rut["dias_ut"] * 4) else Y
        print(G+f"  {'Duração da UT':>48}"+BL+f" {rut['dias_ut']:>4}d"+RS)
        print(cor_saldo+f"  {'Saldo HH ocioso':>48} {rut['saldo_hh']:>7.1f}h"+RS)

        total_dias     = max(total_dias, rut["dias_ut"])
        total_hh      += sum(it["horas_nec"] for it in rut["itens"] if not it.get("sem_equipe"))
        total_ha      += rut["area_ha"]
        total_saldo_hh += rut["saldo_hh"]

    linha()
    print(G+BL+f"  CONSOLIDADO — {fazenda}"+RS)
    sub()
    print(G+f"  UTs analisadas         : {len(resultados_ut)}"+RS)
    print(G+f"  Área total (ha)        : {total_ha:.3f}"+RS)
    print(G+f"  Total horas-homem      : {total_hh:.1f} h"+RS)
    print(Y+f"  Saldo HH ocioso total  : {total_saldo_hh:.1f} h"+RS)
    print(Y+BL+f"  PRAZO ESTIMADO         : {total_dias} dia(s) úteis"+RS)
    print(DM+"  (Prazo = UT mais longa; atividades distintas trabalham em paralelo)"+RS)
    linha()

    print(G+"\n  RESUMO POR ATIVIDADE\n"+RS)
    print(G+f"  {'ATIVIDADE':<48} {'TOT HA':>8} {'TOT HH':>8} {'COLAB':>6} {'JORN':>5}"+RS)
    sub()
    agg = defaultdict(lambda: {"ha":0.0,"hh":0.0})
    for rut in resultados_ut:
        for it in rut["itens"]:
            if not it.get("sem_equipe"):
                agg[it["atividade"]]["ha"] += it["area_ha"]
                agg[it["atividade"]]["hh"] += it["horas_nec"]
    for atv in sorted(agg.keys()):
        eq = equipe.get(atv, {})
        print(G+f"  {atv:<48}"+C+f" {agg[atv]['ha']:>8.3f}"
              +G+f" {agg[atv]['hh']:>8.1f}"
              +G+f" {str(eq.get('colab','-')):>6}"
              +G+f" {str(eq.get('jornada','-')):>5}"+RS)
    sub()

# ──────────────────────────────────────────────────────────────
#  EXPORTAR .TXT
# ──────────────────────────────────────────────────────────────
def exportar_txt(fazenda, resultados_ut, equipe):
    ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    nome = f"ATM_{fazenda.replace(' ','_').replace('/','_')[:30]}_{ts}.txt"
    dest = os.path.join(DIR, nome)
    sep  = "=" * 66; sep2 = "-" * 66
    L    = []

    L += [sep, f"  RESTAURAÇÃO FLORESTAL — RELATÓRIO DE ORÇAMENTO v{VERSION}".center(66),
          f"  Fazenda : {fazenda}",
          f"  Gerado  : {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", sep]

    total_dias=0; total_hh=0.0; total_ha=0.0; total_saldo=0.0

    for rut in resultados_ut:
        L += [f"\n  UT: {rut['chave']}  |  {rut['area_ha']:.3f} ha", sep2,
              f"  {'ATIVIDADE':<48} {'HA':>7} {'HH':>7} {'DIAS':>5}", sep2]
        for it in rut["itens"]:
            if it.get("sem_equipe"):
                L.append(f"  {it['atividade']:<48} {it['area_ha']:>7.3f}  [SEM EQUIPE]")
            else:
                L.append(f"  {it['atividade']:<48} {it['area_ha']:>7.3f}"
                         f" {it['horas_nec']:>7.1f} {it['dias_int']:>4}d")
        L += [sep2,
              f"  {'Duração da UT':>50}  {rut['dias_ut']:>3}d",
              f"  {'Saldo HH ocioso':>50}  {rut['saldo_hh']:>6.1f}h"]
        total_dias  = max(total_dias, rut["dias_ut"])
        total_hh   += sum(it["horas_nec"] for it in rut["itens"] if not it.get("sem_equipe"))
        total_ha   += rut["area_ha"]
        total_saldo += rut["saldo_hh"]

    L += ["\n"+sep, "  TOTAIS DA FAZENDA", sep2,
          f"  UTs                : {len(resultados_ut)}",
          f"  Área total (ha)    : {total_ha:.3f}",
          f"  Horas-homem totais : {total_hh:.1f} h",
          f"  Saldo HH ocioso    : {total_saldo:.1f} h",
          f"  PRAZO ESTIMADO     : {total_dias} dia(s) úteis", sep,
          "\n  EQUIPE CONFIGURADA", sep2]
    for atv, eq in sorted(equipe.items()):
        L.append(f"  {atv:<52} {eq['colab']} colab.  {eq['jornada']:.1f}h efetiva")
    L.append(sep)

    with open(dest,"w",encoding="utf-8") as f:
        f.write("\n".join(L))
    ok(f"Relatório salvo: {dest}")

# ──────────────────────────────────────────────────────────────
#  MÓDULO: RENDIMENTOS
# ──────────────────────────────────────────────────────────────
def modulo_rendimentos(cfg, df):
    ativs = sorted(df["atividade"].dropna().unique().tolist())
    for atv in ativs: garantir_atividade(cfg, atv, interativo=False)
    salvar_config(cfg)

    while True:
        cabecalho("CONFIGURAR RENDIMENTOS ORÇADOS")
        print(G+f"  {'#':>3}  {'ATIVIDADE':<48} {'h/ha':>6} {'EFIC':>5} {'MEC h/ha':>9}"+RS)
        sub()
        for i, atv in enumerate(ativs, 1):
            ac   = cfg["atividades"].get(atv,{})
            rend = ac.get("rendimento_hh",0)
            efic = ac.get("eficiencia",1.0)
            mec  = ac.get("rendimento_mec")
            mec_str = f"{mec:.2f}" if mec else "  —"
            cor  = Y if efic < 1.0 else G
            print(cor+f"  [{i:2}]  {atv:<48} {rend:>6.2f} {efic:>5.2f} {mec_str:>9}"+RS)
        print(G+f"\n  [ 0]  "+DM+"Voltar"+RS)
        sub()
        v = prompt("Número para editar")
        if v=="0": return
        if not v.isdigit() or not (1<=int(v)<=len(ativs)):
            aviso("Inválido."); continue
        atv = ativs[int(v)-1]
        ac  = cfg["atividades"][atv]
        print(G+f"\n  Editando: "+C+atv+RS)
        ac["rendimento_hh"] = pedir_float("Rendimento manual h/ha (orçado)", ac.get("rendimento_hh",8.0))
        ac["eficiencia"]    = min(max(pedir_float(
            "Eficiência (1.0=manual | 0.5=mec padrão)",
            ac.get("eficiencia",1.0)),0.01),1.0)
        ac["tipo"]    = prompt("Tipo [manual/mecanizado/semimecanizado]", ac.get("tipo","manual"))
        ac["recurso"] = prompt("Recurso [homem/maquina]", ac.get("recurso","homem"))
        resp_mec = prompt("Configurar rendimento mecanizado? [s/n]", "n")
        if resp_mec.lower() == "s":
            ac["rendimento_mec"] = pedir_float(
                "Rendimento MECANIZADO h/ha (menor = mais rápido)",
                ac.get("rendimento_mec") or ac["rendimento_hh"] * 0.3)
        salvar_config(cfg)
        ok(f"Salvo: {atv}")
        input(DM+"  [ENTER] "+RS)

# ──────────────────────────────────────────────────────────────
#  MÓDULO: EQUIPE PADRÃO
# ──────────────────────────────────────────────────────────────
def modulo_equipe(cfg):
    cabecalho("PARÂMETROS PADRÃO")
    j = cfg.get("jornada_horas", 4.6)
    c = cfg["equipes"]["padrao"]["colaboradores"]
    print(G+f"  Jornada padrão    : {BL}{j} h/dia{RS}")
    print(G+f"  Colaboradores     : {BL}{c}{RS}\n")
    cfg["jornada_horas"]                      = pedir_float("Nova jornada padrão (h)", j)
    cfg["equipes"]["padrao"]["colaboradores"] = pedir_int  ("Novo nº colaboradores", c)
    salvar_config(cfg)
    ok("Parâmetros salvos.")
    input(DM+"\n  [ENTER para voltar] "+RS)

# ──────────────────────────────────────────────────────────────
#  MÓDULO: CATÁLOGO
# ──────────────────────────────────────────────────────────────
def modulo_catalogo(df):
    cabecalho("CATÁLOGO DE DADOS")
    fazendas = sorted(df["fazenda"].dropna().unique().tolist())
    fazenda  = selecionar("FILTRAR POR FAZENDA (0 = todas)", fazendas, zero_label="Todas")
    filtro   = df if fazenda is None else df[df["fazenda"]==fazenda]
    cabecalho("CATÁLOGO")
    print(G+f"  {'FAZENDA':<28} {'UT':<14} {'ATIVIDADE':<40} {'HA':>7}"+RS)
    sub()
    for _, row in filtro.iterrows():
        print(DM+f"  {str(row['fazenda'])[:28]:<28} "
              +G+f"{str(row['chave']):<14} "
              +C+f"{str(row['atividade'])[:40]:<40} "
              +BL+f"{row['area_ha']:>7.3f}"+RS)
    sub()
    print(G+BL+f"  TOTAL ha: {filtro['area_ha'].sum():.3f}"+RS)
    input(DM+"\n  [ENTER para voltar] "+RS)

# ──────────────────────────────────────────────────────────────
#  MÓDULO: VER MAPEAMENTOS de_para
# ──────────────────────────────────────────────────────────────
def modulo_ver_mapeamentos(cfg):
    cabecalho("MAPEAMENTOS de_para")
    de_para = cfg.get("de_para", {})

    if not de_para:
        aviso("Nenhum mapeamento salvo ainda.")
        print(DM+"  Os mapeamentos são criados automaticamente quando o sistema"+RS)
        print(DM+"  encontra uma atividade nova e você confirma uma tarifa correspondente."+RS)
    else:
        print(G+f"  {'ATIVIDADE MICROPLANEJAMENTO':<45} → {'TARIFA ORÇADA':<30}"+RS)
        sub()
        for mp, tarifa in sorted(de_para.items()):
            print(G+f"  {mp[:45]:<45}"+C+f" → {tarifa[:30]}"+RS)
        sub()
        print(G+f"  Total: {len(de_para)} mapeamentos"+RS)

    input(DM+"\n  [ENTER para voltar] "+RS)

# ──────────────────────────────────────────────────────────────
#  MENU PRINCIPAL — v4
# ──────────────────────────────────────────────────────────────
def menu(cfg, df):
    opcoes = [
        ("1", "Orçar fazenda completa  (UT × atividade × equipe)"),
        ("2", "Sprint — simulação rápida por função/alvo"),
        ("3", "Comparativo Manual vs Mecanizado (prazo)"),
        ("─", "─"*50),
        ("4", "Configurar rendimentos orçados (h/ha)"),
        ("5", "Configurar equipe e jornada padrão"),
        ("6", "Ver catálogo de dados"),
        ("─", "─"*50),
        ("7", "📥 Importar tarifas (Tarifas_e_Rendimento.xlsx)"),
        ("8", "💰 Otimização financeira (mec vs manual → R$)"),
        ("9", "📅 Escopo de meses (dias úteis)"),
        ("M", "🔗 Ver mapeamentos de_para"),
        ("─", "─"*50),
        ("0", "Sair"),
    ]
    while True:
        cabecalho()
        nf = df["fazenda"].nunique(); nu = df["chave"].nunique(); na = df["atividade"].nunique()
        nt = len(cfg.get("tarifas", {})); nm = len(cfg.get("de_para", {}))
        print(G+f"  Base: "+C+f"{nf} fazendas  ·  {nu} UTs  ·  {na} atividades"+RS)
        print(G+f"  Config: "+C+f"{nt} tarifas importadas  ·  {nm} mapeamentos de_para"+RS)
        sub()
        for cod,desc in opcoes:
            if cod == "─":
                print(DM+f"  {desc}"+RS)
            else:
                print(G+f"  [{cod}] "+C+desc+RS)
        sub()
        v = prompt("Opção").strip().upper()
        if   v=="1": modulo_orcar_fazenda(cfg, df)
        elif v=="2": modulo_sprint(cfg, df)
        elif v=="3": modulo_comparativo_mec(cfg, df)
        elif v=="4": modulo_rendimentos(cfg, df)
        elif v=="5": modulo_equipe(cfg)
        elif v=="6": modulo_catalogo(df)
        elif v=="7": modulo_importar_tarifas(cfg)
        elif v=="8": modulo_otimizacao_financeira(cfg, df)
        elif v=="9": modulo_escopo_meses(cfg, df)
        elif v=="M": modulo_ver_mapeamentos(cfg)
        elif v=="0": sair()
        else: aviso("Opção inválida.")

# ──────────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────────
def main():
    cabecalho()
    print(G+DM+"  Inicializando sistema...\n"+RS)
    cfg = carregar_config()
    df  = carregar_planilha(cfg)
    ok(f"Dados carregados. {len(df)} registros  |  "
       f"{df['fazenda'].nunique()} fazendas  |  {df['chave'].nunique()} UTs")

    # Info sobre tarifas
    nt = len(cfg.get("tarifas", {}))
    if nt > 0:
        print(G+f"  Tarifas: {nt} importadas"+RS)
    else:
        print(Y+"  ⚠ Tarifas não importadas. Use opção [7] no menu."+RS)

    input(DM+"  [ENTER para continuar] "+RS)
    menu(cfg, df)

if __name__=="__main__":
    main()
