"""
SRF — Sistema de Restauracao Florestal  v5.9  (Logistica & Dossier executivo)
Baseado no ATM v3 de Isaac (Zaza), reescrito com Smart Scheduler
Uso  : python atm_v5.py
       ATM_DEMO=1 python atm_v5.py
       python atm_v5.py --demo
       Modo DEMO: se existir USEESTAPLANILHAULIANOPOLIS.xlsx, gera/atualiza ulianopolisswg.xlsx;
       tarifas CT 313 como no fluxo normal; [1] usa a fazenda com mais linhas (micro municipio Ulianopolis).
"""

import calendar
import datetime
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import unicodedata
from collections import OrderedDict, defaultdict
from statistics import median

import pandas as pd

try:
    from srf_monitor_state import (
        append_relatorio as _monitor_append_relatorio,
    )
    from srf_monitor_state import (
        build_rendimentos_from_demandas as _monitor_build_rendimentos,
    )
    from srf_monitor_state import (
        default_state_path as _monitor_default_state_path,
    )
    from srf_monitor_state import (
        merge_emit as _monitor_merge_emit,
    )
except Exception:
    _monitor_append_relatorio = None
    _monitor_build_rendimentos = None
    _monitor_default_state_path = None
    _monitor_merge_emit = None

try:
    from rich.console import Console
    from rich.table import Table
except ImportError:
    print("Instale: pip install rich pandas openpyxl")
    sys.exit(1)

# ──────────────────────────────────────────────
#  CORES & UI (estilo ATM v3)
# ──────────────────────────────────────────────
try:
    import colorama

    colorama.init()
    G = "\033[92m"
    Y = "\033[93m"
    R = "\033[91m"
    C = "\033[96m"
    DM = "\033[2m"
    BL = "\033[1m"
    RS = "\033[0m"
except ImportError:
    G = Y = R = C = DM = BL = RS = ""

W = 66
console = Console()

ASCII_ART = r"""
        ,@@@@@@@,
    ,,,.   ,@@@@@@/@@,  .oo8888o.
    ,&%%&%&&%,@@@@@/@@@@@@,8888\88/8o
,%&\%&&%&&%,@@@\@@@/@@@88\88888/88'
%&&%&%&/%&&%@@\@@/ /@@@88888\88888'
%&&%/ %&%%&&@@\ V /@@' `88\8 `/88'
`&%\ ` /%&'    |.|        \ '|8'
    |o|        | |         | |
    |.|        | |         | |
    \\/ ._\//_/__/  ,\_//__\\/.  \_//__/_
"""

VERSION = "7.0"
APP_NAME = "SRF v7 - Sistema de Restauracao Florestal"
DIR = os.path.dirname(os.path.abspath(__file__))
CFGP = os.path.join(DIR, "config.json")
DOSSIER_DIRNAME = "dossiês"

# Modo DEMO (Ulianópolis): ATM_DEMO=1 ou --demo
# Fonte de verdade para reconstruir o demo: USEESTAPLANILHAULIANOPOLIS.xlsx (municipio Ulianopolis)
DEMO_MICRO_FILENAME = "ulianopolisswg.xlsx"
DEMO_MICRO_SOURCE_FILENAME = "USEESTAPLANILHAULIANOPOLIS.xlsx"

# ──────────────────────────────────────────────
# SRF v7 ENHANCEMENTS
# ──────────────────────────────────────────────

def _parse_intervalo_selecao(intervalo_str, max_idx):
    """
    Converte string de seleção em intervalos para lista de índices.
    Exemplos:
        "1,3,5-7,9,15-20" -> [1, 3, 5, 6, 7, 9, 15, 16, 17, 18, 19, 20]
        "TODAS" -> [1, 2, 3, ..., max_idx]
        "1-5,10-20,30" -> [1,2,3,4,5,10,11,12,13,14,15,16,17,18,19,20,30]
    """
    if not intervalo_str or not intervalo_str.strip():
        return []
    
    intervalo_str = intervalo_str.strip().upper()
    
    if intervalo_str in ("TODAS", "TODOS", "T", "ALL", "A"):
        return list(range(1, max_idx + 1))
    
    indices = set()
    partes = intervalo_str.replace(";", ",").split(",")
    
    for parte in partes:
        parte = parte.strip()
        if "-" in parte:
            try:
                inicio, fim = parte.split("-")
                inicio = int(inicio.strip())
                fim = int(fim.strip())
                if 1 <= inicio <= max_idx and 1 <= fim <= max_idx:
                    indices.update(range(min(inicio, fim), max(inicio, fim) + 1))
            except ValueError:
                pass
        else:
            try:
                idx = int(parte)
                if 1 <= idx <= max_idx:
                    indices.add(idx)
            except ValueError:
                pass
    
    return sorted(list(indices))


def _iniciar_monitores_companhia(pid=None, auto_spawn=True):
    """
    SRF v7: Inicia conjunto completo de monitores para exibição persistente.
    
    Monitores da Companhia:
    1. meta - Contexto operacional
    2. rendimentos - HH/h por atividade
    3. relatorios - Auditoria e diagnósticos
    4. custo - Custos acumulados em tempo real
    5. territorio - Distribuição por cidade/equipe
    """
    if not auto_spawn or os.environ.get("SRF_MONITOR_DISABLED", "0") == "1":
        return []
    
    try:
        feeds = [
            ("meta", "SRF v7 - Contexto"),
            ("rendimentos", "SRF v7 - HH/h por Atividade"),
            ("relatorios", "SRF v7 - Auditoria"),
            ("custo", "SRF v7 - Custos"),
            ("territorio", "SRF v7 - Distribuição Geográfica"),
        ]
        
        abertos = []
        for feed, titulo in feeds:
            try:
                if _abrir_monitor_janela(feed, pid, titulo=titulo):
                    abertos.append(feed)
            except Exception as e:
                debug_info = f"Monitor {feed} falhou: {str(e)[:80]}"
                if callable(_monitor_merge_emit) and _MONITOR_STATE_PATH:
                    _monitor_merge_emit(_MONITOR_STATE_PATH, {
                        "debug_startup": {"erro": debug_info}
                    })
        
        return abertos
    except Exception as e:
        print(DM + f"Inicialização de monitores falhou: {e}" + RS)
        return []


