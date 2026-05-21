"""
SRF terminal UI helpers — colors, menus, headers, prompts.

Depends on: srf.text_utils (only for parse_intervalos_escolha)
External: colorama (optional), rich (required)

When ORCA_WEB_MODE=1 is set, interactive functions (prompt, confirmar,
pedir_float, pedir_int, pedir_jornada, selecionar, selecionar_paginado)
delegate to _get_web_bridge() instead of using terminal input(). This allows
the web adapter (src/web/bridge.py) to intercept calls and route them
through a queue-based pause/resume mechanism for the FastAPI web UI.
"""

import datetime
import math
import os
import sys
import threading

_WEB_MODE_INIT = os.environ.get("ORCA_WEB_MODE") == "1"
_tl = threading.local()
_tl._web_bridge = None
_tl._WEB_MODE = _WEB_MODE_INIT


def _get_web_bridge():
    return getattr(_tl, "_web_bridge", None)


def _is_web_mode():
    return getattr(_tl, "_WEB_MODE", _WEB_MODE_INIT)


try:
    from rich.console import Console
    from rich.table import Table
except ImportError:
    print("Instale: pip install rich pandas openpyxl")
    sys.exit(1)

# ──────────────────────────────────────────────
# CORES & UI (estilo ATM v3)
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
                                   ▄▄████████████████▄▄
                                 ▄████▀▀▀▀▀▀▀▀▀▀▀▀▀████▄
                               ▄██▀░░░░░░░░░░░░░░░░░░░░▀██▄
                              ██▀░░░░░░░░░░░░░░░░░░░░░░░░▀██
                             ██░░░░░░░░░░░░░░░░░░░░░░░░░░░██
                            ██▀░░░░░░░░░░░░░░░░░░░░░░░░░░░░██
                           ██▀░░░░░░░░░░░░░░░░░░░░░░░░░░░░░██
                          ██▀░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░██
                          ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░██
                          ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░██
                          ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░██
                          ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░██
                          ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░██
                          ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░██
                          ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░██
                          ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░██
                          ▀█░░░░░░░░░░░░░░░░░░░░░░░░░░░░░██
                          ▀█░░░░░░░░░░░░░░░░░░░░░░░░░░░░░██
                           █░░░░░░░░░░░░░░░░░░░░░░░░░░░██
                           █░░░░░░░░░░░░░░░░░░░░░░░░░░██
                           ▀█░░░░░░░░░░░░░░░░░░░░░░░░░██
                            █░░░░░░░░░░░░░░░░░░░░░░░░██
                            ▀█░░░░░░░░░░░░░░░░░░░░░░██
                             █▄░░░░░░░░░░░░░░░░░░░▄█
                              ██▄▄░░░░░░░░░░░░░░▄██
                               ▀▀████▄▄▄▄▄▄▄▄▄▄████▀▀
