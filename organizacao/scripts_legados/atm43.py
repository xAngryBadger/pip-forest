"""
SRF - Sistema de Restauracao Florestal  v4.2
Autor: Isaac (Zaza)
Uso  : python atm3.py

Changelog v4.2 (Redesign Visual Completo):
  - Interface moderna com cores RGB 256 e bordas Unicode
  - Fallback automatico para terminais sem suporte
  - Picker interativo para selecao de opcoes
  - Dashboard de status com informacoes visuais
  - Tabelas formatadas com bordas profissionais
  - Renomeado de ATM para SRF (Sistema Restauracao Florestal)

Changelog v4.1 (Otimizacao de UX + Correcoes):
  - Removidos emojis para interface CLI profissional
  - Adicionadas validacoes de pre-requisitos nos modulos 8 e 9
  - Modulo 9: opcao de ajustar colaboradores temporariamente
  - Modulo 8: melhorado matching usando fuzzy existente
  - Modulo M: permite editar/deletar mapeamentos interativamente

Changelog v4.0:
  - Motor de reconciliacao com de_para + fuzzy matching
  - Importador de tarifas (Tarifas_e_Rendimento.xlsx)
  - Modulo de otimizacao financeira (mec vs manual)
  - Seletor de intensidade para atividades com classes I-V
  - Fallback guiado para atividades novas
  - Sprint melhorado com colaboradores por atividade
  - Escopo de meses com dias uteis
"""

import os, sys, json, math, datetime
import pandas as pd
from collections import defaultdict
from difflib import get_close_matches

# ══════════════════════════════════════════════════════════════════════════════
#  SISTEMA DE DETECCAO DE TERMINAL E FALLBACK
# ══════════════════════════════════════════════════════════════════════════════
def detectar_capacidades_terminal():
    """Detecta se o terminal suporta Unicode e cores RGB."""
    # Windows 10+ com PowerShell ou CMD sempre suporta Unicode agora
    # Colorama faz fallback automatico para cores
    if sys.platform == 'win32':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleOutputCP(65001)  # UTF-8
        except:
            pass
        # Força para true no Windows (PowerShell 7+, Windows Terminal, VS Code)
        supports_unicode = True
        supports_rgb = True
    else:
        # Linux e MacOS sempre suportam
        supports_unicode = True
        supports_rgb = True

    return {
        'unicode': supports_unicode,
        'rgb': supports_rgb,
        'modern': True  # Assume moderno com colorama
    }

TERM_CAPS = detectar_capacidades_terminal()

# ══════════════════════════════════════════════════════════════════════════════
#  PALETA DE CORES (RGB 256 + Fallback ANSI)
# ══════════════════════════════════════════════════════════════════════════════
class Colors:
    def __init__(self, use_rgb=True):
        self.RESET = "\033[0m"
        self.BOLD = "\033[1m"
        self.DIM = "\033[2m"
        self.ITALIC = "\033[3m"
        self.UNDERLINE = "\033[4m"

        if use_rgb and TERM_CAPS['rgb']:
            self.GREEN = "\033[38;5;46m"
            self.DARK_GREEN = "\033[38;5;28m"
            self.CYAN = "\033[38;5;51m"
            self.YELLOW = "\033[38;5;226m"
            self.RED = "\033[38;5;196m"
            self.WHITE = "\033[38;5;231m"
            self.GRAY = "\033[38;5;245m"
            self.ORANGE = "\033[38;5;208m"
            self.BLUE = "\033[38;5;33m"
            self.MAGENTA = "\033[38;5;199m"
        else:
            self.GREEN = "\033[92m"
            self.DARK_GREEN = "\033[32m"
            self.CYAN = "\033[96m"
            self.YELLOW = "\033[93m"
            self.RED = "\033[91m"
            self.WHITE = "\033[97m"
            self.GRAY = "\033[90m"
            self.ORANGE = "\033[93m"
            self.BLUE = "\033[94m"
            self.MAGENTA = "\033[95m"

try:
    import colorama
    colorama.init()
except ImportError:
    pass

C = Colors(use_rgb=True)

# ══════════════════════════════════════════════════════════════════════════════
#  CARACTERES DE BORDA (Unicode + Fallback ASCII)
# ══════════════════════════════════════════════════════════════════════════════
class Box:
    def __init__(self, use_unicode=True):
        if use_unicode and TERM_CAPS['unicode']:
            self.TL = "╔"; self.TR = "╗"; self.BL = "╚"; self.BR = "╝"
            self.H = "═"; self.V = "║"
            self.LT = "╠"; self.RT = "╣"; self.TT = "╦"; self.BT = "╩"; self.X = "╬"
            self.tl = "┌"; self.tr = "┐"; self.bl = "└"; self.br = "┘"
            self.h = "─"; self.v = "│"
            self.lt = "├"; self.rt = "┤"; self.tt = "┬"; self.bt = "┴"; self.x = "┼"
            self.CHECK = "OK"; self.CROSS = "X"; self.WARN = "!"; self.ARROW = ">"; self.BULLET = "*"
        else:
            self.TL = "+"; self.TR = "+"; self.BL = "+"; self.BR = "+"
            self.H = "="; self.V = "|"
            self.LT = "+"; self.RT = "+"; self.TT = "+"; self.BT = "+"; self.X = "+"
            self.tl = "+"; self.tr = "+"; self.bl = "+"; self.br = "+"
            self.h = "-"; self.v = "|"
            self.lt = "+"; self.rt = "+"; self.tt = "+"; self.bt = "+"; self.x = "+"
            self.CHECK = "[OK]"; self.CROSS = "[X]"; self.WARN = "[!]"; self.ARROW = ">"; self.BULLET = "*"

B = Box(use_unicode=True)

# ══════════════════════════════════════════════════════════════════════════════
#  CONSTANTES
# ══════════════════════════════════════════════════════════════════════════════
W = 76
VERSION = "4.2"
APP_NAME = "Sistema de Restauracao Florestal"
APP_SHORT = "SRF"

ASCII_LOGO = f"""
{C.GREEN}                     .o00o
                   o000000oo
                  00000000000o
                  0000000000000
           {C.DARK_GREEN}         \\  |  /
                    {C.DARK_GREEN} | | |
    {C.GREEN} _{C.DARK_GREEN}.._.._.._.._.._ {C.DARK_GREEN}| | |{C.GREEN} _.._.._.._.._.._{C.RESET}
"""

# ══════════════════════════════════════════════════════════════════════════════
#  COMPONENTES DE UI
# ══════════════════════════════════════════════════════════════════════════════
def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def draw_line(char=None, width=W, color=None):
    if char is None: char = B.H
    if color is None: color = C.DARK_GREEN
    print(color + char * width + C.RESET)

def draw_box_top(width=W, color=None):
    if color is None: color = C.DARK_GREEN
    print(color + B.TL + B.H * (width - 2) + B.TR + C.RESET)

def draw_box_bottom(width=W, color=None):
    if color is None: color = C.DARK_GREEN
    print(color + B.BL + B.H * (width - 2) + B.BR + C.RESET)

def draw_box_separator(width=W, color=None):
    if color is None: color = C.DARK_GREEN
    print(color + B.LT + B.H * (width - 2) + B.RT + C.RESET)

def draw_box_line(text, width=W, align='left', color=None, text_color=None):
    if color is None: color = C.DARK_GREEN
    if text_color is None: text_color = C.WHITE
    inner_width = width - 4
    if align == 'center':
        pad_left = (inner_width - len(text)) // 2
        pad_right = inner_width - len(text) - pad_left
        content = " " * pad_left + text + " " * pad_right
    elif align == 'right':
        content = text.rjust(inner_width)
    else:
        content = text.ljust(inner_width)
    print(f"{color}{B.V}{C.RESET} {text_color}{content}{C.RESET} {color}{B.V}{C.RESET}")

def draw_header(title="", subtitle=""):
    clear_screen()
    print(ASCII_LOGO)
    draw_box_top()
    main_title = f" {APP_SHORT} | {title} " if title else f" {APP_NAME} "
    draw_box_line(main_title, align='center', text_color=C.BOLD + C.GREEN)
    if subtitle:
        draw_box_separator()
        draw_box_line(subtitle, align='center', text_color=C.GRAY)
    draw_box_separator()
    now = datetime.datetime.now().strftime("%d/%m/%Y  %H:%M")
    draw_box_line(f"v{VERSION}  {B.BULLET}  {now}", align='center', text_color=C.DIM + C.GRAY)
    draw_box_bottom()
    print()

def msg_ok(text): print(f"  {C.GREEN}[{B.CHECK}]{C.RESET} {C.WHITE}{text}{C.RESET}")
def msg_warn(text): print(f"  {C.YELLOW}[{B.WARN}]{C.RESET} {C.WHITE}{text}{C.RESET}")
def msg_error(text): print(f"  {C.RED}[{B.CROSS}]{C.RESET} {C.WHITE}{text}{C.RESET}")
def aviso(m): msg_warn(m)
def erro(m): msg_error(m)
def ok(m): msg_ok(m)

def prompt(msg, default=None):
    def_str = f" {C.DIM}[{default}]{C.RESET}" if default is not None else ""
    try:
        ans = input(f"  {C.CYAN}{B.ARROW}{C.RESET} {msg}{def_str}: {C.GREEN}")
        print(C.RESET, end="")
        return ans.strip() or (str(default) if default is not None else "")
    except (KeyboardInterrupt, EOFError):
        print(C.RESET); sair()

def pause(msg="Pressione ENTER para voltar"):
    print()
    input(f"  {C.GRAY}{msg}...{C.RESET}")

def pedir_float(msg, default):
    while True:
        v = prompt(msg, default)
        try:
            f = float(str(v).replace(",", "."))
            if f > 0: return f
        except ValueError: pass
        msg_warn("Valor invalido. Informe um numero positivo.")

def pedir_int(msg, default, allow_zero=False):
    while True:
        v = prompt(msg, default)
        try:
            i = int(v)
            if i > 0 or (allow_zero and i >= 0): return i
        except ValueError: pass
        msg_warn("Valor invalido. Informe um numero inteiro positivo.")

