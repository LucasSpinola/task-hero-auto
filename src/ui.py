"""Saida de console bonita: cores ANSI + moldura (Windows 10+)."""
from __future__ import annotations

import ctypes
import sys
import time as _time

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
GRAY = "\033[90m"
WHITE = "\033[97m"

_W = 56


def enable() -> None:
    """UTF-8 + processamento de sequencias ANSI no console do Windows."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    try:
        k = ctypes.windll.kernel32
        h = k.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        k.GetConsoleMode(h, ctypes.byref(mode))
        k.SetConsoleMode(h, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except Exception:
        pass


def header(title: str, subtitle: str = "") -> None:
    print()
    print(CYAN + "╔" + "═" * _W + "╗" + RESET)
    print(CYAN + "║" + RESET + BOLD + WHITE + title.center(_W) + RESET + CYAN + "║" + RESET)
    if subtitle:
        print(CYAN + "║" + RESET + DIM + subtitle.center(_W) + RESET + CYAN + "║" + RESET)
    print(CYAN + "╚" + "═" * _W + "╝" + RESET)


def kv(key: str, val: str, color: str = WHITE) -> None:
    print(f"  {GRAY}{key:<10}{RESET} {color}{val}{RESET}")


def rule() -> None:
    print(GRAY + "  " + "─" * (_W - 2) + RESET)


def info(msg: str) -> None:
    print(f"  {CYAN}»{RESET} {msg}")


def good(msg: str) -> None:
    print(f"  {GREEN}✔{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"  {YELLOW}▲{RESET} {msg}")


def err(msg: str) -> None:
    print(f"  {RED}✖{RESET} {msg}")


def step(msg: str) -> None:
    print(f"     {GRAY}└─ {msg}{RESET}")


def log(msg: str, color: str = CYAN) -> None:
    """Linha de log com horario + marcador colorido (usada na janela/console)."""
    ts = _time.strftime("%H:%M:%S")
    print(f"{GRAY}{ts}{RESET}  {color}•{RESET} {msg}")


def tag(text: str, color: str) -> str:
    return f"{color}{BOLD}{text}{RESET}"


# garante UTF-8/ANSI assim que o modulo e importado (evita crash de encoding)
enable()