"""

VERSION = "7.0"
APP_NAME = "Orca — Sistema de Restauracao Florestal"

# ──────────────────────────────────────────────
# DISPLAY HELPERS
# ──────────────────────────────────────────────

def linha(c="="):
    print(G + c * W + RS)


def sub(c="-"):
    print(DM + c * W + RS)


def cabecalho(sub_titulo=""):
    os.system("cls" if os.name == "nt" else "clear")
    print(G + ASCII_ART + RS)
    linha()
    print(G + BL + f" [ ORCA ] {APP_NAME} v{VERSION}".center(W) + RS)
    if sub_titulo:
        print(DM + G + sub_titulo.center(W) + RS)
    print(DM + G + datetime.datetime.now().strftime(" %d/%m/%Y %H:%M").center(W) + RS)
    linha()


def subcabecalho(sub_titulo=""):
    """Versao incremental que nao limpa a tela, mantem conteudo anterior."""
    print("\n" + "-" * W)
    print(G + BL + f" [ ORCA ] {APP_NAME} v{VERSION}".center(W) + RS)
    if sub_titulo:
        print(DM + G + sub_titulo.center(W) + RS)
    print(DM + G + datetime.datetime.now().strftime(" %d/%m/%Y %H:%M").center(W) + RS)
    print("-" * W + "\n")


def aviso(m):
    print(Y + f"\n ! {m}" + RS)


def erro(m):
    print(R + f"\n X {m}" + RS)


def ok(m):
    print(G + f"\n + {m}" + RS)


# ──────────────────────────────────────────────
# INPUT HELPERS
# ──────────────────────────────────────────────

def prompt(msg, default=None):
    if _is_web_mode() and _get_web_bridge() is not None:
        return _get_web_bridge().prompt(msg, default)
    suf = f" [{default}]" if default is not None else ""
    try:
        v = input(G + " >> " + C + msg + suf + G + ": " + RS).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    return v if v else (str(default) if default is not None else "")


def pedir_float(msg, default, allow_zero=False):
    if _is_web_mode() and _get_web_bridge() is not None:
        return _get_web_bridge().pedir_float(msg, default, allow_zero=allow_zero)
    while True:
        v = prompt(msg, default)
        try:
            f = float(str(v).replace(",", "."))
            if f > 0 or (allow_zero and f >= 0):
                return f
        except ValueError:
            pass
        aviso("Valor invalido.")


def _parse_jornada(valor):
    s = str(valor).strip().replace(",", ".")
    try:
        return float(s)
    except ValueError:
        pass
    for sep in (":", "h", "e", "E", "H"):
        if sep in s:
            partes = s.split(sep, 1)
            try:
                h = float(partes[0].strip())
                m = float(partes[1].strip())
                if h >= 0 and 0 <= m < 60:
                    return h + m / 60.0
            except (ValueError, IndexError):
                pass
    return None


def pedir_jornada(msg, default):
    if _is_web_mode() and _get_web_bridge() is not None:
        return _get_web_bridge().pedir_jornada(msg, default)
    while True:
        v = prompt(msg, default)
        resultado = _parse_jornada(v)
        if resultado is not None and resultado > 0:
            return resultado
        aviso("Valor invalido. Use decimal (6.5) ou horario (6:30 = 6h30).")


def pedir_int(msg, default, allow_zero=False):
    if _is_web_mode() and _get_web_bridge() is not None:
        return _get_web_bridge().pedir_int(msg, default, allow_zero=allow_zero)
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
    if _is_web_mode() and _get_web_bridge() is not None:
        return _get_web_bridge().selecionar(titulo, itens, zero_label=zero_label)
    print(G + f"\n -- {titulo} " + "--" * max(0, (W - len(titulo) - 6) // 2) + RS)
    for i, it in enumerate(itens, 1):
        print(G + f" [{i:2}] " + C + str(it) + RS)
    print(G + " [ 0] " + DM + zero_label + RS)
    while True:
        v = prompt("Escolha").strip()
        if v == "0":
            return None
        if v.isdigit() and 1 <= int(v) <= len(itens):
            return itens[int(v) - 1]
        aviso("Opcao invalida.")


def selecionar_paginado(titulo, itens, page_size=5, zero_label="Voltar"):
    if _is_web_mode() and _get_web_bridge() is not None:
        return _get_web_bridge().selecionar_paginado(titulo, itens, page_size=page_size, zero_label=zero_label)
    total = len(itens)
    page = 0
    max_page = math.ceil(total / page_size) - 1
    while True:
        start = page * page_size
        end = min(start + page_size, total)
        print(
            G
            + f"\n -- {titulo} (pag {page + 1}/{max_page + 1}) "
            + "--" * max(0, (W - len(titulo) - 16) // 2)
            + RS
        )
        for i in range(start, end):
            print(G + f" [{i + 1:2}] " + C + str(itens[i]) + RS)
        nav = []
        if page > 0:
            nav.append("[-] Anterior")
        if page < max_page:
            nav.append("[+] Proxima")
        nav.append("[0] " + zero_label)
        print(DM + " " + " ".join(nav) + RS)
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
    if _is_web_mode() and _get_web_bridge() is not None:
        return _get_web_bridge().confirmar(msg, default=default)
    s = "S/n" if default else "s/N"
    v = prompt(f"{msg} [{s}]").strip().lower()
    if not v:
        return default
    return v in ("s", "sim", "y", "yes")


def esperar(msg="Pressione ENTER para continuar"):
    if _is_web_mode() and _get_web_bridge() is not None:
        _get_web_bridge().esperar(msg)
        return
    try:
        input(DM + f"\n [{msg}] " + RS)
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)


def escolha(msg="Opcao", default="0"):
    if _is_web_mode() and _get_web_bridge() is not None:
        return _get_web_bridge().escolha(msg, default)
    try:
        v = input(DM + f">> {msg}: " + RS).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    return v if v else default