def _abrir_monitor_janela(feed="meta", pid=None, titulo=None):
    """
    SRF v7: Abre uma janela separada com o monitor SRF.
    Usa subprocess com Kitty preferencial para CachyOS/Hyprland.
    
    Retorna: True se abriu, False se falhou
    """
    try:
        target_pid = int(pid or os.getpid())
        script_monitor = os.path.join(DIR, "srf_monitor.py")

        if not os.path.isfile(script_monitor):
            print(DM + f"Script do monitor não encontrado: {script_monitor}" + RS)
            return False

        cmd = [
            sys.executable,
            script_monitor,
            "--feed", str(feed),
            "--pid", str(target_pid),
            "--interval", "0.5",
        ]

        terminal_cmd = None
        
        # DETECÇÃO INTELIGENTE DE TERMINAL - Kitty para CachyOS
        try:
            # Verifica se kitty está instalado
            subprocess.run(["kitty", "--version"], capture_output=True, check=True)
            # Kitty no modo floating para Hyprland/Wayland
            window_title = titulo or f"SRF v7 - {feed}"
            terminal_cmd = [
                "kitty",
                "--title", window_title,
                "--name", f"srf-monitor-{feed}",
                "-e"
            ] + cmd
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback para outros terminais
            terminais = [
                ("foot", ["foot", "-t", titulo or f"SRF v7", "-e"] + cmd),
                ("wezterm", ["wezterm", "start", "--", "--title", titulo or f"SRF v7"] + cmd),
                ("alacritty", ["alacritty", "--title", titulo or f"SRF v7", "-e"] + cmd),
                ("gnome-terminal", ["gnome-terminal", "--title", titulo or f"SRF v7", "--"] + cmd),
            ]
            
            for nome_term, term_cmd in terminais:
                try:
                    subprocess.run([nome_term, "--version"], capture_output=True, check=True)
                    terminal_cmd = term_cmd
                    break
                except Exception:
                    continue

        if terminal_cmd:
            subprocess.Popen(
                terminal_cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(0.8)  # Pausa para janela iniciar
            return True
        return False
    except Exception as e:
        print(DM + f"Erro ao abrir monitor {feed}: {e}" + RS)
        return False


# Territory Logic - From Requirements - Integrated
def _carregar_territorios_por_fazenda(df_micro):
    """
    SRF v7: Carrega distribuição geográfica de fazendas por cidade/território.
    Baseado nos requisitos:
    - Cachoeira (Cidelandia, Acailandia) -> INOVESA
    - Buritirana -> SWG
    - Ulianopolis, Paragominas -> SWG para manutenção fase 3
    - Dom Eliseu -> INOVESA
    """
    if df_micro is None or df_micro.empty:
        return {}
    
    territorios = {}
    
    # Mapeia cidades para equipes (SWG vs INOVESA)
    cidade_para_equipe = {
        # SWG
        "ulianopolis": "swg",
        "paragominas": "swg",
        "buritirana": "swg",
        # INOVESA
        "cidelandia": "inovesa",
        "acailandia": "inovesa",
        "dom eliseu": "inovesa",
        "cachoeira": "inovesa",
    }
    
    for idx, row in df_micro.iterrows():
        if 'fazenda' not in row or 'cidade' not in row:
            continue
            
        fazenda = str(row['fazenda']).strip().lower()
        cidade = str(row.get('cidade', '')).strip().lower()
        
        # Determina equipe baseada em cidade ou nome da fazenda
        equipe_base = None
        
        # Primeiro tenta mapeamento direto por cidade
        for cidade_key, equipe in cidade_para_equipe.items():
            if cidade_key in cidade:
                equipe_base = equipe
                break
        
        # Fallback: mapeamento por nome da fazenda
        if not equipe_base:
            for cidade_key, equipe in cidade_para_equipe.items():
                if cidade_key in fazenda:
                    equipe_base = equipe
                    break
        
        # Default por características da fazenda
        if not equipe_base:
            if "swg" in fazenda or "sao" in fazenda:
                equipe_base = "swg"
            else:
                equipe_base = "inovesa"
        
        territorios[fazenda] = {
            'cidade': cidade,
            'equipe_base': equipe_base,
            'coordenadas': (row.get('latitude'), row.get('longitude'))
        }
    
    return territorios


def _sugerir_equipe_por_fazenda(fazenda, territorios):
    """
    SRF v7: Sugere equipe para fazenda baseada em lógica de território.
    Retorna: (equipe_sugerida, confianca, motivo)
    """
    if not territorios or not fazenda:
        return None, 0.0, "Sem dados de território"
    
    fazenda_key = str(fazenda).strip().lower()
    
    # Procura match exato
    for f, info in territorios.items():
        if f in fazenda_key or fazenda_key in f:
            return info['equipe_base'], 1.0, f"Match direto: {info['cidade']}"
    
    # Probabilidade baseada em substring
    cidade_keywords = {
        'swg': ['buritirana', 'ulianopolis', 'paragominas', 'sao', 'swg'],
        'inovesa': ['cidelandia', 'acailandia', 'dom eliseu', 'cachoeira', 'inovesa']
    }
    
    for equipe, keywords in cidade_keywords.items():
        for keyword in keywords:
            if keyword in fazenda_key:
                return equipe, 0.8, f"Probabilidade: contém '{keyword}'"
    
    return None, 0.0, "Nenhum match encontrado"


def _is_demo_mode():
    v = os.environ.get("ATM_DEMO", "").strip().lower()
    if v in ("1", "true", "yes", "sim", "on"):
        return True
    return "--demo" in sys.argv


def _is_legacy_mode():
    v = os.environ.get("ATM_LEGACY", "").strip().lower()
    if v in ("1", "true", "yes", "sim", "on"):
        return True
    return "--legacy" in sys.argv


def _is_beta_mode():
    # Fluxo beta promovido a padrão; legado fica opt-in por flag/env.
    if _is_legacy_mode():
        return False
    v = os.environ.get("ATM_BETA", "").strip().lower()
    if v in ("0", "false", "no", "off"):
        return False
    return True


def _is_demo_micro_path(path_or_name):
    if not path_or_name:
        return False
    return os.path.basename(str(path_or_name)).lower() == DEMO_MICRO_FILENAME.lower()


# ──────────────────────────────────────────────
#  MAPEAMENTO FIXO DE COLUNAS CONHECIDAS
#  (fallback semantico so se nenhuma bater)
# ──────────────────────────────────────────────
KNOWN_COLUMNS = {
    "fazenda": ["NOME FAZENDA", "CÓDIGO FAZENDA"],
    "chave": ["CHAVE POLÍGONO", "CHAVE POLIGONO"],
    "area": [
        "ÁREA TRABALHADA ESTIMADA (HECTARE)",
        "ÁREA POLÍGONO (HECTARE)",
        "AREA POLIGONO (HECTARE)",
        "AREA TRABALHADA ESTIMADA (HECTARE)",
    ],
    "atividade": ["ATIVIDADES", "ATIVIDADE"],
}


def linha(c="="):
    print(G + c * W + RS)


def sub(c="-"):
    print(DM + c * W + RS)


def cabecalho(sub_titulo=""):
    os.system("cls" if os.name == "nt" else "clear")
    print(G + ASCII_ART + RS)
    linha()
    print(G + BL + f"  [ SRF ]  {APP_NAME}  v{VERSION}".center(W) + RS)
    if sub_titulo:
        print(DM + G + sub_titulo.center(W) + RS)
    print(DM + G + datetime.datetime.now().strftime("  %d/%m/%Y  %H:%M").center(W) + RS)
    linha()

def subcabecalho(sub_titulo=""):
    """Versão incremental que não limpa a tela, mantém conteúdo anterior."""
    print("\n" + "─" * W)
    print(G + BL + f"  [ SRF ]  {APP_NAME}  v{VERSION}".center(W) + RS)
    if sub_titulo:
        print(DM + G + sub_titulo.center(W) + RS)
    print(DM + G + datetime.datetime.now().strftime("  %d/%m/%Y  %H:%M").center(W) + RS)
    print("─" * W + "\n")


def aviso(m):
    print(Y + f"\n  !  {m}" + RS)


def erro(m):
    print(R + f"\n  X  {m}" + RS)


def ok(m):
    print(G + f"\n  +  {m}" + RS)


def prompt(msg, default=None):
    suf = f" [{default}]" if default is not None else ""
    try:
        v = input(G + "  >> " + C + msg + suf + G + ": " + RS).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    return v if v else (str(default) if default is not None else "")


def pedir_float(msg, default, allow_zero=False):
    while True:
        v = prompt(msg, default)
        try:
            f = float(str(v).replace(",", "."))
            if f > 0 or (allow_zero and f >= 0):
                return f
        except ValueError:
            pass
        aviso("Valor invalido.")


def pedir_int(msg, default, allow_zero=False):
    while True:
        v = prompt(msg, default)
        try:
            i = int(v)
            if i > 0 or (allow_zero and i >= 0):
                return i
        except ValueError:
            pass
        aviso("Valor invalido.")


def selecionar(titulo, itens, zero_label="Voltar"):
    print(G + f"\n  -- {titulo} " + "--" * max(0, (W - len(titulo) - 6) // 2) + RS)
    for i, it in enumerate(itens, 1):
        print(G + f"  [{i:2}] " + C + str(it) + RS)
    print(G + f"  [ 0] " + DM + zero_label + RS)
    while True:
        v = prompt("Escolha").strip()
        if v == "0":
            return None
        if v.isdigit() and 1 <= int(v) <= len(itens):
            return itens[int(v) - 1]
        aviso("Opcao invalida.")


def selecionar_paginado(titulo, itens, page_size=5, zero_label="Voltar"):
    total = len(itens)
    page = 0
    max_page = math.ceil(total / page_size) - 1
    while True:
        start = page * page_size
        end = min(start + page_size, total)
        print(
            G
            + f"\n  -- {titulo} (pag {page + 1}/{max_page + 1}) "
            + "--" * max(0, (W - len(titulo) - 16) // 2)
            + RS
        )
        for i in range(start, end):
            print(G + f"  [{i + 1:2}] " + C + str(itens[i]) + RS)
        nav = []
        if page > 0:
            nav.append("[-] Anterior")
        if page < max_page:
            nav.append("[+] Proxima")
        nav.append("[0] " + zero_label)
        print(DM + "  " + "   ".join(nav) + RS)
        v = prompt("Escolha").strip()
        if v == "0":
            return -1
        if v == "+" and page < max_page:
            page += 1
            continue
        if v == "-" and page > 0:
            page -= 1
            continue
        if v.isdigit() and 1 <= int(v) <= total:
            return int(v) - 1
        aviso("Opcao invalida.")


def confirmar(msg, default=True):
    s = "S/n" if default else "s/N"
    v = prompt(f"{msg} [{s}]").strip().lower()
    if not v:
        return default
    return v in ("s", "sim", "y", "yes")


def remover_acentos(texto):
    if not isinstance(texto, str):
        return ""
    return (
        "".join(
            c
            for c in unicodedata.normalize("NFD", texto)
            if unicodedata.category(c) != "Mn"
        )
        .lower()
        .strip()
    )


import re

_RE_PUNCT = re.compile(r"[^a-z0-9 ]+")
_RE_SPACES = re.compile(r"\s+")


def normalizar_chave(texto):
    """remover_acentos + strip punctuation + collapse whitespace. Canonical lookup key."""
    s = remover_acentos(texto)
    s = _RE_PUNCT.sub(" ", s)
    return _RE_SPACES.sub(" ", s).strip()


def _normalizar_chave_atividade_semantica(texto):
    """
    Normaliza texto de atividade preservando semantica de tokens de fase.
    Regra de negocio (supervisor): PL=Plantio, CD=Conducao.
    Mantem retrocompatibilidade com chaves legadas ao ser usado em conjunto com
    _candidatos_chave_atividade().
    """
    base = normalizar_chave(texto)
    if not base:
        return base
    toks = base.split()
    out = []
    for i, t in enumerate(toks):
        prev = toks[i - 1] if i > 0 else ""
        if t == "pl" and prev in ("impl", "implant", "implantacao"):
            out.append("plantio")
        elif t == "cd" and prev in ("impl", "implant", "implantacao"):
            out.append("conducao")
        else:
            out.append(t)
    return " ".join(out).strip()


def _candidatos_chave_atividade(texto):
    """
    Gera variantes de chave para lookup robusto:
    1) legado (PL/CD literal), 2) semantico (Plantio/Conducao).
    """
    legado = normalizar_chave(texto)
    semantico = _normalizar_chave_atividade_semantica(texto)
    if semantico and semantico != legado:
        return [legado, semantico]
    return [legado]


def _formatar_periodo_meta(mes_ref, ano_ref, prazo_meses):
    """Retorna (inicio, fim) do periodo meta em texto (MM/AAAA)."""
    try:
        mes_ref = int(mes_ref)
        ano_ref = int(ano_ref)
        prazo_meses = int(round(float(prazo_meses)))
    except Exception:
        return None
    inicio = f"{mes_ref:02d}/{ano_ref}"
    if prazo_meses <= 0:
        return (inicio, inicio)
    mes_fim = mes_ref + (prazo_meses - 1)
    ano_fim = ano_ref + (mes_fim - 1) // 12
    mes_fim = ((mes_fim - 1) % 12) + 1
    fim = f"{mes_fim:02d}/{ano_fim}"
    return (inicio, fim)


def _formatar_data_dia(dia, mes, ano):
    """Formata data DD/MM/AAAA; assume valores inteiros validos."""
    return f"{int(dia):02d}/{int(mes):02d}/{int(ano)}"


# Mapeamento de dias da semana para abreviacoes brasileiras
_DIAS_SEMANA_CURTO = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
_DIAS_SEMANA_COMPLETO = [
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sábado",
    "Domingo",
]


def _converter_dia_simulado_para_data(
    dia_simulado: int, dia_ref: int, mes_ref: int, ano_ref: int
):
    """
    Converte dia simulado (1, 2, 3...) para data real.
    Considera todos os dias do calendario (incluindo fins de semana).

    Retorna: (data_str, dia_semana_curto, dia_semana_completo, data_obj)
    Ex: (1, 20, 4, 2025) -> ("20/04/2025", "Seg", "Segunda-feira", date_obj)
    """
    try:
        from datetime import date, timedelta

        dia_simulado = int(dia_simulado)
        dia_ref = int(dia_ref)
        mes_ref = int(mes_ref)
        ano_ref = int(ano_ref)

        # Data de inicio
        data_inicio = date(ano_ref, mes_ref, dia_ref)

        # Adiciona (dia_simulado - 1) dias (dia 1 = data_inicio)
        data_real = data_inicio + timedelta(days=dia_simulado - 1)

        # Formata data como DD/MM/AAAA
        data_str = f"{data_real.day:02d}/{data_real.month:02d}/{data_real.year}"

        # Obtem dia da semana (0=Segunda, 6=Domingo)
        dia_semana_idx = data_real.weekday()
        dia_semana_curto = _DIAS_SEMANA_CURTO[dia_semana_idx]
        dia_semana_completo = _DIAS_SEMANA_COMPLETO[dia_semana_idx]

        return (data_str, dia_semana_curto, dia_semana_completo, data_real)
    except Exception:
        return (f"Dia_{dia_simulado}", "-", "-", None)


def _calcular_data_fim_por_meses(dia_inicio, mes_ref, ano_ref, prazo_meses):
    """
    Calcula data final (dia/mes/ano) a partir de um dia inicial e prazo em meses.
    Ajusta o dia para o maximo do mes final.
    """
    try:
        dia_inicio = int(dia_inicio)
        mes_ref = int(mes_ref)
        ano_ref = int(ano_ref)
        prazo_meses = int(round(float(prazo_meses)))
    except Exception:
        return None
    if prazo_meses <= 0:
        return (dia_inicio, mes_ref, ano_ref)
    mes_fim = mes_ref + (prazo_meses - 1)
    ano_fim = ano_ref + (mes_fim - 1) // 12
    mes_fim = ((mes_fim - 1) % 12) + 1
    ultimo_dia = calendar.monthrange(ano_fim, mes_fim)[1]
    dia_fim = min(max(1, dia_inicio), int(ultimo_dia))
    return (dia_fim, mes_fim, ano_fim)


# ──────────────────────────────────────────────
# CONTEXT DASHBOARD (PERSISTENTE)
# ──────────────────────────────────────────────
class ContextoSessao:
    """Armazena todas as escolhas importantes durante a sessão para exibição no dashboard."""

    def __init__(self):
        self.fazenda_selecionada = None
        self.fazenda_metadata = {}
        self.equipe_selecionada = None
        self.talhoes_selecionados = []
        self.total_talhoes_fazenda = 0
        self.area_total_fazenda = 0.0
        self.data_inicio = None
        self.data_termino = None
        self.atividades_distribuidas = 0
        self.total_atividades = 0
        self.modo_atual = None
        self.orcamento_estrito = True
        self.tarifas_carregadas = 0
        self.custos_globais_ativos = False
        self.valor_direto_total = 0.0
        self.valor_indireto_total = 0.0
        self.timestamp_atualizacao = None
        self._console = Console()

    def atualizar_fazenda(self, nome_fazenda, df_fazenda=None):
        """Atualiza informações da fazenda selecionada."""
        self.fazenda_selecionada = nome_fazenda
        if df_fazenda is not None:
            self.total_talhoes_fazenda = (
                df_fazenda["chave"].nunique() if "chave" in df_fazenda.columns else 0
            )
            if "area" in df_fazenda.columns:
                self.area_total_fazenda = df_fazenda["area"].sum()
            elif "area_ha" in df_fazenda.columns:
                self.area_total_fazenda = df_fazenda["area_ha"].sum()
            else:
                self.area_total_fazenda = 0.0
        else:
            self.total_talhoes_fazenda = 0
            self.area_total_fazenda = 0.0
        self.timestamp_atualizacao = datetime.datetime.now()

    def atualizar_equipe(self, nome_equipe):
        """Atualiza equipe selecionada."""
        self.equipe_selecionada = nome_equipe
        self.timestamp_atualizacao = datetime.datetime.now()

    def definir_escopo_talhoes(self, talhoes_selecionados, todos_talhoes):
        """Define os talhões selecionados e atualiza metadados."""
        self.talhoes_selecionados = (
            list(set(talhoes_selecionados))
            if isinstance(talhoes_selecionados, list)
            else []
        )
        self.total_talhoes_fazenda = (
            len(set(todos_talhoes)) if isinstance(todos_talhoes, list) else 0
        )
        self.timestamp_atualizacao = datetime.datetime.now()

    def atualizar_atividades(self, distribuidas, total):
        """Atualiza contagem de atividades distribuídas vs total."""
        self.atividades_distribuidas = distribuidas
        self.total_atividades = total
        self.timestamp_atualizacao = datetime.datetime.now()

    def definir_datas(self, inicio, termino):
        """Define datas de início e término da operação."""
        self.data_inicio = inicio
        self.data_termino = termino
        self.timestamp_atualizacao = datetime.datetime.now()

    def atualizar_modo(self, modo):
        """Atualiza o modo atual (single, lote, multi_equipe)."""
        self.modo_atual = modo
        self.timestamp_atualizacao = datetime.datetime.now()

    def atualizar_configuracoes(self, cfg):
        """Atualiza configurações importantes do sistema."""
        self.orcamento_estrito = (
            cfg.get("orcamento_estrito", True) if isinstance(cfg, dict) else True
        )
        self.tarifas_carregadas = (
            len(cfg.get("tarifas", {})) if isinstance(cfg, dict) else 0
        )

        cg = (cfg.get("custos_globais") or {}) if isinstance(cfg, dict) else {}
        if cg and (
            float(cg.get("valor_direto_total", 0) or 0) > 0
            or float(cg.get("valor_indireto_total", 0) or 0) > 0
        ):
            self.custos_globais_ativos = True
            self.valor_direto_total = float(cg.get("valor_direto_total", 0) or 0)
            self.valor_indireto_total = float(cg.get("valor_indireto_total", 0) or 0)
        else:
            self.custos_globais_ativos = False
        self.timestamp_atualizacao = datetime.datetime.now()

    def limpar_contexto(self):
        """Limpa o contexto para iniciar nova sessão."""
        self.__init__()

    def _criar_tabela_dashboard(self):
        """Cria a tabela Rich formatada com informações do contexto."""
        table = Table(
            title="[bold cyan]Dashboard de Contexto[/bold cyan]",
            show_header=True,
            header_style="bold cyan",
            border_style="bright_blue",
            padding=(0, 1),
        )

        # Colunas principais
        table.add_column("Fazenda", style="bold green", width=30, justify="left")
        table.add_column("Equipe", style="bold yellow", width=20, justify="left")
        table.add_column("Talhoes", style="bold blue", width=15, justify="center")
        table.add_column(
            "Atividades", style="bold magenta", width=15, justify="center"
        )
        table.add_column("Datas", style="bold red", width=25, justify="left")

        # Preparar dados de cada coluna
        fazenda_info = "[dim]Não selecionada[/dim]"
        if self.fazenda_selecionada:
            fazenda_info = f"[bold green]{self.fazenda_selecionada}[/bold green]"
            meta_parts = []
            if self.total_talhoes_fazenda > 0:
                qtd_talhoes = (
                    len(self.talhoes_selecionados)
                    if self.talhoes_selecionados
                    else self.total_talhoes_fazenda
                )
                meta_parts.append(f"{qtd_talhoes}/{self.total_talhoes_fazenda} talhões")
            if self.area_total_fazenda > 0:
                meta_parts.append(f"{self.area_total_fazenda:,.1f}ha")
            if meta_parts:
                fazenda_info += f"\n[dim]{' | '.join(meta_parts)}[/dim]"

        equipe_info = self.equipe_selecionada or "[dim]Não selecionada[/dim]"

        talhoes_info = "[dim]0/0[/dim]"
        if self.total_talhoes_fazenda > 0:
            qtd = (
                len(self.talhoes_selecionados)
                if self.talhoes_selecionados
                else self.total_talhoes_fazenda
            )
            talhoes_info = f"[bold]{qtd}/{self.total_talhoes_fazenda}[/bold]"

        atividades_info = "[dim]0/0[/dim]"
        if self.total_atividades > 0:
            atividades_info = (
                f"[bold]{self.atividades_distribuidas}/{self.total_atividades}[/bold]"
            )

        datas_info = "[dim]Não definidas[/dim]"
        if self.data_inicio or self.data_termino:
            datas_parts = []
            if self.data_inicio:
                datas_parts.append(f"Início: {self.data_inicio}")
            if self.data_termino:
                datas_parts.append(f"Término: {self.data_termino}")
            datas_info = "\n".join(datas_parts)

        # Adicionar linha principal
        table.add_row(
            fazenda_info, equipe_info, talhoes_info, atividades_info, datas_info
        )

        # Segunda linha com informações adicionais (se houver)
        info_adicional = []
        if self.modo_atual:
            info_adicional.append(
                f"[cyan]Modo:[/cyan] [white]{self.modo_atual}[/white]"
            )
        if self.tarifas_carregadas > 0:
            info_adicional.append(
                f"[cyan]Tarifas:[/cyan] [white]{self.tarifas_carregadas}[/white]"
            )
        if self.custos_globais_ativos:
            total = self.valor_direto_total + self.valor_indireto_total
            info_adicional.append(f"[cyan]Custos:[/cyan] [white]R${total:,.2f}[/white]")
        if not self.orcamento_estrito:
            info_adicional.append("[cyan]Orçamento:[/cyan] [white]Flexível[/white]")

        if info_adicional:
            table.add_row(
                "\n" + "\n".join(info_adicional), "", "", "", "", end_section=True
            )

        return table

    def exibir(self, console_inst=None, mostrar_sempre=True):
        """Exibe o dashboard formatado no console."""
        # Não mostrar se nada foi selecionado e mostrar_sempre=False
        if not mostrar_sempre and not self.fazenda_selecionada:
            return

        console_inst = console_inst or self._console
        table = self._criar_tabela_dashboard()
        console_inst.print("\n", table, "\n")


# Instância global do contexto
contexto_sessao = ContextoSessao()
_MONITOR_STATE_PATH = (
    _monitor_default_state_path(os.getpid())
    if callable(_monitor_default_state_path)
    else None
)


def _emit_monitor_state(partial):
    if _MONITOR_STATE_PATH and callable(_monitor_merge_emit):
        try:
            _monitor_merge_emit(_MONITOR_STATE_PATH, partial)
        except Exception:
            pass


def _emit_monitor_relatorio(titulo, texto):
    if _MONITOR_STATE_PATH and callable(_monitor_append_relatorio):
        try:
            _monitor_append_relatorio(_MONITOR_STATE_PATH, titulo, texto)
        except Exception:
            pass


def _emitir_monitor_atual():
    """Emite o estado atual do contexto para os monitores."""
    if not (_MONITOR_STATE_PATH and callable(_monitor_merge_emit)):
        return
    
    try:
        # Construir estado parcial do contexto atual - FORMATO ESPERADO PELOS MONITORES
        estado = {}
        
        # Operação: fazenda, modo, equipe (para feed "meta")
        if contexto_sessao.fazenda_selecionada:
            estado["operacao"] = {
                "fazenda_atual": str(contexto_sessao.fazenda_selecionada),
                "modo": str(contexto_sessao.modo_atual or ""),
                "equipe_atual": str(contexto_sessao.equipe_selecionada or ""),
                "status_geral": "em_execucao",
            }
            
            # Adicionar mensagem curta com contexto
            msg_parts = []
            if contexto_sessao.fazenda_selecionada:
                msg_parts.append(str(contexto_sessao.fazenda_selecionada))
            if contexto_sessao.equipe_selecionada:
                msg_parts.append(f"Eq:{contexto_sessao.equipe_selecionada}")
            if msg_parts:
                estado["operacao"]["mensagem_curta"] = " | ".join(msg_parts)
        
        # Lote: talhões, atividades (para feed "meta" - lote section)
        if contexto_sessao.talhoes_selecionados is not None:
            estado["lote"] = {
                "talhoes_selecionados": len(contexto_sessao.talhoes_selecionados),
                "talhoes_total": contexto_sessao.total_talhoes_fazenda,
                "area_ha": contexto_sessao.area_total_fazenda,
                # Adicionar campos que o monitor espera
                "dias_meta": 0,  # placeholder - será atualizado depois se necessário
                "dias_consumidos": 0,
                "saldo_dias": 0,
                "status_meta_continuo": "OK",
                "prazo_absoluto": True,
            }
        
        # Atividades distribuídas (vamos usar para rendimentos_sessao simplificado)
        # Nota: O monitor de rendimentos espera uma lista de {atividade, hh_ha, origem, chave_tarifa}
        # Vamos simplificar e enviar o que temos por enquanto
        if contexto_sessao.total_atividades > 0 and contexto_sessao.atividades_distribuidas > 0:
            # Criar uma entrada simplificada para mostrar que há atividades vinculadas
            estado["rendimentos_sessao"] = [{
                "atividade": f"{contexto_sessao.atividades_distribuidas}/{contexto_sessao.total_atividades} atividades",
                "hh_ha": 0.0,  # vamos calcular depois se necessário
                "origem": "sessao",
                "chave_tarifa": "progresso"
            }]
        
        # Timestamp
        if contexto_sessao.timestamp_atualizacao:
            estado["timestamp"] = contexto_sessao.timestamp_atualizacao.timestamp()
            estado["timestamp_iso"] = contexto_sessao.timestamp_atualizacao.strftime("%Y-%m-%dT%H:%M:%S")
        
        _monitor_merge_emit(_MONITOR_STATE_PATH, estado)
    except Exception:
        pass  # Silent fail to not disrupt main flow


def _emitir_monitor_rendimentos(atividade_nome: str, vincular: bool, hh_ha: float = 0.0, origem: str = "", chave_tarifa: str = ""):
    """Emite atualização de rendimento quando uma atividade é vinculada/desvinculada."""
    if not (_MONITOR_STATE_PATH and callable(_monitor_merge_emit)):
        return
    
    try:
        # Para o feed de rendimentos, vamos manter uma lista acumulativa
        # Primeiro, tentar obter o estado atual para manter o que já temos
        estado_atual = {}
        rendimentos_existentes = []
        
        # Obter estado atual existente (se houver)
        if _MONITOR_STATE_PATH and os.path.exists(_MONITOR_STATE_PATH):
            try:
                import json
                with open(_MONITOR_STATE_PATH, 'r', encoding='utf-8') as f:
                    dados_existentes = json.load(f)
                    rendimentos_existentes = dados_existentes.get('rendimentos_sessao', []).copy()
            except:
                rendimentos_existentes = []
        
        # Processar a atividade atual
        if atividade_nome and vincular and hh_ha > 0:
            # Verificar se esta atividade já existe na lista (para atualizar ou adicionar)
            atividade_encontrada = False
            novas_rendimentos = []
            for rend in rendimentos_existentes:
                if rend.get('atividade') == str(atividade_nome):
                    # Atualizar existente
                    novas_rendimentos.append({
                        'atividade': str(atividade_nome),
                        'hh_ha': float(hh_ha),
                        'origem': str(origem) if origem else rend.get('origem', 'sessao'),
                        'chave_tarifa': str(chave_tarifa) if chave_tarifa else rend.get('chave_tarifa', 'vinculada')
                    })
                    atividade_encontrada = True
                else:
                    # Manter outras atividades como estavam
                    novas_rendimentos.append(rend)
            
            # Se não encontrou, adicionar nova
            if not atividade_encontrada:
                novas_rendimentos.append({
                    'atividade': str(atividade_nome),
                    'hh_ha': float(hh_ha),
                    'origem': str(origem) if origem else 'sessao',
                    'chave_tarifa': str(chave_tarifa) if chave_tarifa else 'vinculada'
                })
            
            estado = {"rendimentos_sessao": novas_rendimentos}
        elif not vincular:
            # Se desvincular, remover da lista
            novas_rendimentos = [
                rend for rend in rendimentos_existentes 
                if rend.get('atividade') != str(atividade_nome)
            ]
            estado = {"rendimentos_sessao": novas_rendimentos}
        else:
            # Caso nenhum dos acima, manter estado atual
            estado = {"rendimentos_sessao": rendimentos_existentes}
        
        # Também atualizar o estado geral para manter sincronização
        estado_geral = {}
        if contexto_sessao.fazenda_selecionada:
            estado_geral["operacao"] = {
                "fazenda_atual": str(contexto_sessao.fazenda_selecionada),
                "modo": str(contexto_sessao.modo_atual or ""),
                "equipe_atual": str(contexto_sessao.equipe_selecionada or ""),
                "status_geral": "em_execucao",
            }
            
            msg_parts = []
            if contexto_sessao.fazenda_selecionada:
                msg_parts.append(str(contexto_sessao.fazenda_selecionada))
            if contexto_sessao.equipe_selecionada:
                msg_parts.append(f"Eq:{contexto_sessao.equipe_selecionada}")
            if msg_parts:
                estado_geral["operacao"]["mensagem_curta"] = " | ".join(msg_parts)
        
        if contexto_sessao.talhoes_selecionados is not None:
            estado_geral["lote"] = {
                "talhoes_selecionados": len(contexto_sessao.talhoes_selecionados),
                "talhoes_total": contexto_sessao.total_talhoes_fazenda,
                "area_ha": contexto_sessao.area_total_fazenda,
                "dias_meta": 0,
                "dias_consumidos": 0,
                "saldo_dias": 0,
                "status_meta_continuo": "OK",
                "prazo_absoluto": True,
            }
        
        if contexto_sessao.timestamp_atualizacao:
            estado_geral["timestamp"] = contexto_sessao.timestamp_atualizacao.timestamp()
            estado_geral["timestamp_iso"] = contexto_sessao.timestamp_atualizacao.strftime("%Y-%m-%dT%H:%M:%S")
        
        # Mesclar estado geral com rendimentos
        estado_geral.update(estado)
        _monitor_merge_emit(_MONITOR_STATE_PATH, estado_geral)
    except Exception:
        pass  # Silent fail


def _abrir_monitor_janela(feed="meta", pid=None):
    """
    Abre uma janela separada com o monitor SRF.
    Usa subprocess para iniciar um terminal novo.
    """
    try:
        target_pid = int(pid or os.getpid())
        script_monitor = os.path.join(DIR, "srf_monitor.py")

        if not os.path.isfile(script_monitor):
            aviso(f"Script do monitor nao encontrado: {script_monitor}")
            return False

        # Comando base
        cmd = [
            sys.executable,
            script_monitor,
            "--feed", str(feed),
            "--pid", str(target_pid),
        ]

        if os.name == "nt":
            # Windows: usar start para nova janela
            subprocess.Popen(
                ["start", "cmd", "/k"] + cmd,
                shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
        else:
            # Linux/Mac: tentar terminais comuns (Kitty/Foot primeiro — típico em Hyprland/Sway)
            terminais = [
                ["kitty", "-e"] + cmd,
                ["foot"] + cmd,
                ["wezterm", "start", "--"] + cmd,
                ["alacritty", "-e"] + cmd,
                ["gnome-terminal", "--"] + cmd,
                ["konsole", "--hold", "-e"] + cmd,
                ["xfce4-terminal", "-e"] + cmd,
                ["xterm", "-hold", "-e"] + cmd,
            ]
            for term_cmd in terminais:
                try:
                    subprocess.Popen(
                        term_cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    break
                except FileNotFoundError:
                    continue
            else:
                aviso("Nenhum terminal compativel encontrado para abrir o monitor.")
                return False

        ok(f"Monitor aberto (PID {target_pid}, feed={feed})")
        return True
    except Exception as e:
        aviso(f"Erro ao abrir monitor: {e}")
        return False


def dashboard_header(console_inst=None, mostrar_sempre=True):
    """Wrapper para exibir o dashboard (mantém compatibilidade com chamadas existentes)."""
    global contexto_sessao
    contexto_sessao.exibir(console_inst, mostrar_sempre)


# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
def _default_sequencia_dict():
    return {
        "modo": "implantacao",
        "offset_limpeza_quimica_dias": 30,
        "filtros_plantio": ["plantio"],
        "filtros_irrigacao": ["irrig"],
        "limpeza_quimica_filtros": ["limpeza", "quim"],
        "limpeza_quimica_exclusoes": ["impl", "impl."],
        "implantacao_outras_fase": 5.5,
        "implantacao_fases": [
            {"id": "rocada", "filtros": ["rocada", "roçada"], "exclusoes": []},
            {
                "id": "formiga",
                "filtros": ["formiga", "combate a formiga", "combate a formigas"],
                "exclusoes": [],
            },
            {"id": "coroamento", "filtros": ["coroamento", "coroa"], "exclusoes": []},
            {"id": "coveamento", "filtros": ["coveamento", "coveam"], "exclusoes": []},
            {
                "id": "adubacao_quimica",
                "filtros": ["adubacao quim", "adubação quím", "melhora quim"],
                "exclusoes": [],
            },
        ],
        # Ordem exata solicitada para manutencao SWG (conforme lista de atividades do Excel).
        "swg_fases": [
            {
                "id": "swg_rocada_manual",
                "filtros": ["rocada manual", "roçada manual"],
                "exclusoes": [],
            },
            {
                "id": "swg_limpeza_area",
                "filtros": ["limpeza de area", "limpeza de área"],
                "exclusoes": [],
            },
            {
                "id": "swg_capina_coroa",
                "filtros": ["capina manual coroa", "capina manual"],
                "exclusoes": [],
            },
            {
                "id": "swg_combate_formigas",
                "filtros": ["combate a formigas", "combate a formiga", "formigas"],
                "exclusoes": [],
            },
            {
                "id": "swg_coveamento",
                "filtros": [
                    "coveam area nao subsol",
                    "coveam área não subsol",
                    "coveamento",
                ],
                "exclusoes": [],
            },
            {
                "id": "swg_adubacao_base",
                "filtros": [
                    "adubacao quim man de base",
                    "adubação quim man de base",
                    "adubacao",
                ],
                "exclusoes": [],
            },
            {
                "id": "swg_plantio_manual",
                "filtros": ["plantio manual", "plantio"],
                "exclusoes": [],
            },
            {
                "id": "swg_irrigacao_inicial",
                "filtros": ["irrigacao inicial", "irrigação inicial", "irrigacao"],
                "exclusoes": [],
            },
        ],
    "personalizado_ordem": [],
}


# ──────────────────────────────────────────────
# CONFIGURAÇÃO DE TERRITÓRIOS (V6 NOVO)
# ──────────────────────────────────────────────
def _territorio_config():
    """
    Configuração de territórios/cidades para distribuição automática de equipes.
    Baseado nos requisitos:
    - SWG: 3 equipes com 3 operários úteis cada (1 coordenação não trabalha)
    - Inovesa: 4 equipes com 4 operários úteis cada (1 coordenação não trabalha)
    - Territórios: Açailândia (3), Dom Eliseu (2), Ulianópolis (1), Cidelêndia (1)
    """
    return {
        "cidades": {
            "acailandia": {"nome": "Açailândia", "n_equipes_swg": 3, "n_equipes_inovesa": 4},
            "dom_eliseu": {"nome": "Dom Eliseu", "n_equipes_swg": 2, "n_equipes_inovesa": 3},
            "ulianopolis": {"nome": "Ulianópolis", "n_equipes_swg": 1, "n_equipes_inovesa": 2},
            "cidelandia": {"nome": "Cidelêndia", "n_equipes_swg": 1, "n_equipes_inovesa": 2},
        },
        "empresas": {
            "swg": {
                "nome": "SWG",
                "coordenadores_por_equipe": 1,
                "operarios_por_equipe": 3,  # 3 úteis + 1 coordenação = 4 total
                "equipes_por_cidade": {
                    "acailandia": 3,
                    "dom_eliseu": 2,
                    "ulianopolis": 1,
                    "cidelandia": 1,
                },
            },
            "inovesa": {
                "nome": "Inovesa",
                "coordenadores_por_equipe": 1,
                "operarios_por_equipe": 4,  # 4 úteis + 1 coordenação = 5 total
                "equipes_por_cidade": {
                    "acailandia": 4,
                    "dom_eliseu": 3,
                    "ulianopolis": 2,
                    "cidelandia": 2,
                },
            },
        },
    }


def _detectar_cidade_por_fazenda(nome_fazenda: str) -> str:
    """
    Detecta a cidade/território baseado no nome da fazenda.
    Retorna o código da cidade ou None se não detectar.
    """
    nome_norm = normalizar_chave(str(nome_fazenda))
    cidade_keywords = {
        "acailandia": ["acailandia", "acailand", "ailandia"],
        "dom_eliseu": ["dom eliseu", "eliseu", "dom_eliseu"],
        "ulianopolis": ["ulianopolis", "ulianopol", "ulianópolis"],
        "cidelandia": ["cidelandia", "cideland", "cidelndia", "buritirana"],
    }
    for cidade, keywords in cidade_keywords.items():
        for kw in keywords:
            if kw in nome_norm:
                return cidade
    return None


def _distribuir_fazendas_por_territorio(fazendas: list) -> dict:
    """
    Distribui fazendas por território/cidade automaticamente.
    Retorna: {"acailandia": [fazenda1, fazenda2], "dom_eliseu": [...], ...}
    """
    distribuicao = {"acailandia": [], "dom_eliseu": [], "ulianopolis": [], "cidelandia": []}
    nao_identificadas = []

    for faz in fazendas:
        cidade = _detectar_cidade_por_fazenda(faz)
        if cidade:
            distribuicao[cidade].append(faz)
        else:
            nao_identificadas.append(faz)

    return distribuicao, nao_identificadas


def _calcular_equipes_territorio(cidade: str, empresa: str = "auto") -> dict:
    """
    Calcula configuração de equipes para um território.
    empresa: "swg", "inovesa", ou "auto" (detecta da fazenda)
    """
    cfg_territorio = _territorio_config()
    if cidade not in cfg_territorio["cidades"]:
        return None

    info_cidade = cfg_territorio["cidades"][cidade]

    # Se empresa é auto, assume baseado na cidade (logica customizavel)
    if empresa == "auto":
        empresa = "swg"  # Default SWG (pode ser modificado)

    info_empresa = cfg_territorio["empresas"][empresa]
    n_equipes = info_empresa["equipes_por_cidade"].get(cidade, 1)
    operarios_por_eq = info_empresa["operarios_por_equipe"]
    coordenadores = info_empresa["coordenadores_por_equipe"]
    total_por_eq = operarios_por_eq + coordenadores

    return {
        "cidade": cidade,
        "nome_cidade": info_cidade["nome"],
        "empresa": empresa,
        "nome_empresa": info_empresa["nome"],
        "n_equipes": n_equipes,
        "operarios_por_equipe": operarios_por_eq,
        "coordenadores_por_equipe": coordenadores,
        "total_por_equipe": total_por_eq,
        "total_operarios": n_equipes * operarios_por_eq,
        "total_coordenadores": n_equipes * coordenadores,
        "total_geral": n_equipes * total_por_eq,
    }


def _sugerir_config_territorio(fazendas: list, modo_simplificado: bool = True) -> dict:
    """
    Sugere configuração completa de equipes baseada na distribuição de fazendas.
    modo_simplificado: True = mostra apenas resumo, False = detalhado
    """
    distribuicao, nao_id = _distribuir_fazendas_por_territorio(fazendas)
    sugestoes = []

    for cidade, fazs in distribuicao.items():
        if not fazs:
            continue
        config = _calcular_equipes_territorio(cidade)
        if config:
            config["fazendas"] = fazs
            config["n_fazendas"] = len(fazs)
            sugestoes.append(config)

    return {
        "distribuicao": distribuicao,
        "nao_identificadas": nao_id,
        "sugestoes": sugestoes,
        "total_equipes": sum(s["n_equipes"] for s in sugestoes),
        "total_operarios": sum(s["total_operarios"] for s in sugestoes),
    }


def _aplicar_sobrecarga_swg(fazendas_swg: list, fazendas_disponiveis: list) -> dict:
    """
    Se SWG terminar áreas antes do prazo, pode assumir áreas extras.
    Retorna distribuição ajustada.
    """
    # Por enquanto, apenas estrutura - lógica de sobrecarga depende de simulação
    return {
        "fazendas_originais": fazendas_swg,
        "fazendas_extras": [],
        "areas_prioritarias": [],
        "nota": "Função de sobrecarga SWG - implementar lógica de simulação de conclusão antecipada",
    }


def _merge_sequencia_defaults(seq):
    """Preenche chaves ausentes em cfg['sequencia'] (muta seq)."""
    d0 = _default_sequencia_dict()
    for k, v in d0.items():
        if k not in seq:
            seq[k] = v
        elif (
            k in ("implantacao_fases", "swg_fases", "personalizado_ordem")
            and not seq[k]
        ):
            seq[k] = v


def carregar_config():
    if not os.path.exists(CFGP):
        with open(CFGP, "w", encoding="utf-8") as f:
            json.dump({"de_para": {}, "tarifas": {}, "atividades": {}}, f)
    with open(CFGP, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    for k in ("de_para", "tarifas", "atividades"):
        if k not in cfg:
            cfg[k] = {}
    if "orcamento_estrito" not in cfg:
        cfg["orcamento_estrito"] = True
    if "filtros_bloqueio_global" not in cfg:
        cfg["filtros_bloqueio_global"] = ["plantio", "irrig"]
    if "fazendas_ct" not in cfg:
        cfg["fazendas_ct"] = []
    if "metas" not in cfg:
        cfg["metas"] = {
            "lucro_alvo": None,
            "margem_alvo_pct": None,
            "bonus_aa_formula": "",
            "bonus_bb_formula": "",
            "equacao_quadratica": "",
            "nota": "Rotas preparatorias: preencher quando dados oficiais estiverem disponiveis.",
        }
    if "precos_contrato" not in cfg:
        cfg["precos_contrato"] = {
            "arquivo": "",
            "sheet_preco_final": "",
            "sheet_custo_direto": "",
            "sheet_custo_indireto": "",
        }
    if "custos_globais" not in cfg:
        cfg["custos_globais"] = {
            "arquivo": "",
            "sheet_custo_direto": "",
            "sheet_custo_indireto": "",
            "valor_direto_total": 0.0,
            "valor_indireto_total": 0.0,
            "criterio": "ultimo_valor_na_linha",
            "itens_direto": [],
            "itens_indireto": [],
        }
    if "sequencia" not in cfg or not isinstance(cfg.get("sequencia"), dict):
        cfg["sequencia"] = {}
    _merge_sequencia_defaults(cfg["sequencia"])
    return cfg


def salvar_config(cfg):
    with open(CFGP, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def parse_intervalos_escolha(texto, max_n):
    """
    Converte '1,3,5-8' em indices 0-based unicos e ordenados (numeracao 1..max_n).
    Espacos ignorados; intervalos inclusive.
    """
    out = set()
    if not texto or not str(texto).strip() or max_n < 1:
        return []
    for part in str(texto).replace(" ", "").split(","):
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            try:
                lo, hi = int(a), int(b)
                if lo > hi:
                    lo, hi = hi, lo
                for k in range(lo, hi + 1):
                    if 1 <= k <= max_n:
                        out.add(k - 1)
            except ValueError:
                continue
        else:
            try:
                k = int(part)
                if 1 <= k <= max_n:
                    out.add(k - 1)
            except ValueError:
                continue
    return sorted(out)


def mediana_rendimento_hh(tarifas):
    """Mediana dos rendimento_hh > 0 em config.tarifas, ou None."""
    vals = []
    for v in (tarifas or {}).values():
        if not isinstance(v, dict):
            continue
        try:
            x = float(v.get("rendimento_hh", 0))
            if x > 0:
                vals.append(x)
        except (TypeError, ValueError):
            pass
    if not vals:
        return None
    vals.sort()
    n = len(vals)
    mid = n // 2
    if n % 2:
        return vals[mid]
    return (vals[mid - 1] + vals[mid]) / 2.0


def resolver_rendimento_hh(
    cfg, tarifas, t_nome, strict=False, session_hh=None, atv_micro=None
):
    """
    HH/ha para a chave t_nome em tarifas.
    session_hh: dict opcional {nome_micro ou chave_tarifa: hh_ha} valido so na execucao atual (nao grava config).
    Modo strict: sem mediana/8 silenciosos — retorna None se invalido.
    Excecao: atividades mecanizadas (tipo Mecanizada ou HM>0) retornam 0.0 em strict.
    """
    if session_hh:
        try:
            if atv_micro and atv_micro in session_hh:
                return float(session_hh[atv_micro])
            if t_nome and t_nome in session_hh:
                return float(session_hh[t_nome])
        except (TypeError, ValueError):
            pass
    if t_nome in (tarifas or {}):
        row = tarifas[t_nome]
        r = row.get("rendimento_hh")
        try:
            rf = float(r)
            if rf >= 0:
                if strict and rf <= 0:
                    tipo = str(row.get("tipo", "")).lower()
                    hm = float(row.get("rendimento_hm", 0) or 0)
                    if "mecaniz" in tipo or hm > 0:
                        return 0.0
                    return None
                return rf
        except (TypeError, ValueError):
            if strict:
                return None
    if strict:
        return None
    ex = cfg.get("rendimento_hh_fallback")
    if ex is not None:
        try:
            e = float(ex)
            if e > 0:
                return e
        except (TypeError, ValueError):
            pass
    med = mediana_rendimento_hh(tarifas)
    if med is not None and med > 0:
        return med
    return 8.0


# ──────────────────────────────────────────────
#  CT_313 RAW -> STG NORMALIZER
# ──────────────────────────────────────────────
STG_FILENAME = "CT_313_NORMALIZADA.xlsx"

# Padrao de prototipo: mapeamento fixo EXAME -> CT_313 (normalizado sem acentos).
# Fonte: leitura real das abas MICROPLANEJAMENTO_ABRIL_JUNHO e STG_TARIFAS.
#
# Declividade (ROÇADA MANUAL CLASSE I..V na CT): classe I = terreno mais plano (menor HH/ha e
# menor preco/ha); classe V = declive maximo (maior HH e maior preco — mais custo MO mas mais
# receita). O micro nao traz a classe — o padrao SRF usa sempre CLASSE I / limpeza plana onde
# aplicavel (cenario conservador em margem: sem premio de obra em morro). Ver aviso no scheduler.
DEFAULT_DEPARA_EXAME_CT313 = {
    # ADUBAÇÃO
    "adubacao quim man de base impl pl app rl": "ADUBAÇÃO QUÍMICA MANUAL",
    # CAPINA
    "capina manual coroa impl cd app rl i": "CAPINA COROAMENTO MANUAL I",
    "capina manual coroa impl pl app rl i": "CAPINA COROAMENTO MANUAL I",
    "capina quim man total manut app rl": "CAPINA QUÍMICA TOTAL MANUAL PLANO",
    # COMBATE
    "combate a formigas impl cd app rl": "COMBATE DE FORMIGAS MANUAL",
    "combate a formigas impl pl app rl": "COMBATE DE FORMIGAS MANUAL",
    "combate a formigas manut app rl": "CONTROLE DE FORMIGAS MANUAL  (REPASSE)",
    # CONTROLE — com e sem sufixo I
    "controle de invasoras app rl i": "CAPINA QUÍMICA TOTAL MANUAL PLANO",
    "controle de invasoras app rl": "CAPINA QUÍMICA TOTAL MANUAL PLANO",
    # COVEAMENTO — motocoveador, subsol, NÃO subsol
    "coveamento motocoveador pl app rl": "COVEAMENTO SEMI MECANIZADO - 30CM",
    "coveamento area subsol impl pl app rl": "SUBSOLAGEM COM ADUBAÇÃO (TRATOR PNEU)",
    "coveam area nao subsol impl pl app rl": "COVEAMENTO SEMI MECANIZADO - 30CM",
    # IRRIGAÇÃO
    "irrigacao inicial man impl pl app rl": "IRRIGAÇÃO DE PLANTIO MANUAL",
    # LIMPEZA — QUIM. / QU.
    "limpeza de area quim impl cd app rl": "ROÇADA SEMIMECANIZADA ÁREA TOTAL",
    "limpeza de area quim man app rl": "ROÇADA MANUAL CLASSE I",
    "limpeza de area qu man app rl": "ROÇADA MANUAL CLASSE I",
    # PLANTIO
    "plantio manual app rl": "PLANTIO MANUAL SEM GEL",
    # PREPARO DE SOLO
    "preparo de solo mec c grade app rl": "PREPARO DE SOLO COM ADUBAÇÃO DE BASE E MARCAÇÃO DE BACIA ECAVADEIRA",
    "preparo de solo mec s adub app rl": "PREPARO DE SOLO COM MÁQUINA DE ESTEIRA",
    # ROÇADA
    "rocada manual impl cd app rl i": "ROÇADA MANUAL CLASSE I",
    "rocada manual impl pl app rl i": "ROÇADA MANUAL CLASSE I",
    # Atividades sem par explicito nas tarifas operacionais: usa baseline de MO da CT.
    "conducao de regeneracao": "SERVIÇO DE MÃO DE OBRA",
    "eliminacao de exoticas impl cd app rl": "SERVIÇO DE MÃO DE OBRA",
    "nucleacao em faixas app rl": "SERVIÇO DE MÃO DE OBRA",
}


def _depara_heuristico_exame_ct313(kn, tarifas):
    """
    Fallback quando o micro usa outras convencoes de texto (APPN RL/NR, manl., microtrator,
    MELHORA QUIM..., ESTIVA..., parenteses etc.). So aplica se a tarifa alvo existir no CT.
    """
    if not kn or not tarifas:
        return None

    def pick(*names):
        for n in names:
            if n in tarifas:
                return n
        return None

    # Ordem: mais especifico / excecao primeiro
    if "estiva" in kn:
        return pick("SERVIÇO DE MÃO DE OBRA")
    if "subsol" in kn or "area subsol" in kn:
        return pick("SUBSOLAGEM COM ADUBAÇÃO (TRATOR PNEU)")
    if "coveamento" in kn:
        return pick(
            "COVEAMENTO SEMI MECANIZADO - 30CM",
            "COVEAMENTO SEMI MECANIZADO - 40CM",
        )
    if "combate" in kn and "formiga" in kn:
        return pick(
            "COMBATE DE FORMIGAS MANUAL",
            "CONTROLE DE FORMIGAS MANUAL  (REPASSE)",
        )
    # "Melhoria / Mineral" no micro as vezes vem como MELHORA QUIM ... DE BASE
    if ("melhora" in kn or "melhoria" in kn) and ("quim" in kn or "quimica" in kn):
        return pick("ADUBAÇÃO QUÍMICA MANUAL")
    if "adubacao" in kn and ("quim" in kn or "quimica" in kn):
        return pick("ADUBAÇÃO QUÍMICA MANUAL")
    if "limpeza" in kn and "area" in kn:
        if "quim" in kn or "quimica" in kn:
            return pick(
                "ROÇADA SEMIMECANIZADA ÁREA TOTAL",
                "ROÇADA MANUAL CLASSE I",
            )
        return pick("ROÇADA MANUAL CLASSE I")
    if "irrigacao" in kn:
        return pick(
            "IRRIGAÇÃO DE PLANTIO MANUAL",
            "IRRIGAÇÃO DE PLANTIO SEMIMEC",
        )
    if "plantio" in kn and "manual" in kn:
        return pick("PLANTIO MANUAL SEM GEL", "PLANTIO MANUAL COM GEL")
    if "preparo" in kn and "solo" in kn:
        if "rocadeira" in kn or "esteira" in kn or "s adub" in kn or "s adubacao" in kn:
            return pick("PREPARO DE SOLO COM MÁQUINA DE ESTEIRA")
        if "grade" in kn or ("adub" in kn and "s adub" not in kn):
            return pick(
                "PREPARO DE SOLO COM ADUBAÇÃO DE BASE E MARCAÇÃO DE BACIA ECAVADEIRA",
            )
        return pick(
            "PREPARO DE SOLO COM MÁQUINA DE ESTEIRA",
            "PREPARO DE SOLO COM ADUBAÇÃO DE BASE E MARCAÇÃO DE BACIA ECAVADEIRA",
        )
    if "nucleacao" in kn:
        return pick("SERVIÇO DE MÃO DE OBRA")
    if "conducao" in kn:
        return pick("SERVIÇO DE MÃO DE OBRA")
    if "eliminacao" in kn and "exotica" in kn:
        return pick("SERVIÇO DE MÃO DE OBRA")
    if "controle" in kn and "invasora" in kn:
        return pick("CAPINA QUÍMICA TOTAL MANUAL PLANO")
    if "rocada" in kn and "manual" in kn:
        return pick("ROÇADA MANUAL CLASSE I")
    if "capina" in kn:
        if "quim" in kn or "quimica" in kn:
            return pick(
                "CAPINA QUÍMICA TOTAL MANUAL PLANO",
                "CAPINA QUÍMICA TOTAL MANUAL DECLIVIDADE",
            )
        return pick("CAPINA COROAMENTO MANUAL I")
    return None


def _ct_file_hash(path):
    h = hashlib.md5()
    h.update(str(os.path.getmtime(path)).encode())
    h.update(str(os.path.getsize(path)).encode())
    return h.hexdigest()


def _find_preco_final_sheet(xls):
    for s in xls.sheet_names:
        if remover_acentos(s).replace(" ", "") in ("precofinal", "preco final"):
            return s
    return None


def _find_diaria_tf_sheet(xls):
    for s in xls.sheet_names:
        if "diaria_tf" in remover_acentos(s).replace(" ", ""):
            return s
    return None


def normalizar_ct313(caminho_ct):
    """
    Le CT_313 bruta e gera CT_313_NORMALIZADA.xlsx com aba STG_TARIFAS.
    Retorna (caminho_stg, n_linhas, custo_hora_tf).
    """
    xls = pd.ExcelFile(caminho_ct)
    pf = _find_preco_final_sheet(xls)
    if not pf:
        return None, 0, 0.0

    df = pd.read_excel(caminho_ct, sheet_name=pf, header=None)

    custo_hora_tf = 0.0
    tf = _find_diaria_tf_sheet(xls)
    if tf:
        dft = pd.read_excel(caminho_ct, sheet_name=tf, header=None)
        try:
            custo_dia = float(dft.iloc[3][4])
            jornada_tf = float(dft.iloc[4][2])
            if jornada_tf > 0:
                custo_hora_tf = custo_dia / jornada_tf
        except (IndexError, TypeError, ValueError):
            pass

    rows = []
    for i in range(5, len(df)):
        r = df.iloc[i]
        nome = str(r[2]).strip() if pd.notna(r[2]) else ""
        if not nome or nome == "0":
            continue
        tipo = str(r[4]).strip() if pd.notna(r[4]) else ""
        try:
            hh = float(r[5]) if pd.notna(r[5]) else 0.0
        except (TypeError, ValueError):
            hh = 0.0
        try:
            hm = float(r[6]) if pd.notna(r[6]) else 0.0
        except (TypeError, ValueError):
            hm = 0.0
        try:
            preco = float(r[7]) if pd.notna(r[7]) else 0.0
        except (TypeError, ValueError):
            preco = 0.0
        custo_h = custo_hora_tf if hh > 0 and custo_hora_tf > 0 else 0.0
        custo_ha = hh * custo_h if custo_h > 0 else 0.0
        rows.append(
            {
                "atividade": nome,
                "tipo": tipo,
                "rendimento_hh": hh,
                "rendimento_hm": hm,
                "preco_ha": preco,
                "custo_hora": custo_h,
                "custo_ha": custo_ha,
                "fonte_aba": pf,
            }
        )

    df_stg = pd.DataFrame(rows)
    meta = pd.DataFrame(
        [
            {
                "gerado_em": datetime.datetime.now().isoformat(),
                "arquivo_origem": os.path.basename(caminho_ct),
                "linhas_validas": len(rows),
                "custo_hora_tf": round(custo_hora_tf, 4),
            }
        ]
    )

    stg_path = os.path.join(DIR, STG_FILENAME)
    with pd.ExcelWriter(stg_path, engine="openpyxl") as w:
        df_stg.to_excel(w, sheet_name="STG_TARIFAS", index=False)
        meta.to_excel(w, sheet_name="STG_METADATA", index=False)

    return stg_path, len(rows), custo_hora_tf


def carregar_stg_tarifas(stg_path):
    """Le STG_TARIFAS e retorna dict {atividade: {rendimento_hh, preco_ha, custo_hora, custo_ha, tipo}}."""
    df = pd.read_excel(stg_path, sheet_name="STG_TARIFAS")
    t = {}
    for _, r in df.iterrows():
        nome = str(r.get("atividade", "")).strip()
        if not nome:
            continue
        hh = float(r.get("rendimento_hh") or 0)
        hm = float(r.get("rendimento_hm") or 0)
        t[nome] = {
            "rendimento_hh": hh,
            "rendimento_hm": hm,
            "preco_ha": float(r.get("preco_ha") or 0),
            "custo_hora": float(r.get("custo_hora") or 0),
            "custo_ha": float(r.get("custo_ha") or 0),
            "tipo": str(r.get("tipo") or ""),
            "preco_unit": float(r.get("preco_ha") or 0),
            "recurso": "homem" if hh > 0 else "maquina",
            "eficiencia": 1.0,
        }
    return t


def modulo_normalizar_ct(cfg):
    """Menu: selecionar CT bruta, gerar STG, integrar em config.tarifas."""
    dashboard_header()
    subcabecalho("NORMALIZAR CT_313 -> STG_TARIFAS")
    caminho = selecionar_arquivo("CT_313 BRUTA (.xlsm ou .xlsx)")
    if not caminho:
        return

    print(DM + "  Processando... pode demorar alguns segundos." + RS)
    stg_path, n, custo_h = normalizar_ct313(caminho)
    if not stg_path:
        erro("Aba 'Preco Final' nao encontrada neste arquivo.")
        input(DM + "\n  [ENTER] " + RS)
        return

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
    input(DM + "\n  [ENTER para voltar] " + RS)


def _guess_sheet(xls, keys):
    for s in xls.sheet_names:
        ns = normalizar_chave(s)
        if all(k in ns for k in keys):
            return s
    return None


def _pick_col(df, required_tokens_sets):
    cols = list(df.columns)
    for c in cols:
        nc = normalizar_chave(c)
        for toks in required_tokens_sets:
            if all(t in nc for t in toks):
                return c
    return None


def _to_float_any(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return None
    s = s.replace("R$", "").replace(" ", "")
    if "," in s and "." in s:
        # Ex.: 1.234,56 -> 1234.56
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


def _last_non_zero(nums):
    for n in reversed(nums):
        if n is not None and abs(float(n)) > 1e-9:
            return float(n)
    for n in reversed(nums):
        if n is not None:
            return float(n)
    return 0.0


def _is_raw_cost_row_label(lbl):
    n = normalizar_chave(lbl)
    if not n:
        return False
    bad = {
        "indireto",
        "custo indireto pessoal",
        "custo indireto",
        "custo direto",
        "bdi",
        "soma",
    }
    if n in bad:
        return False
    if n in {"d", "premio"}:
        return False
    if n.startswith("previsao "):
        return False
    if n.startswith("resultado "):
        return False
    if n.startswith("desconto "):
        return False
    return True


def _extrair_custos_globais_brutos(caminho, sheet_cd, sheet_ci):
    """
    Extrai custos globais de planilha bruta (layout "torto"):
    - pega coluna A como item
    - consolida cada linha pelo ultimo valor nao nulo/nao-zero das colunas laterais
    - total direto/indireto prioriza linha 'CUSTO DIRETO'/'CUSTO INDIRETO'
      e, se ausente, usa soma dos itens consolidados.
    """

    def parse_sheet(sheet_name):
        df = pd.read_excel(caminho, sheet_name=sheet_name, header=None)
        itens = []
        total_linha = None
        for _, r in df.iterrows():
            label = str(r.iloc[0] if len(r) > 0 else "").strip()
            if not label:
                continue
            nums = []
            for v in list(r.iloc[1:]):
                fv = _to_float_any(v)
                if fv is not None:
                    nums.append(fv)
            nlabel = normalizar_chave(label)
            if nlabel in {"custo direto", "custo indireto"}:
                total_linha = _last_non_zero(nums)
                continue
            if _is_raw_cost_row_label(label):
                val = _last_non_zero(nums)
                if abs(val) > 1e-9:
                    itens.append({"item": label, "valor": round(float(val), 6)})
        total = (
            float(total_linha)
            if total_linha is not None
            else float(sum(x["valor"] for x in itens))
        )
        return total, itens

    total_cd, itens_cd = parse_sheet(sheet_cd)
    total_ci, itens_ci = parse_sheet(sheet_ci)
    return {
        "valor_direto_total": round(float(total_cd), 6),
        "valor_indireto_total": round(float(total_ci), 6),
        "itens_direto": itens_cd,
        "itens_indireto": itens_ci,
    }


def modulo_importar_custos_globais_brutos(cfg):
    """
    Rota secundaria:
    importa CUSTO_DIRETO/CUSTO_INDIRETO em formato bruto (coluna A + valores laterais),
    sem rateio por atividade, para uso no fechamento financeiro global.
    """
    dashboard_header()
    subcabecalho("IMPORTAR CUSTOS GLOBAIS (BRUTO)")
    caminho = selecionar_arquivo(
        "PLANILHA BRUTA DE CUSTOS (CUSTO_DIRETO/CUSTO_INDIRETO)"
    )
    if not caminho:
        return
    try:
        xls = pd.ExcelFile(caminho)
        cd = _guess_sheet(xls, ["custo", "direto"])
        ci = _guess_sheet(xls, ["custo", "indireto"])
        sub()
        print(G + "  CUSTO_DIRETO   : " + C + f"{cd or '??'}" + RS)
        print(G + "  CUSTO_INDIRETO : " + C + f"{ci or '??'}" + RS)
        if not (cd and ci) or not confirmar(
            "Usar mapeamento automatico de abas?", default=True
        ):
            cd = selecionar("ABA CUSTO_DIRETO", xls.sheet_names)
            if cd is None:
                return
            ci = selecionar("ABA CUSTO_INDIRETO", xls.sheet_names)
            if ci is None:
                return

        ext = _extrair_custos_globais_brutos(caminho, cd, ci)
        cfg["custos_globais"] = {
            "arquivo": os.path.basename(caminho),
            "sheet_custo_direto": cd,
            "sheet_custo_indireto": ci,
            "valor_direto_total": ext["valor_direto_total"],
            "valor_indireto_total": ext["valor_indireto_total"],
            "criterio": "ultimo_valor_na_linha",
            "itens_direto": ext["itens_direto"],
            "itens_indireto": ext["itens_indireto"],
        }
        salvar_config(cfg)
ok(
    f"{len(df)} registros | "
    f"{df['fazenda'].nunique()} fazendas | {df['chave'].nunique()} talhoes | "
    f"{len(dp)} de_para mapeados ({novos} novos)"
)

# SRF v7: Auto-spawn monitors se SRF_MONITOR_AUTO=1 (padrão)
if os.environ.get("SRF_MONITOR_AUTO", "1") == "1":
    print(G + "\nSRF v7 está inicializando monitores auxiliares..." + RS)
    print(DM + "5 janelas serão abertas: Contexto | HH/h | Auditoria | Custos | Território" + RS)
    print(DM + "Para desativar: SRF_MONITOR_AUTO=0" + RS)
    
    if confirmar("Abrir janelas auxiliares de monitor?", default=True):
        monitors_abertos = _iniciar_monitores_companhia(pid=os.getpid(), auto_spawn=True)
        if monitors_abertos:
            ok(f"✓ {len(monitors_abertos)} monitores inicializados")
            time.sleep(1.5)  # Pausa para janelas carregarem
            input(DM + "\n [ENTER para continuar com o principal] " + RS)

input(DM + " [ENTER para continuar] " + RS)

    equipes_config = []
    fazendas_restantes = list(fazendas)

    for ie in range(1, n_equipes + 1):
        sub()
        print(G + BL + f" EQUIPE {ie}/{n_equipes}" + RS)

        # ──────────────────────────────────────────────
        # CONFIGURAÇÃO AUTOMÁTICA POR TERRITÓRIO (V6 NOVO)
        # ──────────────────────────────────────────────
        if usar_modo_territorio and config_territorio:
            # Encontrar a configuração de território para esta equipe
            cfg_territorio_eq = None
            equipe_idx_atual = ie - 1
            acum_equipes = 0

            for sug in config_territorio["sugestoes"]:
                n_eq_cidade = sug["n_equipes"]
                if equipe_idx_atual < acum_equipes + n_eq_cidade:
                    # Esta equipe pertence a esta cidade
                    cidade_eq = sug["cidade"]
                    n_cidade = equipe_idx_atual - acum_equipes + 1
                    nome_eq = f"{sug['nome_empresa']} {sug['nome_cidade']} Eq{n_cidade}"
                    j_eq = 4.3
                    exec_eq = sug["operarios_por_equipe"]
                    turmas_eq = [
                        {
                            "nome": f"{sug['nome_empresa']} {sug['nome_cidade']}",
                            "operarios": exec_eq,
                            "atividades": [],
                        }
                    ]
                    # Distribuir fazendas desta cidade entre as equipes dela
                    fazs_cidade = sug["fazendas"]
                    n_por_eq = max(1, len(fazs_cidade) // n_eq_cidade)
                    inicio_idx = n_cidade - 1
                    faz_eq = fazs_cidade[inicio_idx : inicio_idx + n_por_eq]

                    ok(f"Configuracao automatica: {nome_eq}")
                    print(G + f"  Cidade: {sug['nome_cidade']}" + RS)
                    print(G + f"  Empresa: {sug['nome_empresa']}" + RS)
                    print(G + f"  Operarios: {exec_eq}" + RS)
                    print(G + f"  Fazendas: {len(faz_eq)}" + RS)
                    cfg_territorio_eq = {
                        "nome": nome_eq,
                        "jornada": j_eq,
                        "executores": exec_eq,
                        "turmas": turmas_eq,
                        "fazendas": faz_eq,
                    }
                    break
                acum_equipes += n_eq_cidade

            if cfg_territorio_eq:
                nome_eq = cfg_territorio_eq["nome"]
                j_eq = cfg_territorio_eq["jornada"]
                exec_eq = cfg_territorio_eq["executores"]
                turmas_eq = cfg_territorio_eq["turmas"]
                faz_eq = cfg_territorio_eq["fazendas"]
                prazo_eq = pedir_float(f"Prazo meta para '{nome_eq}' (meses)", 3.0)

                data_fim_txt = None
                if confirmar(
                    f"Informar dia final manualmente para '{nome_eq}'?", default=False
                ):
                    mes_fim = pedir_int("Mes final (1-12)", mes_ref)
                    mes_fim = max(1, min(12, int(mes_fim)))
                    ano_fim = pedir_int("Ano final", ano_ref)
                    dia_max_fim = calendar.monthrange(ano_fim, mes_fim)[1]
                    dia_fim = pedir_int(
                        f"Dia final (1-{dia_max_fim})", min(dia_ref, dia_max_fim)
                    )
                    dia_fim = max(1, min(dia_max_fim, int(dia_fim)))
                    data_fim_txt = _formatar_data_dia(dia_fim, mes_fim, ano_fim)
                else:
                    fim_calc = _calcular_data_fim_por_meses(
                        dia_ref, mes_ref, ano_ref, prazo_eq
                    )
                    if fim_calc:
                        data_fim_txt = _formatar_data_dia(
                            fim_calc[0], fim_calc[1], fim_calc[2]
                        )
        else:
            # ──────────────────────────────────────────────
            # CONFIGURAÇÃO MANUAL (modo tradicional)
            # ──────────────────────────────────────────────
            nome_eq = prompt(f"Nome da equipe {ie}", f"Equipe {ie}")
            prazo_eq = pedir_float(f"Prazo meta para '{nome_eq}' (meses)", 3.0)
            j_eq = pedir_float(f"Jornada diaria '{nome_eq}' (horas)", 4.3)
            exec_eq = pedir_int(f"Executores '{nome_eq}'", 10)

            data_fim_txt = None
            if confirmar(
                f"Informar dia final manualmente para '{nome_eq}'?", default=False
            ):
                mes_fim = pedir_int("Mes final (1-12)", mes_ref)
                mes_fim = max(1, min(12, int(mes_fim)))
                ano_fim = pedir_int("Ano final", ano_ref)
                dia_max_fim = calendar.monthrange(ano_fim, mes_fim)[1]
                dia_fim = pedir_int(
                    f"Dia final (1-{dia_max_fim})", min(dia_ref, dia_max_fim)
                )
                dia_fim = max(1, min(dia_max_fim, int(dia_fim)))
                data_fim_txt = _formatar_data_dia(dia_fim, mes_fim, ano_fim)
            else:
                fim_calc = _calcular_data_fim_por_meses(dia_ref, mes_ref, ano_ref, prazo_eq)
                if fim_calc:
                    data_fim_txt = _formatar_data_dia(fim_calc[0], fim_calc[1], fim_calc[2])

            perfil_carregado = None
            perfis = _listar_perfis_equipe()
            if perfis and confirmar(
                f"Carregar perfil de equipe para '{nome_eq}'?", default=False
            ):
                perfil_carregado = _carregar_perfil_equipe_menu()

            if perfil_carregado:
                turmas_eq = [
                    {
                        "nome": t["nome"],
                        "operarios": t["operarios"],
                        "atividades": list(t.get("atividades") or []),
                    }
                    for t in perfil_carregado.get("turmas", [])
                ]
                exec_eq = sum(t["operarios"] for t in turmas_eq)
                ok(
                    f"Perfil carregado: {len(turmas_eq)} turma(s), {exec_eq} executores."
                )
            else:
                turmas_eq = [{"nome": nome_eq, "operarios": exec_eq, "atividades": []}]
                menu_vincular_atividades_turma(turmas_eq[0], todas_atvs)

        if not fazendas_restantes:
            aviso("Todas as fazendas ja foram atribuidas. Esta equipe ficara vazia.")
            faz_eq = []
        elif ie == n_equipes:
            faz_eq = list(fazendas_restantes)
            ok(f"Restantes ({len(faz_eq)}) atribuidas a '{nome_eq}'.")
        else:
            print(G + f"\n  Fazendas disponiveis ({len(fazendas_restantes)}):" + RS)
            for idx_f, f in enumerate(fazendas_restantes, 1):
                print(G + f"  {idx_f:3}. " + C + f + RS)
            sel_txt = prompt(
                f"Indices das fazendas para '{nome_eq}' (ex: 1,3,5-7) ou ENTER=todas restantes",
                "",
            )
            if not sel_txt.strip():
                faz_eq = list(fazendas_restantes)
            else:
                idxs = parse_intervalos_escolha(sel_txt, len(fazendas_restantes))
                faz_eq = [fazendas_restantes[i] for i in idxs]
            for f in faz_eq:
                if f in fazendas_restantes:
                    fazendas_restantes.remove(f)
            ok(f"{len(faz_eq)} fazenda(s) para '{nome_eq}'.")

        equipes_config.append(
            {
                "nome": nome_eq,
                "prazo_meses": prazo_eq,
                "jornada": j_eq,
                "executores": exec_eq,
                "turmas": turmas_eq,
                "fazendas": faz_eq,
                "modo_seq": modo_seq,
                "mes_ref": mes_ref,
                "ano_ref": ano_ref,
                "data_inicio_txt": data_inicio_txt,
                "data_fim_txt": data_fim_txt,
            }
        )

    all_eq_results = []
    for ec in equipes_config:
        linha()
        print(
            G
            + BL
            + f"  PROCESSANDO EQUIPE: {ec['nome']} ({len(ec['fazendas'])} fazendas)"
            + RS
        )
        linha()

        dias_meta_eq = dias_uteis_no_periodo(
            ec["mes_ref"], ec["ano_ref"], ec["prazo_meses"]
        )
        cap_eq_dia = float(ec["executores"]) * float(ec["jornada"])
        eq_resultados = []
        dias_acum_eq = 0

        ctx_eq = {
            "modo_seq": ec["modo_seq"],
            "usar_bloqueio_global": False,
            "usar_reforco_automatico": True,
            "usar_pool_pos_bloqueio": False,
            "prazo_meses": ec["prazo_meses"],
            "mes_ref": ec["mes_ref"],
            "ano_ref": ec["ano_ref"],
            "data_inicio_txt": ec.get("data_inicio_txt"),
            "data_fim_txt": ec.get("data_fim_txt"),
            "jornada": ec["jornada"],
            "executores": ec["executores"],
            "turmas": ec["turmas"],
            "penalidade": 1.0,
            "preencher_orfas_template": True,
        }
        contexto_sessao.atualizar_modo("multi_equipes")
        contexto_sessao.atualizar_equipe(ec["nome"])
        contexto_sessao.definir_datas(ec.get("data_inicio_txt"), ec.get("data_fim_txt"))
        _emitir_monitor_atual()
        _emit_monitor_state(
            {
                "operacao": {
                    "modo": "multi_equipes",
                    "equipe_atual": str(ec["nome"]),
                    "status_geral": "processando_equipe",
                    "mensagem_curta": f"Equipe {ec['nome']} ({len(ec['fazendas'])} fazendas)",
                },
                "lote": {
                    "dias_meta": int(dias_meta_eq),
                    "dias_consumidos": int(dias_acum_eq),
                    "saldo_dias": int(max(0, int(dias_meta_eq) - int(dias_acum_eq))),
                    "fazenda_indice": 0,
                    "n_fazendas": int(len(ec["fazendas"])),
                    "status_meta_continuo": "OK",
                    "prazo_absoluto": True,
                },
            }
        )

        for fz in ec["fazendas"]:
            r = calcular_cronograma_inteligente(
                cfg,
                df_scope[df_scope["fazenda"] == fz].copy(),
                fz,
                esperar_enter=False,
                ctx=dict(ctx_eq),
            )
            if r:
                dias_faz = int(r.get("dias_simulado", 0))
                r["dia_inicio_acumulado"] = dias_acum_eq + 1
                dias_acum_eq += dias_faz
                r["dia_fim_acumulado"] = dias_acum_eq
                r["saldo_meta_apos"] = max(0, dias_meta_eq - dias_acum_eq)
                r["pct_meta_consumida"] = round(
                    (dias_acum_eq / dias_meta_eq * 100) if dias_meta_eq > 0 else 0.0, 1
                )
                r["status_meta_continuo"] = (
                    "EXCEDIDO"
                    if dias_acum_eq > dias_meta_eq
                    else ("RISCO" if dias_acum_eq >= dias_meta_eq * 0.8 else "OK")
                )
                eq_resultados.append(r)

        all_eq_results.append(
            {
                "equipe": ec["nome"],
                "executores": ec["executores"],
                "jornada": ec["jornada"],
                "prazo_meses": ec["prazo_meses"],
                "data_inicio_txt": ec.get("data_inicio_txt"),
                "data_fim_txt": ec.get("data_fim_txt"),
                "dias_meta": dias_meta_eq,
                "dias_acumulados": dias_acum_eq,
                "hh_total": sum(float(x.get("total_hh", 0)) for x in eq_resultados),
                "receita": sum(float(x.get("receita_total", 0)) for x in eq_resultados),
                "custo_mo": sum(
                    float(x.get("custo_mo_total", 0)) for x in eq_resultados
                ),
                "n_fazendas": len(ec["fazendas"]),
                "status": "DENTRO" if dias_acum_eq <= dias_meta_eq else "EXCEDIDO",
                "resultados_fazendas": eq_resultados,
            }
        )

    linha()
    print(G + BL + "  CONSOLIDADO MULTI-EQUIPES" + RS)
    t_meq = Table(title="Comparativo entre equipes")
    t_meq.add_column("Equipe", style="cyan")
    t_meq.add_column("Exec.", justify="right")
    t_meq.add_column("Fazendas", justify="right")
    t_meq.add_column("HH", justify="right")
    t_meq.add_column("Dias acum.", justify="right")
    t_meq.add_column("Meta (dias)", justify="right")
    t_meq.add_column("Saldo", justify="right")
    t_meq.add_column("Status", justify="center")
    for eq in all_eq_results:
        saldo = max(0, eq["dias_meta"] - eq["dias_acumulados"])
        st = eq["status"]
        cor = "[green]" if st == "DENTRO" else "[red]"
        t_meq.add_row(
            eq["equipe"],
            str(eq["executores"]),
            str(eq["n_fazendas"]),
            f"{eq['hh_total']:,.1f}",
            str(eq["dias_acumulados"]),
            str(eq["dias_meta"]),
            f"{saldo} dias",
            f"{cor}{st}[/]",
        )
    console.print(t_meq)

    try:
        pasta = os.path.join(DIR, DOSSIER_DIRNAME)
        os.makedirs(pasta, exist_ok=True)
        emp_slug = _slug_ficheiro_seguro(empresa_filtro) if empresa_filtro else "Todas"
        nome_xlsx = f"MultiEquipes_{emp_slug}.xlsx"
        caminho = os.path.join(pasta, nome_xlsx)
        rows_eq = []
        for eq in all_eq_results:
            for r in eq["resultados_fazendas"]:
                rows_eq.append(
                    {
                        "Equipe": eq["equipe"],
                        "Data_inicio": eq.get("data_inicio_txt"),
                        "Data_termino": eq.get("data_fim_txt"),
                        "Fazenda": r.get("fazenda"),
                        "Dias": r.get("dias_simulado"),
                        "Dia_inicio_acum": r.get("dia_inicio_acumulado"),
                        "Dia_fim_acum": r.get("dia_fim_acumulado"),
                        "Meta_consumida_%": r.get("pct_meta_consumida"),
                        "Saldo": r.get("saldo_meta_apos"),
                        "Status": r.get("status_meta_continuo"),
                        "HH": r.get("total_hh"),
                        "Receita": r.get("receita_total"),
                        "Custo_MO": r.get("custo_mo_total"),
                    }
                )
        rows_sumario = []
        for eq in all_eq_results:
            rows_sumario.append(
                {
                    "Equipe": eq["equipe"],
                    "Data_inicio": eq.get("data_inicio_txt"),
                    "Data_termino": eq.get("data_fim_txt"),
                    "Executores": eq["executores"],
                    "Jornada": eq["jornada"],
                    "Fazendas": eq["n_fazendas"],
                    "HH_total": eq["hh_total"],
                    "Dias_acumulados": eq["dias_acumulados"],
                    "Meta_dias": eq["dias_meta"],
                    "Status": eq["status"],
                }
            )
        with pd.ExcelWriter(caminho, engine="openpyxl") as w:
            pd.DataFrame(rows_sumario).to_excel(
                w, sheet_name="SUMARIO_EQUIPES", index=False
            )
            pd.DataFrame(rows_eq).to_excel(
                w, sheet_name="DETALHE_POR_FAZENDA", index=False
            )
        ok(f"Multi-equipes exportado: {nome_xlsx}")
    except Exception as ex:
        aviso(f"Erro ao exportar multi-equipes: {ex}")

    linha()
    input(DM + "\n  [ENTER para voltar ao menu] " + RS)


# ──────────────────────────────────────────────
#  MENU PRINCIPAL
# ──────────────────────────────────────────────
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
            print(G + BL + "\n  FILTRO POR EMPRESA (EQUIPE)" + RS)
            print(DM + f"  {len(equipes)} empresa(s) encontrada(s) no micro." + RS)
            equipes_disp = ["TODAS"] + equipes
            eq = selecionar("EMPRESA / EQUIPE", equipes_disp)
            if eq and eq != "TODAS":
                empresa_filtro = eq
                nk_sel = normalizar_chave(eq)
                sem_eq = df_filt["equipe"].isna() | (
                    df_filt["equipe"].astype(str).str.strip() == ""
                )
                n_sem = int(sem_eq.sum())
                if n_sem:
                    print(
                        DM
                        + f"  Excluindo {n_sem} linha(s) sem EQUIPE preenchida (nao entram no filtro por empresa)."
                        + RS
                    )
                df_filt = df_filt[~sem_eq]
                df_filt = df_filt[
                    df_filt["equipe"]
                    .astype(str)
                    .apply(lambda x: normalizar_chave(x.strip()) == nk_sel)
                ]
                ok(
                    f"Filtrado por equipe: {eq} ({len(df_filt)} registros, "
                    f"{df_filt['atividade'].nunique()} atividade(s), {df_filt['fazenda'].nunique()} fazenda(s))"
                )
    if empresa_filtro:
        contexto_sessao.atualizar_equipe(empresa_filtro)
    else:
        contexto_sessao.atualizar_equipe(None)
    _emitir_monitor_atual()
    return df_filt, empresa_filtro


def _selecionar_talhoes_fazenda(df_faz, fazenda):
    """Permite recorte por talhao dentro da fazenda selecionada."""
    if df_faz is None or df_faz.empty:
        contexto_sessao.definir_escopo_talhoes([], [])
        return df_faz, {"fazenda": fazenda, "modo_talhao": "vazio", "talhoes": []}
    if "chave" not in df_faz.columns:
        contexto_sessao.definir_escopo_talhoes([], [])
        return df_faz, {"fazenda": fazenda, "modo_talhao": "sem_coluna", "talhoes": []}

    talhoes = sorted(
        {str(x).strip() for x in df_faz["chave"].dropna().tolist() if str(x).strip()},
        key=str,
    )
    if not talhoes:
        contexto_sessao.definir_escopo_talhoes([], [])
        return df_faz, {"fazenda": fazenda, "modo_talhao": "sem_talhoes", "talhoes": []}
    if len(talhoes) == 1:
        ok(f"Talhao unico na fazenda: {talhoes[0]}")
        contexto_sessao.definir_escopo_talhoes(talhoes[:], talhoes[:])
        _emitir_monitor_atual()
        return df_faz, {
            "fazenda": fazenda,
            "modo_talhao": "unico",
            "talhoes": talhoes[:],
        }

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
        _emitir_monitor_atual()
        return df_faz, {
            "fazenda": fazenda,
            "modo_talhao": "todos",
            "talhoes": talhoes[:],
        }

    selecionados = []
    if op == "SELECIONAR TALHOES POR LISTA":
        print(DM + "  Digite numeros separados por virgula (ex.: 1,3,7)." + RS)
        for i, t in enumerate(talhoes, 1):
            print(G + f"  [{i:2}] " + C + str(t) + RS)
        raw = prompt("Talhoes", "")
        idxs = []
        for p in str(raw).replace(";", ",").split(","):
            p = p.strip()
            if p.isdigit():
                iv = int(p)
                if 1 <= iv <= len(talhoes):
                    idxs.append(iv - 1)
        idxs = sorted(set(idxs))
        selecionados = [talhoes[i] for i in idxs]
    else:
        filtro = normalizar_chave(prompt("Texto para filtrar talhoes", ""))
        if filtro:
            selecionados = [t for t in talhoes if filtro in normalizar_chave(t)]

    if not selecionados:
        aviso("Nenhum talhao selecionado; mantendo TODOS os talhoes da fazenda.")
        contexto_sessao.definir_escopo_talhoes(talhoes[:], talhoes[:])
        _emitir_monitor_atual()
        return df_faz, {
            "fazenda": fazenda,
            "modo_talhao": "fallback_todos",
            "talhoes": talhoes[:],
        }

    df_sel = df_faz[df_faz["chave"].astype(str).isin(set(selecionados))].copy()
    ok(
        f"Escopo por talhao aplicado: {len(selecionados)} selecionado(s), {len(df_sel)} linha(s) no micro."
    )
    contexto_sessao.definir_escopo_talhoes(selecionados, talhoes[:])
    _emitir_monitor_atual()
    return df_sel, {
        "fazenda": fazenda,
        "modo_talhao": "parcial",
        "talhoes": selecionados,
    }


def _menu_ajustar_escopo_atividades(df_faz):
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
        tls = _talhoes()
        sub()
        print(G + BL + "  AJUSTE DE ATIVIDADES (APENAS NESTA EXECUCAO)" + RS)
        print(
            DM
            + f"  Atividades no escopo: {len(atvs)} | Talhoes no escopo: {len(tls)}"
            + RS
        )
        op = selecionar(
            "OPERACAO DE AJUSTE",
            [
                "Substituir atividade",
                "Remover atividade",
                "Adicionar atividade",
                "Concluir ajustes",
            ],
        )
        if not op or op == "Concluir ajustes":
            break

        if op == "Substituir atividade":
            if not atvs:
                aviso("Sem atividades para substituir.")
                continue
            src = selecionar("ATIVIDADE ORIGEM", atvs)
            if not src:
                continue
            dst_opt = selecionar("DESTINO", atvs + ["[DIGITAR NOVA ATIVIDADE]"])
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
            out.loc[out["atividade"].astype(str) == str(src), "atividade"] = dst
            ok(f"Substituida atividade: '{src}' -> '{dst}'.")
            continue

        if op == "Remover atividade":
            if not atvs:
                aviso("Sem atividades para remover.")
                continue
            rm = selecionar("ATIVIDADE PARA REMOVER", atvs)
            if not rm:
                continue
            n0 = len(out)
            out = out[out["atividade"].astype(str) != str(rm)].copy()
            ok(f"Atividade removida do escopo: '{rm}' ({n0 - len(out)} linha(s)).")
            continue

        if op == "Adicionar atividade":
            base_opt = selecionar("NOVA ATIVIDADE", atvs + ["[DIGITAR NOVA ATIVIDADE]"])
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
                "Area/ha para nova atividade (por talhao)",
                round(area_def, 2),
                allow_zero=True,
            )
            pen_def = float(out["penalidade"].median() or 1.0)
            pen_nova = pedir_float(
                "Penalidade de terreno da nova atividade",
                round(pen_def, 2),
                allow_zero=False,
            )

            add_rows = []
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
            ok(f"Atividade '{nova}' adicionada em {len(add_rows)} talhao(es).")

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


def menu_principal(cfg, df, nome_arquivo_micro="", demo_mode=False):
    opcoes = [
        ("1", "Smart Scheduler + Dossier Financeiro"),
        ("2", "Importar Tarifas (CT_313 manual)"),
        ("3", "Normalizar CT_313 -> STG (auto)"),
        ("4", "Mapeamentos de_para (micro -> tarifa)"),
        ("5", "Trocar planilha de microplanejamento (.xlsx)"),
        ("6", "Fazendas micro vs CT (lista fazendas_ct)"),
        ("7", "Importar Planilha de Preco (PRECO_FINAL + custos)"),
        ("8", "Importar Custos Globais Brutos (sem rateio por atividade)"),
        ("9", "Rotas de Metas/Bonificacao/Equacoes (preparatorio)"),
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
        stg_existe = os.path.exists(os.path.join(DIR, STG_FILENAME))
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
        cg = cfg.get("custos_globais", {}) or {}
        if (
            float(cg.get("valor_direto_total", 0) or 0) > 0
            or float(cg.get("valor_indireto_total", 0) or 0) > 0
        ):
            print(
                G
                + "  Custos globais ativos: "
                + C
                + f"Direto R$ {float(cg.get('valor_direto_total', 0) or 0):,.2f} | "
                + f"Indireto R$ {float(cg.get('valor_indireto_total', 0) or 0):,.2f}"
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
                    calcular_cronograma_inteligente(cfg, df_faz, faz)
            else:
                df_scope, empresa_filtro = _aplicar_filtro_empresa_e_escopo(df)
                if df_scope is None or df_scope.empty:
                    aviso("Nenhum dado apos filtros.")
                    continue
                fazendas = sorted(df_scope["fazenda"].unique().tolist())
                if len(fazendas) == 1:
                    faz = fazendas[0]
                    ok(f"Fazenda unica no escopo: {faz}")
                    df_faz = df_scope[df_scope["fazenda"] == faz].copy()
                    contexto_sessao.atualizar_fazenda(faz, df_faz)
                    df_faz, meta_escopo = _selecionar_talhoes_fazenda(df_faz, faz)
                    calcular_cronograma_inteligente(
                        cfg, df_faz, faz, escopo_meta=meta_escopo
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
                        df_faz = df_scope[df_scope["fazenda"] == faz].copy()
                        df_faz, meta_escopo = _selecionar_talhoes_fazenda(df_faz, faz)
                        calcular_cronograma_inteligente(
                            cfg, df_faz, faz, escopo_meta=meta_escopo
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
        elif v == "7":
            modulo_importar_precos_contrato(cfg)
        elif v == "8":
            modulo_importar_custos_globais_brutos(cfg)
        elif v == "9":
            modulo_rotas_metas_bonus(cfg)
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
        f"DEMO Ulianópolis ({DEMO_MICRO_SOURCE_FILENAME} -> {DEMO_MICRO_FILENAME} + CT 313)"
        if demo
        else ""
    )
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
        micro_padrao = os.path.join(DIR, DEMO_MICRO_FILENAME)
        if not os.path.exists(micro_padrao):
            erro(
                f"Modo DEMO: coloque {DEMO_MICRO_SOURCE_FILENAME} (gera {DEMO_MICRO_FILENAME}) "
                f"ou o proprio {DEMO_MICRO_FILENAME} em:\n  {DIR}"
            )
            sys.exit(1)
    else:
        micro_padrao = _find_default_micro_path(cfg)
    ct_padrao = _find_default_ct_path()
    contrato_cfg = cfg.get("precos_contrato", {})
    usar_contrato = bool(
        contrato_cfg and contrato_cfg.get("arquivo") and len(cfg.get("tarifas", {})) > 0
    )

    if usar_contrato:
        ok(
            f"Preco de contrato ativo: {contrato_cfg.get('arquivo')} | {len(cfg.get('tarifas', {}))} tarifas"
        )
    elif ct_padrao:
        try:
            stg_path, n, custo_h = normalizar_ct313(ct_padrao)
            if stg_path and n > 0:
                cfg["tarifas"] = carregar_stg_tarifas(stg_path)
                cfg["custo_hora_tf"] = round(custo_h, 4)
                salvar_config(cfg)
                ok(
                    f"CT auto: {os.path.basename(ct_padrao)} -> {n} tarifas | custo/h TF = R${custo_h:.2f}"
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


if __name__ == "__main__":
    main()