def selecionar(titulo, itens, zero_label="Voltar"):
    if not itens:
        msg_warn("Nenhum item disponivel para selecao.")
        return None
    page_size = 12
    page = 0
    total_pages = (len(itens) - 1) // page_size + 1

    while True:
        print(f"\n  {C.DARK_GREEN}{B.tl}{B.h} {C.WHITE}{titulo} {C.DARK_GREEN}{B.h * max(0, W - len(titulo) - 8)}{B.tr}{C.RESET}")
        start = page * page_size
        end = min(start + page_size, len(itens))
        for i in range(start, end):
            num = i + 1
            item = str(itens[i])[:W-12]
            print(f"  {C.DARK_GREEN}{B.v}{C.RESET} {C.GREEN}[{num:2}]{C.RESET} {C.CYAN}{item:<{W-12}}{C.RESET} {C.DARK_GREEN}{B.v}{C.RESET}")
        for _ in range(page_size - (end - start)):
            print(f"  {C.DARK_GREEN}{B.v}{C.RESET} {' ' * (W - 6)} {C.DARK_GREEN}{B.v}{C.RESET}")
        print(f"  {C.DARK_GREEN}{B.lt}{B.h * (W - 4)}{B.rt}{C.RESET}")
        if total_pages > 1:
            nav = f"Pag {page + 1}/{total_pages} | [N]ext [P]rev | [0] {zero_label}"
        else:
            nav = f"{len(itens)} itens | [0] {zero_label}"
        print(f"  {C.DARK_GREEN}{B.v}{C.RESET} {C.GRAY}{nav:<{W-6}}{C.RESET} {C.DARK_GREEN}{B.v}{C.RESET}")
        print(f"  {C.DARK_GREEN}{B.bl}{B.h * (W - 4)}{B.br}{C.RESET}")
        v = prompt("Escolha").strip().upper()
        if v == "0": return None
        elif v == "N" and page < total_pages - 1: page += 1
        elif v == "P" and page > 0: page -= 1
        elif v.isdigit() and 1 <= int(v) <= len(itens): return itens[int(v) - 1]
        else: msg_warn("Opcao invalida.")

def draw_table(headers, rows, col_widths=None, title=None):
    if not headers: return
    if col_widths is None:
        col_widths = []
        for i, h in enumerate(headers):
            max_w = len(str(h))
            for row in rows:
                if i < len(row): max_w = max(max_w, len(str(row[i])))
            col_widths.append(min(max_w + 2, 40))
    if title: print(f"\n  {C.BOLD}{C.WHITE}{title}{C.RESET}")
    top_line = B.tl
    for i, w in enumerate(col_widths):
        top_line += B.h * w
        top_line += B.tt if i < len(col_widths) - 1 else B.tr
    print(f"  {C.DARK_GREEN}{top_line}{C.RESET}")
    header_line = B.v
    for i, (h, w) in enumerate(zip(headers, col_widths)):
        header_line += f"{C.BOLD}{C.WHITE}{str(h)[:w-1].center(w)}{C.RESET}{C.DARK_GREEN}{B.v}"
    print(f"  {C.DARK_GREEN}{header_line}{C.RESET}")
    sep_line = B.lt
    for i, w in enumerate(col_widths):
        sep_line += B.h * w
        sep_line += B.x if i < len(col_widths) - 1 else B.rt
    print(f"  {C.DARK_GREEN}{sep_line}{C.RESET}")
    for row in rows:
        data_line = f"{C.DARK_GREEN}{B.v}{C.RESET}"
        for i, w in enumerate(col_widths):
            cell = str(row[i])[:w-1] if i < len(row) else ""
            try:
                float(cell.replace(",", ".").replace("R$", "").strip())
                cell_fmt = cell.rjust(w)
            except: cell_fmt = cell.ljust(w)
            data_line += f"{C.CYAN}{cell_fmt}{C.RESET}{C.DARK_GREEN}{B.v}{C.RESET}"
        print(f"  {data_line}")
    bottom_line = B.bl
    for i, w in enumerate(col_widths):
        bottom_line += B.h * w
        bottom_line += B.bt if i < len(col_widths) - 1 else B.br
    print(f"  {C.DARK_GREEN}{bottom_line}{C.RESET}")

def draw_status_box(stats):
    print(f"  {C.DARK_GREEN}{B.tl}{B.h} {C.WHITE}STATUS DO SISTEMA{C.DARK_GREEN} {B.h * (W - 23)}{B.tr}{C.RESET}")
    for key, value in stats.items():
        line = f"{key}: {C.CYAN}{value}{C.RESET}"
        visible_len = len(key) + len(str(value)) + 2
        padding = W - visible_len - 6
        print(f"  {C.DARK_GREEN}{B.v}{C.RESET}  {line}{' ' * max(0, padding)} {C.DARK_GREEN}{B.v}{C.RESET}")
    print(f"  {C.DARK_GREEN}{B.bl}{B.h * (W - 4)}{B.br}{C.RESET}")

def sair():
    print(f"\n  {C.GREEN}Sistema encerrado. Ate logo!{C.RESET}\n")
    sys.exit(0)

def linha(c=None): draw_line(c)
def sub(c=None):
    if c is None: c = B.h
    print(C.DIM + c * W + C.RESET)
def cabecalho(sub_titulo=""): draw_header(sub_titulo)

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════════════════════
DIR = os.path.dirname(os.path.abspath(__file__))
CFGP = os.path.join(DIR, "config.json")

def carregar_config():
    if not os.path.exists(CFGP):
        msg_error(f"config.json nao encontrado: {CFGP}"); sys.exit(1)
    with open(CFGP, "r", encoding="utf-8") as f: cfg = json.load(f)
    if "de_para" not in cfg: cfg["de_para"] = {}
    if "tarifas" not in cfg: cfg["tarifas"] = {}
    if "arquivo_tarifas" not in cfg: cfg["arquivo_tarifas"] = "Tarifas e Rendimento.xlsx"
    return cfg

def salvar_config(cfg):
    with open(CFGP, "w", encoding="utf-8") as f: json.dump(cfg, f, ensure_ascii=False, indent=2)

# ══════════════════════════════════════════════════════════════════════════════
#  MOTOR DE RECONCILIACAO v4
# ══════════════════════════════════════════════════════════════════════════════
def normalizar_nome(nome):
    import re
    nome = re.sub(r'\s+(Impl\.|Manut\.)\s*(PL|CD)?\s*', ' ', nome, flags=re.IGNORECASE)
    nome = re.sub(r'\s*[-–]\s*APP/?RL\s*I*\s*$', '', nome, flags=re.IGNORECASE)
    nome = re.sub(r'\s+APP/?RL\s*I*\s*$', '', nome, flags=re.IGNORECASE)
    nome = re.sub(r'\s+I+\s*$', '', nome)
    nome = re.sub(r'\s+', ' ', nome).strip()
    return nome.upper()

def fuzzy_match(nome_mp, tarifas_disponiveis, cutoff=0.35):
    nome_norm = normalizar_nome(nome_mp)
    nomes_tarifas = list(tarifas_disponiveis.keys())
    nomes_norm_map = {normalizar_nome(t): t for t in nomes_tarifas}
    if nome_norm in nomes_norm_map: return [nomes_norm_map[nome_norm]]
    matches = get_close_matches(nome_norm, list(nomes_norm_map.keys()), n=3, cutoff=cutoff)
    return [nomes_norm_map[m] for m in matches]

def reconciliar_atividade(cfg, nome_mp, interativo=True):
    if nome_mp in cfg["atividades"]: return cfg["atividades"][nome_mp]
    if nome_mp in cfg.get("de_para", {}):
        tarifa_target = cfg["de_para"][nome_mp]
        if tarifa_target in cfg.get("tarifas", {}): return cfg["tarifas"][tarifa_target]
        elif tarifa_target in cfg["atividades"]: return cfg["atividades"][tarifa_target]
    tarifas = cfg.get("tarifas", {})
    if tarifas and interativo:
        sugestoes = fuzzy_match(nome_mp, tarifas)
        if sugestoes:
            print(f"\n  {C.YELLOW}[{B.WARN}] Nova atividade detectada: {C.CYAN}{nome_mp}{C.RESET}")
            print(f"  {C.YELLOW}Sugestoes de tarifas correspondentes:{C.RESET}")
            for i, sug in enumerate(sugestoes, 1):
                t = tarifas[sug]
                hh = t.get('hh', '?')
                preco = t.get('preco_unit', 0)
                print(f"    {C.GREEN}[{i}]{C.RESET} {sug[:45]:<45} {C.CYAN}HH:{hh:>5}  R$:{preco:>8.2f}{C.RESET}")
            print(f"    {C.GREEN}[0]{C.RESET} {C.GRAY}Nenhuma - informar manualmente{C.RESET}")
            resp = prompt("Escolha", "1")
            if resp.isdigit() and 1 <= int(resp) <= len(sugestoes):
                tarifa_escolhida = sugestoes[int(resp) - 1]
                cfg["de_para"][nome_mp] = tarifa_escolhida
                salvar_config(cfg)
                msg_ok(f"Mapeamento salvo: {nome_mp[:35]}... -> {tarifa_escolhida[:25]}...")
                return tarifas[tarifa_escolhida]
    if interativo:
        print(f"\n  {C.YELLOW}[{B.WARN}] Atividade sem match: {C.CYAN}{nome_mp}{C.RESET}")
        print(f"  {C.DIM}Informe os dados manualmente (serao salvos no config):{C.RESET}")
        rend_hh = pedir_float("  Rendimento h/ha", 8.0)
        tipo = prompt("  Tipo [manual/mecanizado/semi]", "manual")
        nova_atividade = {"rendimento_hh": rend_hh, "tipo": tipo, "recurso": "homem" if tipo == "manual" else "maquina", "eficiencia": 1.0 if tipo == "manual" else 0.5, "rendimento_mec": None}
        cfg["atividades"][nome_mp] = nova_atividade
        salvar_config(cfg)
        msg_ok(f"Atividade salva: {nome_mp[:50]}...")
        return nova_atividade
    return {"rendimento_hh": 8.0, "tipo": "manual", "recurso": "homem", "eficiencia": 1.0, "rendimento_mec": None}

def garantir_atividade(cfg, atv, interativo=True):
    if atv not in cfg["atividades"]: reconciliar_atividade(cfg, atv, interativo)

