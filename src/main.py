"""Auto-Guardar (Task Hero).

Sem argumentos -> abre a JANELA (GUI com caixinhas + bandeja).
    --console : modo terminal (teclas F8/F7/F9), sem janela
    --debug   : so mostra a confianca do INVEN FULL (nao clica)
    --once    : testa o 'Guardar Tudo' uma vez e sai
"""
from __future__ import annotations

import argparse
import ctypes
import sys
import time

import config as cfgmod
import ui
import vision
from assets import Assets

VERSION = "v2"


def set_dpi_aware() -> None:
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def ensure_console() -> None:
    """Quando empacotado como app de janela, abre um console p/ os modos de texto."""
    if getattr(sys, "frozen", False):
        try:
            ctypes.windll.kernel32.AllocConsole()
            sys.stdout = open("CONOUT$", "w", encoding="utf-8", errors="replace")
            sys.stderr = open("CONOUT$", "w", encoding="utf-8", errors="replace")
        except Exception:
            pass
    ui.enable()


def debug_loop(cfg, A) -> int:
    import engine
    tr = engine.Tracker(A)
    ui.header("DEBUG · INVEN FULL", VERSION)
    ui.info("Nao clica; so mostra a confianca. Ctrl+C p/ sair.")
    last = 0.0
    try:
        while True:
            t0 = time.time()
            scr = vision.grab_screen()
            if tr.roi is None:
                tr.acquire(scr)
            conf = tr.inven_full_conf(scr)
            cur = 0.0 if conf is None else conf
            present = conf is not None and conf >= cfg.trigger_threshold
            if t0 - last > 0.2:
                col = ui.GREEN if present else ui.GRAY
                state = "INVEN FULL" if present else ("procurando" if conf is None else "vazio/ok")
                sc = "?" if tr.scale is None else f"{tr.scale:.2f}"
                bar = "█" * int(min(cur, 1.0) * 20) + "·" * (20 - int(min(cur, 1.0) * 20))
                print(f"\r  conf {col}{cur:0.3f}{ui.RESET} [{col}{bar}{ui.RESET}] "
                      f"{col}{state:<11}{ui.RESET} {ui.GRAY}escala={sc}{ui.RESET}   ", end="", flush=True)
                last = t0
            dt = time.time() - t0
            if dt < cfg.poll_interval_s:
                time.sleep(cfg.poll_interval_s - dt)
    except KeyboardInterrupt:
        print("\n  saindo.")
    return 0


def once_run(cfg, A) -> int:
    import os
    import tempfile
    import actions
    import engine
    shots = os.path.join(tempfile.gettempdir(), "th_shots")
    ui.header("TESTE · Guardar uma vez", VERSION)
    ui.info("Guardando UMA vez em 3s. Nao mexa no mouse.")
    ui.kv("Prints", shots, ui.GRAY)
    time.sleep(3.0)
    tr = engine.Tracker(A)
    tr.acquire(vision.grab_screen())
    ok = actions.store_flow(A, cfg, scale_hint=tr.scale, search_region=tr.region,
                            verbose=True, shots_dir=shots)
    (ui.good if ok else ui.err)("concluido." if ok else "nao consegui (veja acima).")
    ui.kv("Prints", shots, ui.GRAY)
    return 0 if ok else 1


def console_run(cfg, A) -> int:
    import threading
    import engine
    e = engine.Engine(cfg, A)
    e.active.set()   # modo console roda direto
    if cfg.auto_open_chests:
        e.chests.set()
    if cfg.auto_synth:
        e.synth.set()
    hot = engine.Hotkeys(e, cfg.hotkeys.get("toggle", "f8"), cfg.hotkeys.get("chests", "f7"),
                         cfg.hotkeys.get("synth", "f6"), cfg.hotkeys.get("quit", "f9"))
    hot.start()
    ui.header("AUTO-GUARDAR · console", VERSION)
    ui.kv("Atalhos", "[F8] guardar  [F7] baus  [F6] sintese  [F9] sair")
    ui.rule()
    threading.Thread(target=e.loop, daemon=True).start()
    try:
        while not e.quit.is_set():
            print(f"\r  {ui.GRAY}{e.status:<48}{ui.RESET}", end="", flush=True)
            time.sleep(0.4)
    except KeyboardInterrupt:
        e.quit.set()
    hot.stop()
    print("\n  saindo.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Auto-Guardar (Task Hero)")
    ap.add_argument("--console", action="store_true", help="modo terminal (sem janela)")
    ap.add_argument("--debug", action="store_true", help="so mostra a confianca, nao clica")
    ap.add_argument("--once", action="store_true", help="testa o 'Guardar Tudo' uma vez")
    args = ap.parse_args()

    set_dpi_aware()

    if args.debug or args.once or args.console:
        ensure_console()
        try:
            cfg = cfgmod.load()
            A = Assets()
        except FileNotFoundError as e:
            print(f"ERRO: {e}")
            return 1
        if args.once:
            return once_run(cfg, A)
        if args.debug:
            return debug_loop(cfg, A)
        return console_run(cfg, A)

    # padrao: janela (GUI)
    import gui
    return gui.run(VERSION)


if __name__ == "__main__":
    raise SystemExit(main())