# ══════════════════════════════════════════════════════════════════════════════
#  IMPORTADOR DE TARIFAS (Modulo 7)
# ══════════════════════════════════════════════════════════════════════════════
def modulo_importar_tarifas(cfg):
    draw_header("IMPORTAR TARIFAS")
    arq_tarifas = cfg.get("arquivo_tarifas", "Tarifas e Rendimento.xlsx")
    caminho = os.path.join(DIR, arq_tarifas)
    if not os.path.exists(caminho):
        novo = prompt(f"Arquivo '{arq_tarifas}' nao encontrado. Caminho completo")
        if not os.path.exists(novo): msg_error("Arquivo nao encontrado."); return
        caminho = novo
    print(f"  {C.DIM}Lendo: {caminho}{C.RESET}")
    try: df = pd.read_excel(caminho, sheet_name=0)
    except Exception as e: msg_error(f"Erro ao ler arquivo: {e}"); return
    tarifas_importadas = {}
    for _, row in df.iterrows():
        nome = row.get('Atividade')
        if pd.isna(nome) or not str(nome).strip(): continue
        nome = str(nome).strip()
        tipo = str(row.get('Tipo', 'Manual')).strip()
        hh = row.get('HH'); hm = row.get('HM')
        preco_hora = row.get('Preco Hora', row.get('Preço Hora', 0))
        preco_unit = row.get('Preco Unitario', row.get('Preço Unitário', 0))
        unidade = row.get('Unidade', 'Ha')
        fisico_mensal = row.get('Fisico Mensal', row.get('Fisíco Mensal', 0))
        hh = float(hh) if pd.notna(hh) else None
        hm = float(hm) if pd.notna(hm) else None
        preco_hora = float(preco_hora) if pd.notna(preco_hora) else 0
        preco_unit = float(preco_unit) if pd.notna(preco_unit) else 0
        fisico_mensal = float(fisico_mensal) if pd.notna(fisico_mensal) else 0
        tarifas_importadas[nome] = {"tipo": tipo, "hh": hh, "hm": hm, "preco_hora": preco_hora, "preco_unit": preco_unit, "unidade": str(unidade), "fisico_mensal": fisico_mensal, "rendimento_hh": hh if hh else (hm if hm else 8.0), "rendimento_mec": hm, "recurso": "homem" if tipo == "Manual" else "maquina", "eficiencia": 1.0 if tipo == "Manual" else 0.5}
    cfg["tarifas"] = tarifas_importadas
    salvar_config(cfg)
    manuais = sum(1 for t in tarifas_importadas.values() if t["tipo"] == "Manual")
    mecanizadas = sum(1 for t in tarifas_importadas.values() if t["tipo"] == "Mecanizada")
    semi = sum(1 for t in tarifas_importadas.values() if "Semi" in t["tipo"])
    msg_ok(f"Importadas {len(tarifas_importadas)} tarifas!")
    print(f"    {C.GREEN}Manual: {manuais}  |  Mecanizada: {mecanizadas}  |  Semi: {semi}{C.RESET}")
    headers = ["TARIFA", "TIPO", "HH", "HM", "R$/ha"]
    rows = []
    for nome, t in list(tarifas_importadas.items())[:10]:
        hh_str = f"{t['hh']:.1f}" if t['hh'] else "-"
        hm_str = f"{t['hm']:.2f}" if t['hm'] else "-"
        rows.append([nome[:35], t['tipo'][:10], hh_str, hm_str, f"{t['preco_unit']:.2f}"])
    draw_table(headers, rows, col_widths=[37, 12, 6, 6, 10])
    if len(tarifas_importadas) > 10: print(f"  {C.DIM}... e mais {len(tarifas_importadas) - 10} tarifas{C.RESET}")
    pause()

def analisar_viabilidade_mecanizacao(atividade, area_ha, economia_rs, tarifa_mec_nome, cfg):
    """
    Analisa viabilidade de mecanizacao considerando area minima e aluguel.

    Logica:
    1. Verifica se area >= area minima para o tipo de maquina
    2. Se considerar_aluguel=True, calcula custo proporcional
    3. Economia precisa compensar custo de aluguel

    Returns:
        dict {
            "viavel": bool,
            "motivo": str (explicacao),
            "score": float (quanto maior, melhor recomendacao)
        }
    """
    criterios = cfg.get("criterios_mecanizacao", {})

    # 1. Determinar area minima para este tipo de maquina
    area_min = criterios.get("area_minima_ha", {}).get("default", 2.0)
    areas_min = criterios.get("area_minima_ha", {})

    # Buscar tipo de maquina no nome da tarifa
    for tipo_maq, min_ha in areas_min.items():
        if tipo_maq != "default" and tipo_maq != "_descricao":
            if tipo_maq.upper() in tarifa_mec_nome.upper():
                area_min = min_ha
                break

    # 2. Verificar area minima
    if area_ha < area_min:
        return {
            "viavel": False,
            "motivo": f"Area pequena ({area_ha:.2f} < {area_min:.2f}ha)",
            "score": 0.0
        }

    # 3. Considerar custo de aluguel se habilitado
    if criterios.get("considerar_aluguel", True):
        custos_aluguel = criterios.get("custo_aluguel_mensal", {})
        custo_aluguel_mensal = 0.0

        # Buscar custo de aluguel para este tipo
        for tipo_maq, custo in custos_aluguel.items():
            if tipo_maq.upper() in tarifa_mec_nome.upper():
                custo_aluguel_mensal = custo
                break

        if custo_aluguel_mensal > 0:
            dias_min = criterios.get("dias_minimos_uso", 5)
            custo_dia = custo_aluguel_mensal / 30
            custo_projeto = custo_dia * dias_min

            # Economia precisa superar custo de aluguel
            if economia_rs < custo_projeto:
                return {
                    "viavel": False,
                    "motivo": f"Economia (R$ {economia_rs:.0f}) < aluguel estimado (R$ {custo_projeto:.0f})",
                    "score": economia_rs / custo_projeto if custo_projeto > 0 else 0.0
                }

    # 4. Calcular score (quanto maior, melhor)
    # Score considera: economia absoluta + proporcao de area vs minimo
    score = (economia_rs / 1000) * (area_ha / area_min)

    return {
        "viavel": True,
        "motivo": "Recomendada",
        "score": score
    }

# ══════════════════════════════════════════════════════════════════════════════
#  MODULO DE OTIMIZACAO FINANCEIRA (Modulo 8)
# ══════════════════════════════════════════════════════════════════════════════
def modulo_otimizacao_financeira(cfg, df):
    draw_header("OTIMIZACAO FINANCEIRA")
    tarifas = cfg.get("tarifas", {})
    if not tarifas: msg_warn("Tarifas nao importadas. Use o modulo [7] primeiro."); pause(); return
    if "equipes" not in cfg or "padrao" not in cfg["equipes"]: msg_warn("Configure a equipe padrao primeiro [Menu -> 5]"); pause(); return
    criterios = cfg.get("criterios_mecanizacao", {})  # v4.3
    fazendas = sorted(df["fazenda"].dropna().unique().tolist())
    fazenda = selecionar("SELECIONE A FAZENDA", fazendas)
    if fazenda is None: return
    df_faz = df[df["fazenda"] == fazenda].copy()
    alternativas = {"ROCADA MANUAL": ["ROCADA MECANIZADA", "ROCADA SEMIMEC NA LINHA"], "CAPINA": ["CAPINA QUIMICA TOTAL DRONE", "CAPINA POS-EMERG TOTAL MEC"], "IRRIGACAO": ["IRRIGACAO DE PLANTIO SEMI-MECANIZADA"], "PLANTIO": ["PLANTIO SEMIMECANIZADO COM GEL"]}
    draw_header(f"ANALISE FINANCEIRA - {fazenda}")
    total_manual = 0.0; total_mec = 0.0; total_ha = 0.0; recomendacoes = []
    agg = defaultdict(float)
    for _, row in df_faz.iterrows(): agg[row["atividade"]] += row["area_ha"]
    headers = ["ATIVIDADE", "HA", "R$ MANUAL", "R$ MEC", "ECONOMIA"]; rows = []
    for atv, area in sorted(agg.items()):
        tarifa_nome = cfg.get("de_para", {}).get(atv, atv)
        tarifa_manual = None; tarifa_mec = None
        if tarifa_nome in tarifas:
            t_dados = tarifas[tarifa_nome]
            if t_dados["tipo"] == "Manual": tarifa_manual = t_dados
        else:
            sugestoes_manual = fuzzy_match(atv, {k: v for k, v in tarifas.items() if v["tipo"] == "Manual"})
            if sugestoes_manual: tarifa_manual = tarifas[sugestoes_manual[0]]
        sugestoes_mec = fuzzy_match(atv, {k: v for k, v in tarifas.items() if v["tipo"] in ["Mecanizada", "Semi-Mecanizada"]})
        if sugestoes_mec: tarifa_mec = tarifas[sugestoes_mec[0]]
        if not tarifa_mec:
            for chave, alts in alternativas.items():
                if chave in atv.upper():
                    for alt in alts:
                        if alt in tarifas: tarifa_mec = tarifas[alt]; break
                    break
        if tarifa_manual:
            custo_manual = area * tarifa_manual.get("preco_unit", 0)
            total_manual += custo_manual; total_ha += area
            if tarifa_mec:
                custo_mec = area * tarifa_mec.get("preco_unit", 0); total_mec += custo_mec
                economia = custo_manual - custo_mec
                pct = (economia / custo_manual * 100) if custo_manual > 0 else 0
                rows.append([atv[:30], f"{area:.2f}", f"{custo_manual:.2f}", f"{custo_mec:.2f}", f"{economia:+.2f}"])

                # Analisar viabilidade com criterios inteligentes (v4.3)
                if pct > criterios.get("economia_minima_pct", 15):
                    tarifa_mec_nome = sugestoes_mec[0] if sugestoes_mec else ""
                    analise = analisar_viabilidade_mecanizacao(atv, area, economia, tarifa_mec_nome, cfg)

                    if analise["viavel"]:
                        recomendacoes.append({
                            "atividade": atv,
                            "area": area,
                            "economia": economia,
                            "pct": pct,
                            "score": analise["score"],
                            "maquina": tarifa_mec_nome,
                            "motivo": analise["motivo"]
                        })
            else:
                total_mec += custo_manual
                rows.append([atv[:30], f"{area:.2f}", f"{custo_manual:.2f}", "-", "-"])
    draw_table(headers, rows, col_widths=[32, 8, 12, 12, 12])
    print(f"\n  {C.BOLD}{C.WHITE}RESUMO{C.RESET}"); draw_line(B.h)
    print(f"  {C.GRAY}Area analisada     : {C.WHITE}{total_ha:,.2f} ha{C.RESET}")
    print(f"  {C.GRAY}Custo total MANUAL : {C.YELLOW}R$ {total_manual:,.2f}{C.RESET}")
    print(f"  {C.GRAY}Custo total MEC    : {C.GREEN}R$ {total_mec:,.2f}{C.RESET}")
    economia_total = total_manual - total_mec
    if total_manual > 0:
        pct_total = economia_total / total_manual * 100
        print(f"  {C.BOLD}{C.CYAN}ECONOMIA POTENCIAL : R$ {economia_total:,.2f} ({pct_total:.1f}%){C.RESET}")
    if recomendacoes:
        print(f"\n  {C.YELLOW}{C.BOLD}RECOMENDACOES DE MECANIZACAO{C.RESET}"); draw_line(B.h)
        # Ordenar por score (maior = melhor recomendacao)
        for rec in sorted(recomendacoes, key=lambda x: -x.get("score", 0)):
            maquina_info = f" {C.DIM}[{rec.get('maquina', '')[:25]}]{C.RESET}" if rec.get('maquina') else ""
            print(f"  {C.GREEN}{B.BULLET}{C.RESET} {rec['atividade'][:35]:<35} {C.CYAN}{rec['area']:.1f}ha{C.RESET} -> {C.YELLOW}R$ {rec['economia']:,.2f} ({rec['pct']:.0f}%){C.RESET}{maquina_info}")
        print(f"  {C.DIM}Criterio: area minima + economia compensa aluguel (v4.3){C.RESET}")
    pause()

# ══════════════════════════════════════════════════════════════════════════════
#  ESCOPO DE MESES (Modulo 9)
# ══════════════════════════════════════════════════════════════════════════════
def dias_uteis_mes(ano, mes, feriados=None):
    import calendar
    if feriados is None: feriados = []
    dias = 0; cal = calendar.Calendar()
    for dia in cal.itermonthdays2(ano, mes):
        if dia[0] == 0: continue
        data = datetime.date(ano, mes, dia[0])
        if dia[1] < 5 and data not in feriados: dias += 1
    return dias

def modulo_escopo_meses(cfg, df):
    draw_header("ESCOPO DE MESES")
    if "equipes" not in cfg or "padrao" not in cfg["equipes"]: msg_error("Configure a equipe padrao primeiro [Menu -> 5]"); pause(); return
    fazendas = sorted(df["fazenda"].dropna().unique().tolist())
    fazenda = selecionar("SELECIONE A FAZENDA", fazendas)
    if fazenda is None: return
    df_faz = df[df["fazenda"] == fazenda].copy()
    print(f"\n  {C.BOLD}{C.WHITE}PERIODO DE EXECUCAO{C.RESET}")
    ano = pedir_int("  Ano", datetime.datetime.now().year)
    mes_ini = pedir_int("  Mes inicial (1-12)", 4)
    mes_fim = pedir_int("  Mes final (1-12)", 6)
    if mes_fim < mes_ini: mes_fim += 12
    meses_nomes = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    total_dias_uteis = 0; meses_info = []
    for m in range(mes_ini, mes_fim + 1):
        mes_real = ((m - 1) % 12) + 1; ano_real = ano if m <= 12 else ano + 1
        dias = dias_uteis_mes(ano_real, mes_real); total_dias_uteis += dias
        meses_info.append({"mes": mes_real, "ano": ano_real, "nome": meses_nomes[mes_real - 1], "dias_uteis": dias})
    jornada = cfg.get("jornada_horas", 4.6); colab_padrao = cfg["equipes"]["padrao"]["colaboradores"]
    print(f"\n  {C.GREEN}Colaboradores padrao: {colab_padrao}{C.RESET}")
    colab_str = prompt(f"  Colaboradores para analise (ENTER = {colab_padrao})", "")
    colab = int(colab_str) if colab_str.strip() and colab_str.isdigit() else colab_padrao
    cap_dia = colab * jornada
    total_hh = 0.0
    for _, row in df_faz.iterrows():
        atv = row["atividade"]; garantir_atividade(cfg, atv, interativo=False)
        ac = cfg["atividades"].get(atv, {}); rend = ac.get("rendimento_hh", 8.0) * ac.get("eficiencia", 1.0)
        total_hh += row["area_ha"] * rend
    draw_header(f"CRONOGRAMA - {fazenda}")
    draw_status_box({"Periodo": f"{meses_info[0]['nome']}/{meses_info[0]['ano']} a {meses_info[-1]['nome']}/{meses_info[-1]['ano']}", "Dias uteis": str(total_dias_uteis), "Capacidade/dia": f"{cap_dia:.1f} HH ({colab} colab x {jornada}h)", "Capacidade total": f"{cap_dia * total_dias_uteis:.1f} HH", "Demanda total": f"{total_hh:.1f} HH"})
    headers = ["MES", "DIAS", "CAP HH", "DEMANDA", "STATUS"]; rows = []
    hh_restante = total_hh
    for m in meses_info:
        cap_mes = m["dias_uteis"] * cap_dia; demanda_mes = min(hh_restante, cap_mes)
        hh_restante = max(0, hh_restante - cap_mes)
        if hh_restante > 0 and demanda_mes >= cap_mes: status = "CAPACIDADE"
        elif hh_restante == 0: status = "OK"
        else: status = "FOLGA"
        rows.append([f"{m['nome']}/{m['ano']}", str(m['dias_uteis']), f"{cap_mes:.1f}", f"{demanda_mes:.1f}", status])
    draw_table(headers, rows, col_widths=[12, 8, 12, 12, 12])
    print()
    if hh_restante > 0:
        dias_extras = math.ceil(hh_restante / cap_dia)
        msg_warn(f"ATENCAO: Faltam {hh_restante:.1f} HH ({dias_extras} dias extras necessarios)")
    else:
        folga = (cap_dia * total_dias_uteis) - total_hh
        msg_ok(f"Periodo suficiente. Folga de {folga:.1f} HH")
    pause()

# ══════════════════════════════════════════════════════════════════════════════
#  DADOS
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
#  BUSCA E SELEÇÃO DE ARQUIVOS
# ══════════════════════════════════════════════════════════════════════════════
def buscar_arquivos_excel(extensoes=['.xlsx', '.xls', '.csv'], max_profundidade=3, diretorio=None):
    """Busca recursivamente por arquivos Excel/CSV APENAS no diretorio atual (v4.3: otimizado)."""
    # OTIMIZADO v4.3: Busca apenas DIR e getcwd() para performance
    pastas_busca = [DIR, os.getcwd()]
    pastas_busca = list(set(pastas_busca))  # Remover duplicatas

    arquivos_encontrados = {}

    for pasta_base in pastas_busca:
        if not os.path.exists(pasta_base):
            continue

        try:
            for raiz, dirs, arquivos in os.walk(pasta_base):
                # Limitar profundidade
                profundidade = raiz.replace(pasta_base, "").count(os.sep)
                if profundidade > max_profundidade:
                    dirs[:] = []
                    continue

                # NOVO v4.3: Ignorar pastas ocultas e ambientes virtuais
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['venv', 'env', 'node_modules', '__pycache__', '.git']]

                for arquivo in arquivos:
                    if any(arquivo.endswith(ext) for ext in extensoes):
                        caminho_completo = os.path.join(raiz, arquivo)
                        # Chave mais clara: pasta/arquivo
                        pasta_rel = os.path.basename(os.path.dirname(caminho_completo)) or 'raiz'
                        chave = f"{arquivo}  ({pasta_rel})"
                        arquivos_encontrados[chave] = caminho_completo
        except PermissionError:
            pass

    return arquivos_encontrados

def picker_arquivo(titulo="SELECIONE UM ARQUIVO", extensoes=['.xlsx', '.xls', '.csv'], arquivo_default=None):
    """Picker visual para seleção de arquivo com busca."""
    draw_header(titulo)

    print(f"\n  {C.BOLD}{C.WHITE}Procurando arquivos no diretorio atual...{C.RESET}")
    print(f"  {C.DIM}Pastas: {os.path.basename(DIR) or 'script'} e {os.path.basename(os.getcwd()) or 'atual'}{C.RESET}")
    arquivos = buscar_arquivos_excel(extensoes)

    if not arquivos:
        msg_error("Nenhum arquivo encontrado no diretorio atual.")
        print(f"  {C.DIM}Dica: Coloque o arquivo .xlsx na mesma pasta que o script{C.RESET}\n")
        caminho = prompt("Informe o caminho completo do arquivo")
        if os.path.exists(caminho):
            return caminho
        else:
            msg_error("Arquivo não encontrado.")
            return None

    # Ordenar por nome do arquivo
    arquivos_sorted = sorted(arquivos.items(), key=lambda x: x[0])

    # Se há um arquivo padrão, priorizar
    if arquivo_default and arquivo_default in arquivos:
        arquivos_sorted.insert(0, (arquivo_default, arquivos[arquivo_default]))

    print(f"  {C.GREEN}Encontrados {len(arquivos)} arquivo(s){C.RESET}\n")

    # Usar picker para escolher
    escolhido = selecionar(f"{titulo} ({len(arquivos)} encontrados)",
                          [f"{nome}" for nome, _ in arquivos_sorted],
                          zero_label="Buscar manualmente")

    if escolhido is None:
        # Busca manual
        print(f"\n  {C.BOLD}{C.WHITE}Busca Manual{C.RESET}")
        caminho = prompt("Informe o caminho completo do arquivo .xlsx")
        if os.path.exists(caminho):
            return caminho
        else:
            msg_error("Arquivo não encontrado.")
            return None

    # Encontrar o caminho correspondente
    for nome, caminho in arquivos_sorted:
        if f"{nome}" == escolhido:
            return caminho

    return None

def selecionador_aba(caminho_arquivo):
    """Seletor interativo de abas do Excel."""
    try:
        xls = pd.ExcelFile(caminho_arquivo)
        abas = xls.sheet_names
    except Exception as e:
        msg_error(f"Erro ao ler abas: {e}")
        return None

    if len(abas) == 1:
        return abas[0]

    draw_header("SELECIONE A ABA")
    print(f"  {C.GREEN}Abas disponíveis:{C.RESET}\n")

    aba_escolhida = selecionar("SELECIONE A ABA", abas)
    return aba_escolhida

def carregar_planilha(cfg):
    """Carrega planilha com picker visual aprimorado."""
    arquivo_default = cfg.get("arquivo", "exame.xlsx")

    # Picker de arquivo
    caminho = picker_arquivo("SELECIONE O ARQUIVO DE MICROPLANEJAMENTO",
                            ['.xlsx', '.xls', '.csv'],
                            arquivo_default)
    if caminho is None:
        msg_error("Nenhum arquivo foi selecionado.")
        return None

    # Atualizar config com novo arquivo
    cfg["arquivo"] = os.path.basename(caminho)

    # Picker de aba
    aba = selecionador_aba(caminho)
    if aba is None:
        msg_error("Nenhuma aba foi selecionada.")
        return None

    cfg["aba"] = aba
    salvar_config(cfg)

    print(f"  {C.DIM}Carregando: {caminho} (aba: {aba}){C.RESET}")

    try:
        # Tentar ler com colunas padrão
        df = pd.read_excel(caminho, sheet_name=aba, header=0, usecols=[2, 7, 9, 20])
        df.columns = ["fazenda", "chave", "area_ha", "atividade"]
        df = df.dropna(subset=["atividade", "area_ha", "chave"])
        df["area_ha"] = pd.to_numeric(df["area_ha"], errors="coerce").fillna(0)

        msg_ok(f"Carregadas {len(df)} linhas com sucesso!")
        return df[df["area_ha"] > 0]
    except Exception as e:
        msg_error(f"Erro ao processar arquivo: {e}")
        print(f"  {C.DIM}Certifique-se que as colunas estão nas posições corretas (2, 7, 9, 20){C.RESET}")
        return None

# ══════════════════════════════════════════════════════════════════════════════
#  CALCULO CENTRAL
# ══════════════════════════════════════════════════════════════════════════════
def estimar_dias_uteis(dias_corridos):
    """
    Converte dias corridos em dias uteis (seg-sex).

    Formula: Semanas completas × 5 + dias restantes (max 5)

    Exemplo:
        7 dias corridos → 5 uteis (1 semana)
        10 dias corridos → 8 uteis (1 semana + 3 dias)
        14 dias corridos → 10 uteis (2 semanas)
    """
    if dias_corridos <= 0:
        return 0

    semanas_completas = int(dias_corridos // 7)
    dias_restantes = dias_corridos % 7

    dias_uteis = semanas_completas * 5

    # Dias restantes: maximo 5 uteis por semana
    if dias_restantes <= 5:
        dias_uteis += dias_restantes
    else:
        dias_uteis += 5

    return dias_uteis

def calcular_item(area_ha, colaboradores, rend_hh, jornada_ef, eficiencia=1.0):
    if colaboradores <= 0 or jornada_ef <= 0: return None
    rend_ef = rend_hh * eficiencia; horas_nec = area_ha * rend_ef; cap_dia = colaboradores * jornada_ef
    dias_exatos = horas_nec / cap_dia
    dias_corridos = math.ceil(dias_exatos)  # Dias calendario
    dias_int = estimar_dias_uteis(dias_corridos)  # Converter para dias uteis (seg-sex)
    horas_ultimo = horas_nec % cap_dia
    saldo_h = (cap_dia - horas_ultimo) if horas_ultimo > 0.001 else 0.0
    pct_uso = (horas_ultimo / cap_dia) if horas_ultimo > 0.001 else 1.0
    ha_extra = (saldo_h / rend_ef) if rend_ef > 0 else 0.0
    return dict(area_ha=area_ha, colaboradores=colaboradores, rend_hh=rend_hh, eficiencia=eficiencia, rend_ef=rend_ef, jornada=jornada_ef, horas_nec=horas_nec, cap_dia=cap_dia, dias_exatos=dias_exatos, dias_corridos=dias_corridos, dias_int=dias_int, saldo_h=saldo_h, pct_uso=pct_uso, ha_extra=ha_extra)

def calcular_talhao(df_talhao, equipe, cfg):
    itens = []
    for _, row in df_talhao.iterrows():
        atv = row["atividade"]; ac = cfg["atividades"].get(atv, {}); eq = equipe.get(atv, None)
        if eq is None or eq["colab"] <= 0:
            itens.append({"atividade": atv, "area_ha": row["area_ha"], "horas_nec": 0, "dias_int": 0, "dias_exatos": 0, "saldo_h": 0, "colaboradores": 0, "rend_hh": ac.get("rendimento_hh", 0), "jornada": 0, "sem_equipe": True})
            continue
        r = calcular_item(area_ha=row["area_ha"], colaboradores=eq["colab"], rend_hh=ac.get("rendimento_hh", 8.0), jornada_ef=eq["jornada"], eficiencia=ac.get("eficiencia", 1.0))
        if r: r["atividade"] = atv; r["sem_equipe"] = False; itens.append(r)
    itens_validos = [it for it in itens if not it.get("sem_equipe")]
    if not itens_validos: return itens, 0, 0.0
    dias_talhao = max(it["dias_int"] for it in itens_validos); saldo_total_hh = 0.0
    for it in itens_validos:
        horas_disponiveis_no_horizonte = it["colaboradores"] * it["jornada"] * dias_talhao
        saldo_total_hh += max(0.0, horas_disponiveis_no_horizonte - it["horas_nec"])
    return itens, dias_talhao, saldo_total_hh

def redistribuir_horas_talhoes(resultados_talhao, equipe, cfg):
    """
    Redistribui horas ociosas entre talhoes em cascata (mesma fazenda).

    Logica:
    1. Talhao 1 calcula normalmente → sobra 10h
    2. Talhao 2 recebe 10h bonus → reduz dias necessarios → sobra 5h
    3. Talhao 3 recebe 5h bonus → etc.

    IMPORTANTE: Apenas redistribui dentro da mesma fazenda.

    Returns:
        Lista atualizada com dias ajustados e saldo redistribuido
    """
    saldo_acumulado_hh = 0.0
    resultados_ajustados = []

    for rtalhao in resultados_talhao:
        # 1. Calcular total de HH necessarias (excluindo atividades sem equipe)
        itens_validos = [it for it in rtalhao["itens"] if not it.get("sem_equipe")]
        if not itens_validos:
            # Talhao sem equipe - apenas preserva
            resultados_ajustados.append({
                "chave": rtalhao["chave"],
                "area_ha": rtalhao["area_ha"],
                "itens": rtalhao["itens"],
                "dias_talhao": 0,
                "saldo_hh": 0.0,
                "saldo_recebido": 0.0
            })
            continue

        total_hh_necessarias = sum(it["horas_nec"] for it in itens_validos)

        # 2. Consumir saldo acumulado do talhao anterior
        hh_a_consumir = min(saldo_acumulado_hh, total_hh_necessarias)
        hh_restantes = total_hh_necessarias - hh_a_consumir

        # 3. Recalcular dias com HH reduzidas
        # Capacidade total por dia (soma de todos os itens)
        cap_dia_total = sum(it["cap_dia"] for it in itens_validos)

        if cap_dia_total > 0:
            dias_corridos = math.ceil(hh_restantes / cap_dia_total)
            dias_ajustados = estimar_dias_uteis(dias_corridos)
        else:
            dias_ajustados = 0

        # 4. Calcular novo saldo
        # HH disponiveis = capacidade por dia × dias + bonus recebido
        hh_disponiveis = cap_dia_total * dias_corridos + hh_a_consumir
        novo_saldo = max(0.0, hh_disponiveis - total_hh_necessarias)

        # 5. Armazenar resultado ajustado
        resultados_ajustados.append({
            "chave": rtalhao["chave"],
            "area_ha": rtalhao["area_ha"],
            "itens": rtalhao["itens"],
            "dias_talhao": dias_ajustados,
            "saldo_hh": novo_saldo,
            "saldo_recebido": hh_a_consumir
        })

        # 6. Atualizar saldo acumulado para proximo talhao
        saldo_acumulado_hh = novo_saldo

    return resultados_ajustados

# ══════════════════════════════════════════════════════════════════════════════
#  COLETA DE EQUIPE
# ══════════════════════════════════════════════════════════════════════════════
def coletar_equipe(ativs, cfg, titulo="MONTAR EQUIPE"):
    print(f"\n  {C.BOLD}{C.WHITE}{titulo}{C.RESET}")
    print(f"  {C.DIM}Para cada atividade: informe colaboradores e jornada efetiva.{C.RESET}")
    print(f"  {C.DIM}ENTER = manter padrao  |  0 = pular atividade{C.RESET}\n")
    equipe = {}; jornada_padrao = cfg.get("jornada_horas", 4.6); colab_padrao = cfg["equipes"]["padrao"]["colaboradores"]
    for i, atv in enumerate(ativs, 1):
        draw_line(B.h * 1, color=C.DIM)
        ac = cfg["atividades"].get(atv, {}); preco = ""
        if atv in cfg.get("de_para", {}):
            t_nome = cfg["de_para"][atv]
            if t_nome in cfg.get("tarifas", {}): preco = f"  R$:{cfg['tarifas'][t_nome].get('preco_unit', 0):.2f}/ha"
        print(f"  {C.GREEN}[{i}/{len(ativs)}]{C.RESET} {C.CYAN}{atv}{C.RESET}")
        print(f"         {C.DIM}rend: {ac.get('rendimento_hh', 8.0)} h/ha  |  efic: {ac.get('eficiencia', 1.0)}{C.YELLOW}{preco}{C.RESET}")
        colab = pedir_int("  Colaboradores", colab_padrao, allow_zero=True)
        jornada = pedir_float("  Jornada efetiva (h)", jornada_padrao) if colab > 0 else jornada_padrao
        equipe[atv] = {"colab": colab, "jornada": jornada}
    return equipe

# ══════════════════════════════════════════════════════════════════════════════
#  MODULO 1: ORCAR FAZENDA
# ══════════════════════════════════════════════════════════════════════════════
def modulo_orcar_fazenda(cfg, df):
    draw_header("ORCAR FAZENDA COMPLETA")
    fazendas = sorted(df["fazenda"].dropna().unique().tolist())
    fazenda = selecionar("SELECIONE A FAZENDA", fazendas)
    if fazenda is None: return
    df_faz = df[df["fazenda"] == fazenda].copy()
    uts = sorted(df_faz["chave"].unique().tolist()); ativs = sorted(df_faz["atividade"].unique().tolist())
    for atv in ativs: garantir_atividade(cfg, atv)
    salvar_config(cfg)
    draw_header(f"FAZENDA: {fazenda}")
    draw_status_box({"TALHOES": str(len(uts)), "Atividades distintas": str(len(ativs))})
    headers = ["#", "ATIVIDADE", "h/ha", "EFIC", "MEC"]; rows = []
    for i, atv in enumerate(ativs, 1):
        ac = cfg["atividades"][atv]; rend = ac.get("rendimento_hh", 8.0); efic = ac.get("eficiencia", 1.0)
        rmec = ac.get("rendimento_mec"); mec_str = f"{rmec:.1f}" if rmec else "-"
        rows.append([str(i), atv[:45], f"{rend:.2f}", f"{efic:.2f}", mec_str])
    draw_table(headers, rows, col_widths=[4, 47, 8, 6, 8], title="ATIVIDADES")
    equipe = coletar_equipe(ativs, cfg)
    resultados_talhao = []
    for chave in uts:
        df_talhao = df_faz[df_faz["chave"] == chave]; area_talhao = df_talhao["area_ha"].iloc[0]
        itens, dias_talhao, saldo_hh = calcular_talhao(df_talhao, equipe, cfg)
        resultados_talhao.append({"chave": chave, "area_ha": area_talhao, "itens": itens, "dias_talhao": dias_talhao, "saldo_hh": saldo_hh})

    # REDISTRIBUIR HORAS OCIOSAS ENTRE TALHOES (v4.3)
    resultados_talhao = redistribuir_horas_talhoes(resultados_talhao, equipe, cfg)

    exibir_relatorio_fazenda(fazenda, resultados_talhao, equipe)
    resp = prompt("\n  Exportar relatorio .txt? [s/n]", "s")
    if resp.lower() == "s": exportar_txt(fazenda, resultados_ut, equipe)
    pause("Pressione ENTER para voltar ao menu")

# ══════════════════════════════════════════════════════════════════════════════
#  MODULO 2: SPRINT
# ══════════════════════════════════════════════════════════════════════════════
def modulo_sprint(cfg, df):
    draw_header("SPRINT - SIMULACAO RAPIDA")
    fazendas = sorted(df["fazenda"].dropna().unique().tolist())
    fazenda = selecionar("SELECIONE A FAZENDA", fazendas)
    if fazenda is None: return
    df_faz = df[df["fazenda"] == fazenda].copy()
    uts = sorted(df_faz["chave"].unique().tolist()); ativs = sorted(df_faz["atividade"].unique().tolist())
    for atv in ativs: garantir_atividade(cfg, atv)
    print(f"\n  {C.BOLD}{C.WHITE}ESCOPO DO SPRINT{C.RESET}")
    print(f"  {C.GREEN}[1]{C.RESET} {C.CYAN}Fazenda inteira{C.RESET}")
    print(f"  {C.GREEN}[2]{C.RESET} {C.CYAN}Um TALHAO especifico{C.RESET}")
    escopo = prompt("Escolha", "1")
    if escopo == "2":
        talhao_sel = selecionar("SELECIONE O TALHAO", uts)
        if talhao_sel is None: return
        df_alvo = df_faz[df_faz["chave"] == talhao_sel]; titulo_alvo = f"TALHAO {talhao_sel}"
    else: df_alvo = df_faz; titulo_alvo = fazenda
    ativs_alvo = sorted(df_alvo["atividade"].unique().tolist())
    print(f"\n  {C.BOLD}{C.WHITE}FILTRAR ATIVIDADES?{C.RESET}")
    print(f"  {C.GREEN}[1]{C.RESET} {C.CYAN}Todas as atividades{C.RESET}")
    print(f"  {C.GREEN}[2]{C.RESET} {C.CYAN}Escolher atividades especificas{C.RESET}")
    filtro_resp = prompt("Escolha", "1")
    ativs_sprint = ativs_alvo
    if filtro_resp == "2":
        selecionadas = []; print(f"\n  {C.WHITE}Marque as atividades (s/n para cada):{C.RESET}")
        for atv in ativs_alvo:
            resp = prompt(f"  Incluir '{atv[:50]}'? [s/n]", "s")
            if resp.lower() != "n": selecionadas.append(atv)
        if not selecionadas: msg_warn("Nenhuma atividade selecionada."); return
        ativs_sprint = selecionadas
    print(f"\n  {C.BOLD}{C.WHITE}MODO DE EQUIPE{C.RESET}")
    print(f"  {C.GREEN}[1]{C.RESET} {C.CYAN}Pool unico (mesma equipe para todas){C.RESET}")
    print(f"  {C.GREEN}[2]{C.RESET} {C.CYAN}Colaboradores por atividade{C.RESET}")
    modo_equipe = prompt("Escolha", "1")
    if modo_equipe == "2": equipe_sprint = coletar_equipe(ativs_sprint, cfg, "EQUIPE DO SPRINT")
    else:
        draw_line(); print(f"  {C.BOLD}{C.WHITE}EQUIPE UNICA DO SPRINT{C.RESET}\n")
        colab = pedir_int("  Colaboradores", cfg["equipes"]["padrao"]["colaboradores"])
        jornada = pedir_float("  Jornada efetiva (h)", cfg.get("jornada_horas", 4.6))
        equipe_sprint = {atv: {"colab": colab, "jornada": jornada} for atv in ativs_sprint}
    draw_header(f"SPRINT - {titulo_alvo}")
    total_dias_seq = 0; total_hh = 0.0; total_ha_sprint = 0.0; max_dias_paralelo = 0
    agg = defaultdict(float)
    for _, row in df_alvo[df_alvo["atividade"].isin(ativs_sprint)].iterrows(): agg[row["atividade"]] += row["area_ha"]
    headers = ["ATIVIDADE", "TOT HA", "TOT HH", "DIAS"]; rows = []
    for atv in sorted(agg.keys()):
        ac = cfg["atividades"].get(atv, {}); area = agg[atv]; eq = equipe_sprint.get(atv, {})
        colab = eq.get("colab", 4); jornada = eq.get("jornada", 4.6)
        r = calcular_item(area, colab, ac.get("rendimento_hh", 8.0), jornada, ac.get("eficiencia", 1.0))
        if r:
            total_dias_seq += r["dias_int"]; total_hh += r["horas_nec"]; total_ha_sprint += area
            max_dias_paralelo = max(max_dias_paralelo, r["dias_int"])
            rows.append([atv[:42], f"{area:.3f}", f"{r['horas_nec']:.1f}", f"{r['dias_int']}d"])
    draw_table(headers, rows, col_widths=[44, 10, 10, 8])
    print(f"\n  {C.BOLD}{C.WHITE}RESUMO{C.RESET}"); draw_line(B.h)
    print(f"  {C.GRAY}Total area           : {C.WHITE}{total_ha_sprint:.3f} ha{C.RESET}")
    print(f"  {C.GRAY}Total horas-homem    : {C.WHITE}{total_hh:.1f} h{C.RESET}")
    print(f"  {C.YELLOW}{C.BOLD}Prazo SEQUENCIAL     : {total_dias_seq} dia(s){C.RESET}")
    print(f"  {C.CYAN}{C.BOLD}Prazo PARALELO       : {max_dias_paralelo} dia(s){C.RESET}")
    print(f"  {C.DIM}Sequencial = uma atividade apos a outra{C.RESET}")
    print(f"  {C.DIM}Paralelo   = equipes independentes simultaneamente{C.RESET}")
    pause("Pressione ENTER para voltar ao menu")

# ══════════════════════════════════════════════════════════════════════════════
#  MODULO 3: COMPARATIVO MEC vs MANUAL
# ══════════════════════════════════════════════════════════════════════════════
def modulo_comparativo_mec(cfg, df):
    draw_header("COMPARATIVO: MANUAL vs MECANIZADO")
    fazendas = sorted(df["fazenda"].dropna().unique().tolist())
    fazenda = selecionar("SELECIONE A FAZENDA", fazendas)
    if fazenda is None: return
    df_faz = df[df["fazenda"] == fazenda].copy()
    ativs = sorted(df_faz["atividade"].unique().tolist())
    for atv in ativs: garantir_atividade(cfg, atv)
    ativs_mec = [a for a in ativs if cfg["atividades"][a].get("rendimento_mec")]
    if not ativs_mec:
        msg_warn("Nenhuma atividade desta fazenda tem 'rendimento_mec' no config.")
        print(f"  {C.DIM}Configure via Menu Principal > opcao 4 (campo rendimento_mec).{C.RESET}"); pause(); return
    print(f"\n  {C.WHITE}Atividades com rendimento mecanizado configurado:{C.RESET}")
    for atv in ativs_mec:
        ac = cfg["atividades"][atv]
        print(f"  {C.GREEN}{B.BULLET}{C.RESET} {atv[:52]} {C.CYAN}manual {ac['rendimento_hh']:.1f} h/ha  |  mec {ac['rendimento_mec']:.1f} h/ha{C.RESET}")
    draw_line(); print(f"  {C.BOLD}{C.WHITE}EQUIPE PARA O COMPARATIVO{C.RESET}\n")
    colab_manual = pedir_int("  Colaboradores (modo manual)", cfg["equipes"]["padrao"]["colaboradores"])
    jornada = pedir_float("  Jornada efetiva (h)", cfg.get("jornada_horas", 4.6))
    colab_mec = pedir_int("  Operadores (modo mecanizado)", 1)
    agg = defaultdict(float)
    for _, row in df_faz[df_faz["atividade"].isin(ativs_mec)].iterrows(): agg[row["atividade"]] += row["area_ha"]
    draw_header(f"COMPARATIVO - {fazenda}")
    headers = ["ATIVIDADE", "HA", "MAN dias", "MEC dias", "GANHO"]; rows = []
    total_man = 0; total_mec = 0; total_ha = 0.0
    for atv in sorted(agg.keys()):
        ac = cfg["atividades"][atv]; area = agg[atv]
        r_man = calcular_item(area, colab_manual, ac["rendimento_hh"], jornada, ac.get("eficiencia", 1.0))
        r_mec = calcular_item(area, colab_mec, ac["rendimento_mec"], jornada, 1.0)
        if r_man and r_mec:
            ganho = r_man["dias_int"] - r_mec["dias_int"]
            rows.append([atv[:40], f"{area:.3f}", f"{r_man['dias_int']}d", f"{r_mec['dias_int']}d", f"{ganho:+}d"])
            total_man += r_man["dias_int"]; total_mec += r_mec["dias_int"]; total_ha += area
    draw_table(headers, rows, col_widths=[42, 8, 10, 10, 8])
    print(f"\n  {C.BOLD}{C.WHITE}TOTAIS{C.RESET}"); draw_line(B.h)
    print(f"  {C.GRAY}Area total analisada : {C.WHITE}{total_ha:.3f} ha{C.RESET}")
    print(f"  {C.YELLOW}{C.BOLD}Total MANUAL         : {total_man} dia(s){C.RESET}")
    print(f"  {C.GREEN}{C.BOLD}Total MECANIZADO     : {total_mec} dia(s){C.RESET}")
    if total_man > 0:
        red = ((total_man - total_mec) / total_man) * 100
        print(f"  {C.CYAN}{C.BOLD}Reducao de prazo     : {red:.1f}%{C.RESET}")
    pause("Pressione ENTER para voltar ao menu")

# ══════════════════════════════════════════════════════════════════════════════
#  EXIBICAO DO RELATORIO
# ══════════════════════════════════════════════════════════════════════════════
def exibir_relatorio_fazenda(fazenda, resultados_talhao, equipe):
    draw_header(f"RELATORIO - {fazenda}")
    total_dias = 0; total_hh = 0.0; total_ha = 0.0; total_saldo_hh = 0.0
    for rtalhao in resultados_talhao:
        print(f"\n  {C.DARK_GREEN}{B.tl}{B.h} {C.BOLD}{C.WHITE}TALHAO: {rtalhao['chave']}{C.RESET} {C.DARK_GREEN}{B.h * 20} {C.CYAN}{rtalhao['area_ha']:.3f} ha{C.RESET} {C.DARK_GREEN}{B.h * 20}{B.tr}{C.RESET}")
        # Mostrar se recebeu horas do talhao anterior (v4.3)
        if rtalhao.get("saldo_recebido", 0) > 0:
            print(f"  {C.CYAN}{B.BULLET} Recebeu {rtalhao['saldo_recebido']:.1f}h do talhao anterior{C.RESET}")
        headers = ["ATIVIDADE", "HA", "HH", "DIAS"]; rows = []
        for it in rtalhao["itens"]:
            if it.get("sem_equipe"): rows.append([it['atividade'][:40], f"{it['area_ha']:.3f}", "-", "SEM EQUIPE"])
            else: rows.append([it['atividade'][:40], f"{it['area_ha']:.3f}", f"{it['horas_nec']:.1f}", f"{it['dias_int']}d"])
        draw_table(headers, rows, col_widths=[42, 8, 8, 10])
        print(f"  {C.GRAY}Duracao do TALHAO: {C.BOLD}{rtalhao['dias_talhao']}d{C.RESET}  |  {C.GRAY}Saldo HH ocioso: {C.YELLOW}{rtalhao['saldo_hh']:.1f}h{C.RESET}")
        total_dias = max(total_dias, rtalhao["dias_talhao"])
        total_hh += sum(it["horas_nec"] for it in rtalhao["itens"] if not it.get("sem_equipe"))
        total_ha += rtalhao["area_ha"]; total_saldo_hh += rtalhao["saldo_hh"]
    print(f"\n  {C.BOLD}{C.WHITE}CONSOLIDADO - {fazenda}{C.RESET}"); draw_line(B.H)
    draw_status_box({"TALHOES analisados": str(len(resultados_talhao)), "Area total (ha)": f"{total_ha:.3f}", "Total horas-homem": f"{total_hh:.1f} h", "Saldo HH ocioso total": f"{total_saldo_hh:.1f} h", "PRAZO ESTIMADO": f"{total_dias} dia(s) uteis"})
    print(f"  {C.DIM}(Prazo = TALHAO mais longo; atividades distintas trabalham em paralelo){C.RESET}")
    print(f"\n  {C.BOLD}{C.WHITE}RESUMO POR ATIVIDADE{C.RESET}")
    headers = ["ATIVIDADE", "TOT HA", "TOT HH", "COLAB", "JORN"]; rows = []
    agg = defaultdict(lambda: {"ha": 0.0, "hh": 0.0})
    for rtalhao in resultados_talhao:
        for it in rtalhao["itens"]:
            if not it.get("sem_equipe"): agg[it["atividade"]]["ha"] += it["area_ha"]; agg[it["atividade"]]["hh"] += it["horas_nec"]
    for atv in sorted(agg.keys()):
        eq = equipe.get(atv, {})
        rows.append([atv[:40], f"{agg[atv]['ha']:.3f}", f"{agg[atv]['hh']:.1f}", str(eq.get('colab', '-')), str(eq.get('jornada', '-'))])
    draw_table(headers, rows, col_widths=[42, 10, 10, 6, 6])

# ══════════════════════════════════════════════════════════════════════════════
#  EXPORTAR TXT
# ══════════════════════════════════════════════════════════════════════════════
def exportar_txt(fazenda, resultados_talhao, equipe):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    nome = f"SRF_{fazenda.replace(' ', '_').replace('/', '_')[:30]}_{ts}.txt"
    dest = os.path.join(DIR, nome); sep = "=" * 66; sep2 = "-" * 66; L = []
    L += [sep, f"  RESTAURACAO FLORESTAL - RELATORIO DE ORCAMENTO v{VERSION}".center(66), f"  Fazenda : {fazenda}", f"  Gerado  : {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", sep]
    total_dias = 0; total_hh = 0.0; total_ha = 0.0; total_saldo = 0.0
    for rtalhao in resultados_talhao:
        L += [f"\n  TALHAO: {rtalhao['chave']}  |  {rtalhao['area_ha']:.3f} ha", sep2]
        # Mostrar se recebeu horas (v4.3)
        if rtalhao.get("saldo_recebido", 0) > 0:
            L.append(f"  (+) Recebeu {rtalhao['saldo_recebido']:.1f}h do talhao anterior")
        L += [f"  {'ATIVIDADE':<48} {'HA':>7} {'HH':>7} {'DIAS':>5}", sep2]
        for it in rtalhao["itens"]:
            if it.get("sem_equipe"): L.append(f"  {it['atividade']:<48} {it['area_ha']:>7.3f}  [SEM EQUIPE]")
            else: L.append(f"  {it['atividade']:<48} {it['area_ha']:>7.3f} {it['horas_nec']:>7.1f} {it['dias_int']:>4}d")
        L += [sep2, f"  {'Duracao do TALHAO':>50}  {rtalhao['dias_talhao']:>3}d", f"  {'Saldo HH ocioso':>50}  {rtalhao['saldo_hh']:>6.1f}h"]
        total_dias = max(total_dias, rtalhao["dias_talhao"])
        total_hh += sum(it["horas_nec"] for it in rtalhao["itens"] if not it.get("sem_equipe"))
        total_ha += rtalhao["area_ha"]; total_saldo += rtalhao["saldo_hh"]
    L += ["\n" + sep, "  TOTAIS DA FAZENDA", sep2, f"  TALHOES            : {len(resultados_talhao)}", f"  Area total (ha)    : {total_ha:.3f}", f"  Horas-homem totais : {total_hh:.1f} h", f"  Saldo HH ocioso    : {total_saldo:.1f} h", f"  PRAZO ESTIMADO     : {total_dias} dia(s) uteis", sep, "\n  EQUIPE CONFIGURADA", sep2]
    for atv, eq in sorted(equipe.items()): L.append(f"  {atv:<52} {eq['colab']} colab.  {eq['jornada']:.1f}h efetiva")
    L.append(sep)
    with open(dest, "w", encoding="utf-8") as f: f.write("\n".join(L))
    msg_ok(f"Relatorio salvo: {dest}")

# ══════════════════════════════════════════════════════════════════════════════
#  MODULO: RENDIMENTOS
# ══════════════════════════════════════════════════════════════════════════════
def modulo_rendimentos(cfg, df):
    ativs = sorted(df["atividade"].dropna().unique().tolist())
    for atv in ativs: garantir_atividade(cfg, atv, interativo=False)
    salvar_config(cfg)
    while True:
        draw_header("CONFIGURAR RENDIMENTOS ORCADOS")
        headers = ["#", "ATIVIDADE", "h/ha", "EFIC", "MEC h/ha"]; rows = []
        for i, atv in enumerate(ativs, 1):
            ac = cfg["atividades"].get(atv, {}); rend = ac.get("rendimento_hh", 0); efic = ac.get("eficiencia", 1.0)
            mec = ac.get("rendimento_mec"); mec_str = f"{mec:.2f}" if mec else "-"
            rows.append([str(i), atv[:45], f"{rend:.2f}", f"{efic:.2f}", mec_str])
        draw_table(headers, rows, col_widths=[4, 47, 8, 6, 10])
        print(f"\n  {C.GREEN}[0]{C.RESET} {C.GRAY}Voltar{C.RESET}")
        v = prompt("Numero para editar")
        if v == "0": return
        if not v.isdigit() or not (1 <= int(v) <= len(ativs)): msg_warn("Invalido."); continue
        atv = ativs[int(v) - 1]; ac = cfg["atividades"][atv]
        print(f"\n  {C.GREEN}Editando: {C.CYAN}{atv}{C.RESET}")
        ac["rendimento_hh"] = pedir_float("Rendimento manual h/ha (orcado)", ac.get("rendimento_hh", 8.0))
        ac["eficiencia"] = min(max(pedir_float("Eficiencia (1.0=manual | 0.5=mec padrao)", ac.get("eficiencia", 1.0)), 0.01), 1.0)
        ac["tipo"] = prompt("Tipo [manual/mecanizado/semimecanizado]", ac.get("tipo", "manual"))
        ac["recurso"] = prompt("Recurso [homem/maquina]", ac.get("recurso", "homem"))
        resp_mec = prompt("Configurar rendimento mecanizado? [s/n]", "n")
        if resp_mec.lower() == "s": ac["rendimento_mec"] = pedir_float("Rendimento MECANIZADO h/ha (menor = mais rapido)", ac.get("rendimento_mec") or ac["rendimento_hh"] * 0.3)
        salvar_config(cfg); msg_ok(f"Salvo: {atv}"); pause("ENTER")

# ══════════════════════════════════════════════════════════════════════════════
#  MODULO: EQUIPE PADRAO
# ══════════════════════════════════════════════════════════════════════════════
def modulo_equipe(cfg):
    draw_header("PARAMETROS PADRAO")
    j = cfg.get("jornada_horas", 4.6); c = cfg["equipes"]["padrao"]["colaboradores"]
    draw_status_box({"Jornada padrao": f"{j} h/dia", "Colaboradores": str(c)})
    print(f"\n  {C.BOLD}{C.WHITE}Atualizar valores:{C.RESET}")
    cfg["jornada_horas"] = pedir_float("Nova jornada padrao (h)", j)
    cfg["equipes"]["padrao"]["colaboradores"] = pedir_int("Novo n colaboradores", c)
    salvar_config(cfg); msg_ok("Parametros salvos."); pause()

# ══════════════════════════════════════════════════════════════════════════════
#  MODULO: CATALOGO
# ══════════════════════════════════════════════════════════════════════════════
def modulo_catalogo(df):
    draw_header("CATALOGO DE DADOS")
    fazendas = sorted(df["fazenda"].dropna().unique().tolist())
    fazenda = selecionar("FILTRAR POR FAZENDA (0 = todas)", fazendas, zero_label="Todas")
    filtro = df if fazenda is None else df[df["fazenda"] == fazenda]
    draw_header("CATALOGO")
    headers = ["FAZENDA", "TALHAO", "ATIVIDADE", "HA"]; rows = []
    for _, row in filtro.head(50).iterrows(): rows.append([str(row['fazenda'])[:25], str(row['chave'])[:12], str(row['atividade'])[:35], f"{row['area_ha']:.3f}"])
    draw_table(headers, rows, col_widths=[27, 14, 37, 8])
    if len(filtro) > 50: print(f"  {C.DIM}... mostrando 50 de {len(filtro)} registros{C.RESET}")
    print(f"\n  {C.BOLD}{C.GREEN}TOTAL ha: {filtro['area_ha'].sum():.3f}{C.RESET}"); pause()

# ══════════════════════════════════════════════════════════════════════════════
#  MODULO: MAPEAMENTOS de_para
# ══════════════════════════════════════════════════════════════════════════════
def modulo_ver_mapeamentos(cfg):
    while True:
        draw_header("MAPEAMENTOS de_para")
        de_para = cfg.get("de_para", {})
        if not de_para:
            msg_warn("Nenhum mapeamento salvo ainda.")
            print(f"  {C.DIM}Os mapeamentos sao criados automaticamente quando o sistema{C.RESET}")
            print(f"  {C.DIM}encontra uma atividade nova e voce confirma uma tarifa correspondente.{C.RESET}")
            pause(); return
        headers = ["#", "ATIVIDADE MICROPLANEJAMENTO", "TARIFA ORCADA"]; rows = []
        items = sorted(de_para.items())
        for i, (mp, tarifa) in enumerate(items, 1): rows.append([str(i), mp[:38], tarifa[:28]])
        draw_table(headers, rows, col_widths=[4, 40, 30], title=f"Total: {len(de_para)} mapeamentos")
        print(f"\n  {C.GREEN}[D]{C.RESET} Deletar mapeamento")
        print(f"  {C.GREEN}[E]{C.RESET} Editar mapeamento")
        print(f"  {C.GREEN}[0]{C.RESET} Voltar")
        opcao = prompt("Escolha", "0").strip().upper()
        if opcao == "0": return
        elif opcao == "D":
            num = prompt("  Numero do mapeamento para deletar", "")
            if num.isdigit() and 1 <= int(num) <= len(items):
                mp_chave = items[int(num) - 1][0]
                confirma = prompt(f"  Confirma exclusao de '{mp_chave[:40]}'? (S/N)", "N").upper()
                if confirma == "S": del cfg["de_para"][mp_chave]; salvar_config(cfg); msg_ok(f"Mapeamento deletado: {mp_chave[:40]}..."); pause("ENTER para continuar")
            else: msg_error("Numero invalido."); pause("ENTER para continuar")
        elif opcao == "E":
            num = prompt("  Numero do mapeamento para editar", "")
            if num.isdigit() and 1 <= int(num) <= len(items):
                mp_chave, tarifa_antiga = items[int(num) - 1]
                print(f"\n  {C.GREEN}Atividade: {mp_chave}{C.RESET}")
                print(f"  {C.YELLOW}Tarifa atual: {tarifa_antiga}{C.RESET}")
                nova_tarifa = prompt("  Nova tarifa", tarifa_antiga)
                if nova_tarifa.strip(): cfg["de_para"][mp_chave] = nova_tarifa.strip(); salvar_config(cfg); msg_ok("Mapeamento atualizado!"); pause("ENTER para continuar")
            else: msg_error("Numero invalido."); pause("ENTER para continuar")
        else: msg_warn("Opcao invalida."); pause("ENTER para continuar")

# ══════════════════════════════════════════════════════════════════════════════
#  MODULO 10: PROVA REAL - VALIDACAO DE CALCULOS
# ══════════════════════════════════════════════════════════════════════════════
def modulo_prova_real(cfg):
    """
    Valida calculos comparando com planilha de teste.

    Arquivo esperado: exame_validacao.xlsx
    Colunas: atividade, area_ha, colaboradores, jornada, dias_esperados
    """
    draw_header("PROVA REAL - VALIDACAO DE CALCULOS")

    # Procurar arquivo de validacao
    arquivo_exame = os.path.join(DIR, "exame_validacao.xlsx")
    if not os.path.exists(arquivo_exame):
        msg_error(f"Arquivo nao encontrado: exame_validacao.xlsx")
        print(f"\n  {C.DIM}Crie o arquivo com as colunas:{C.RESET}")
        print(f"  {C.CYAN}atividade | area_ha | colaboradores | jornada | dias_esperados{C.RESET}")
        pause()
        return

    try:
        df_exame = pd.read_excel(arquivo_exame, sheet_name=0)
    except Exception as e:
        msg_error(f"Erro ao ler arquivo: {e}")
        pause()
        return

    # Validar colunas
    colunas_req = ["atividade", "area_ha", "colaboradores", "jornada", "dias_esperados"]
    if not all(col in df_exame.columns for col in colunas_req):
        msg_error("Colunas invalidas no arquivo!")
        print(f"  {C.YELLOW}Esperado: {', '.join(colunas_req)}{C.RESET}")
        print(f"  {C.RED}Encontrado: {', '.join(df_exame.columns)}{C.RESET}")
        pause()
        return

    print(f"  {C.CYAN}Executando {len(df_exame)} testes...{C.RESET}\n")

    resultados = []
    ok_count = 0

    for idx, row in df_exame.iterrows():
        atv = row["atividade"]

        # Verificar se atividade existe
        if atv not in cfg["atividades"]:
            resultados.append({
                "atividade": atv,
                "dias_calc": "-",
                "dias_esp": row["dias_esperados"],
                "status": "NAO ENCONTRADA"
            })
            continue

        ac = cfg["atividades"][atv]
        calc = calcular_item(
            area_ha=row["area_ha"],
            colaboradores=row["colaboradores"],
            rend_hh=ac.get("rendimento_hh", 8.0),
            jornada_ef=row["jornada"],
            eficiencia=ac.get("eficiencia", 1.0)
        )

        if calc is None:
            resultados.append({
                "atividade": atv,
                "dias_calc": "-",
                "dias_esp": row["dias_esperados"],
                "status": "ERRO CALCULO"
            })
            continue

        # Comparar com tolerancia
        diferenca = abs(calc["dias_int"] - row["dias_esperados"])
        tolerancia = 1  # +/- 1 dia

        if diferenca <= tolerancia:
            status = "OK"
            ok_count += 1
        else:
            status = f"DIVERGE ({diferenca}d)"

        resultados.append({
            "atividade": atv[:40],
            "dias_calc": calc["dias_int"],
            "dias_esp": int(row["dias_esperados"]),
            "dias_corridos": calc.get("dias_corridos", "-"),
            "status": status
        })

    # Exibir tabela de resultados
    headers = ["ATIVIDADE", "CALC", "ESPER", "CORR", "STATUS"]
    rows = []
    for r in resultados:
        # Colorir status
        if r["status"] == "OK":
            status_str = f"{C.GREEN}{r['status']}{C.RESET}"
        elif "DIVERGE" in r["status"]:
            status_str = f"{C.YELLOW}{r['status']}{C.RESET}"
        else:
            status_str = f"{C.RED}{r['status']}{C.RESET}"

        rows.append([
            r["atividade"],
            f"{r['dias_calc']}d" if r['dias_calc'] != "-" else "-",
            f"{r['dias_esp']}d",
            f"{r.get('dias_corridos', '-')}d" if r.get('dias_corridos') != "-" else "-",
            status_str
        ])

    draw_table(headers, rows, col_widths=[42, 8, 8, 8, 16])

    # Resumo
    taxa = (ok_count / len(resultados)) * 100 if resultados else 0
    print(f"\n  {C.BOLD}{C.WHITE}RESULTADO{C.RESET}")
    draw_line(B.h)

    if taxa >= 90:
        cor = C.GREEN
    elif taxa >= 70:
        cor = C.YELLOW
    else:
        cor = C.RED

    print(f"  {cor}Taxa de sucesso: {taxa:.1f}% ({ok_count}/{len(resultados)}){C.RESET}")
    print(f"  {C.DIM}Tolerancia: +/- 1 dia{C.RESET}")

    pause()

# ══════════════════════════════════════════════════════════════════════════════
#  MENU PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
def menu(cfg, df):
    while True:
        draw_header()
        nf = df["fazenda"].nunique(); nu = df["chave"].nunique(); na = df["atividade"].nunique()
        nt = len(cfg.get("tarifas", {})); nm = len(cfg.get("de_para", {}))
        draw_status_box({"Base de Dados": f"{nf} Fazendas  {B.BULLET}  {nu} TALHOES  {B.BULLET}  {na} Atividades", "Configuracoes": f"{nt} Tarifas importadas  {B.BULLET}  {nm} Mapeamentos"})
        print(f"\n  {C.BOLD}{C.WHITE}ORCAMENTO E SIMULACAO{C.RESET}")
        print(f"  {C.GREEN}[1]{C.RESET} {C.WHITE}Orcar fazenda completa{C.GRAY} (TALHAO x atividade x equipe){C.RESET}")
        print(f"  {C.GREEN}[2]{C.RESET} {C.WHITE}Sprint{C.GRAY} - simulacao rapida por funcao/alvo{C.RESET}")
        print(f"  {C.GREEN}[3]{C.RESET} {C.WHITE}Comparativo Manual vs Mecanizado{C.GRAY} (prazo){C.RESET}")
        print(f"\n  {C.BOLD}{C.WHITE}CONFIGURACOES E DADOS{C.RESET}")
        print(f"  {C.GREEN}[4]{C.RESET} {C.WHITE}Configurar rendimentos orcados{C.GRAY} (h/ha){C.RESET}")
        print(f"  {C.GREEN}[5]{C.RESET} {C.WHITE}Configurar equipe e jornada padrao{C.RESET}")
        print(f"  {C.GREEN}[6]{C.RESET} {C.WHITE}Ver catalogo de dados{C.RESET}")
        print(f"\n  {C.BOLD}{C.WHITE}MODULOS AVANCADOS{C.RESET}")
        print(f"  {C.GREEN}[7]{C.RESET} {C.CYAN}IMPORT{C.RESET} {C.WHITE}Importar tarifas{C.GRAY} (Excel){C.RESET}")
        print(f"  {C.GREEN}[8]{C.RESET} {C.CYAN}OTIMIZ{C.RESET} {C.WHITE}Otimizacao financeira{C.GRAY} (Mec vs Manual -> R$){C.RESET}")
        print(f"  {C.GREEN}[9]{C.RESET} {C.CYAN}ESCOPO{C.RESET} {C.WHITE}Escopo de meses{C.GRAY} (dias uteis){C.RESET}")
        print(f"  {C.GREEN}[10]{C.RESET} {C.CYAN}PROVA{C.RESET} {C.WHITE}Prova Real{C.GRAY} (validacao de calculos vs Excel){C.RESET}")
        print(f"  {C.GREEN}[M]{C.RESET} {C.CYAN}MAPEAR{C.RESET} {C.WHITE}Ver mapeamentos de_para{C.RESET}")
        print(f"\n  {C.GRAY}[0] Sair do sistema{C.RESET}")
        draw_line(B.h)
        v = prompt("Opcao").strip().upper()
        if v == "1": modulo_orcar_fazenda(cfg, df)
        elif v == "2": modulo_sprint(cfg, df)
        elif v == "3": modulo_comparativo_mec(cfg, df)
        elif v == "4": modulo_rendimentos(cfg, df)
        elif v == "5": modulo_equipe(cfg)
        elif v == "6": modulo_catalogo(df)
        elif v == "7": modulo_importar_tarifas(cfg)
        elif v == "8": modulo_otimizacao_financeira(cfg, df)
        elif v == "9": modulo_escopo_meses(cfg, df)
        elif v == "10": modulo_prova_real(cfg)
        elif v == "M": modulo_ver_mapeamentos(cfg)
        elif v == "0": sair()
        else: msg_warn("Opcao invalida.")

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    if os.name == 'nt': os.system('color')
    draw_header()
    print(f"  {C.DIM}Inicializando sistema...{C.RESET}\n")
    print(f"  {C.GRAY}Terminal: Unicode={'Sim' if TERM_CAPS['unicode'] else 'Nao'}  |  RGB={'Sim' if TERM_CAPS['rgb'] else 'Nao'}{C.RESET}")
    cfg = carregar_config()
    df = carregar_planilha(cfg)
    if df is None or len(df) == 0:
        msg_error("Nao foi possível carregar dados. Saindo...")
        pause()
        return
    msg_ok(f"Dados carregados. {len(df)} registros  |  {df['fazenda'].nunique()} fazendas  |  {df['chave'].nunique()} TALHOES")
    nt = len(cfg.get("tarifas", {}))
    if nt > 0: print(f"  {C.GREEN}Tarifas: {nt} importadas{C.RESET}")
    else: print(f"  {C.YELLOW}[{B.WARN}] Tarifas nao importadas. Use opcao [7] no menu.{C.RESET}")
    pause("Pressione ENTER para continuar")
    menu(cfg, df)

if __name__ == "__main__":
    main()
