"""Janela (tkinter) com as caixinhas, status, log e bandeja."""
from __future__ import annotations

import os
import re
import sys
import threading
import tkinter as tk
from collections import deque
from tkinter import ttk

import engine as eng_mod
from config import resource_dir

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "TaskHeroAutoStash"


def _icon_path() -> str:
    return str(resource_dir() / "docs" / "icone.ico")


class LogWriter:
    """Captura print()/ui.* e guarda as linhas (sem ANSI) p/ a GUI mostrar."""

    def __init__(self):
        self.buf = deque(maxlen=400)
        self.lock = threading.Lock()

    def write(self, s):
        s = _ANSI.sub("", s)
        if not s:
            return
        with self.lock:
            self.buf.append(s)

    def flush(self):
        pass

    def drain(self) -> str:
        with self.lock:
            if not self.buf:
                return ""
            out = "".join(self.buf)
            self.buf.clear()
            return out


def _startup_target() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    script = os.path.join(os.path.dirname(__file__), "main.py")
    return f'"{pyw}" "{script}"'


def is_startup_enabled() -> bool:
    import winreg
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY)
        winreg.QueryValueEx(k, RUN_NAME)
        winreg.CloseKey(k)
        return True
    except OSError:
        return False


def set_startup(enable: bool) -> None:
    import winreg
    k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_ALL_ACCESS)
    try:
        if enable:
            winreg.SetValueEx(k, RUN_NAME, 0, winreg.REG_SZ, _startup_target())
        else:
            try:
                winreg.DeleteValue(k, RUN_NAME)
            except OSError:
                pass
    finally:
        winreg.CloseKey(k)


def _make_tray(root, engine):
    try:
        import pystray
        from PIL import Image, ImageDraw
    except Exception:
        return None

    try:
        img = Image.open(_icon_path()).convert("RGBA")
    except Exception:
        img = Image.new("RGB", (64, 64), (28, 28, 36))
        d = ImageDraw.Draw(img)
        d.rectangle([12, 24, 52, 50], fill=(210, 160, 50), outline=(120, 80, 20), width=2)
        d.rectangle([12, 24, 52, 34], fill=(180, 130, 40))
        d.rectangle([29, 36, 35, 44], fill=(120, 80, 20))

    def show(icon=None, item=None):
        root.after(0, root.deiconify)

    def toggle_guardar(icon=None, item=None):
        ev = engine.running
        root.after(0, lambda: (ev.clear() if ev.is_set() else ev.set()))

    def toggle_baus(icon=None, item=None):
        ev = engine.chests
        root.after(0, lambda: (ev.clear() if ev.is_set() else ev.set()))

    def quit_app(icon=None, item=None):
        root.after(0, lambda: _do_quit(root, engine))

    menu = pystray.Menu(
        pystray.MenuItem("Mostrar", show, default=True),
        pystray.MenuItem("Auto-guardar", toggle_guardar, checked=lambda i: engine.running.is_set()),
        pystray.MenuItem("Auto-abrir baus", toggle_baus, checked=lambda i: engine.chests.is_set()),
        pystray.MenuItem("Sair", quit_app),
    )
    icon = pystray.Icon(RUN_NAME, img, "Task Hero Auto", menu)
    icon.run_detached()
    return icon


def _do_quit(root, engine, icon=None):
    engine.quit.set()
    try:
        if icon is not None:
            icon.stop()
    except Exception:
        pass
    root.destroy()


def run(version: str = "") -> int:
    # captura stdout/stderr -> log da GUI (os prints do engine/actions caem aqui)
    log = LogWriter()
    sys.stdout = log
    sys.stderr = log

    import config as cfgmod
    from assets import Assets
    try:
        cfg = cfgmod.load()
        A = Assets()
    except Exception as e:
        import tkinter.messagebox as mb
        r = tk.Tk()
        r.withdraw()
        mb.showerror("Task Hero Auto", f"Erro ao iniciar:\n\n{e}\n\n"
                     "Faltam os templates em templates/ui? Reinstale o programa.")
        r.destroy()
        return 1

    engine = eng_mod.Engine(cfg, A)
    if cfg.auto_open_chests:
        engine.chests.set()
    if cfg.auto_synth:
        engine.synth.set()

    hot = eng_mod.Hotkeys(engine, cfg.hotkeys.get("toggle", "f8"), cfg.hotkeys.get("chests", "f7"),
                          cfg.hotkeys.get("synth", "f6"), cfg.hotkeys.get("quit", "f9"))
    hot.start()

    root = tk.Tk()
    root.title("Task Hero Auto")
    root.geometry("480x560")
    root.minsize(440, 520)
    root.configure(bg="#f4f5f7")
    try:
        root.iconbitmap(_icon_path())
    except Exception:
        pass

    try:
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure(".", background="#f4f5f7")
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 15), background="#f4f5f7")
        style.configure("Sub.TLabel", font=("Segoe UI", 9), foreground="#6b7280", background="#f4f5f7")
        style.configure("St.TLabel", font=("Segoe UI", 10), background="#f4f5f7")
        style.configure("TCheckbutton", font=("Segoe UI", 10), background="#f4f5f7")
        style.configure("Card.TLabelframe", background="#f4f5f7")
        style.configure("Card.TLabelframe.Label", font=("Segoe UI Semibold", 9),
                        foreground="#374151", background="#f4f5f7")
    except Exception:
        style = None

    var_guardar = tk.BooleanVar(value=engine.running.is_set())
    var_baus = tk.BooleanVar(value=engine.chests.is_set())
    var_synth = tk.BooleanVar(value=engine.synth.is_set())
    var_startup = tk.BooleanVar(value=is_startup_enabled())

    def on_guardar():
        engine.running.set() if var_guardar.get() else engine.running.clear()

    def on_baus():
        engine.chests.set() if var_baus.get() else engine.chests.clear()

    def on_synth():
        if var_synth.get():
            engine._last_synth = 0.0   # roda o 1o ciclo logo ao marcar
            engine.synth.set()
        else:
            engine.synth.clear()

    def on_startup():
        try:
            set_startup(var_startup.get())
        except Exception as e:
            print(f"[aviso] nao consegui ajustar inicio com Windows: {e!r}")

    # cabecalho
    head = ttk.Frame(root, padding=(16, 14, 16, 4))
    head.pack(fill="x")
    ttk.Label(head, text="Task Hero Auto", style="Title.TLabel").pack(anchor="w")
    ttk.Label(head, text="Abra o jogo, marque abaixo o que você quer no automático, e pode deixar rodando.",
              style="Sub.TLabel", wraplength=440, justify="left").pack(anchor="w", pady=(1, 0))

    # status
    strow = ttk.Frame(root, padding=(16, 6, 16, 8))
    strow.pack(fill="x")
    dot = tk.Label(strow, text="●", fg="#9aa0a6", bg="#f4f5f7", font=("Segoe UI", 12))
    dot.pack(side="left")
    status_var = tk.StringVar(value="iniciando...")
    ttk.Label(strow, textvariable=status_var, style="St.TLabel").pack(side="left", padx=(7, 0))

    # automacoes
    auto = ttk.LabelFrame(root, text=" Automações ", padding=(12, 8), style="Card.TLabelframe")
    auto.pack(fill="x", padx=14, pady=(0, 8))
    ttk.Checkbutton(auto, text="Guardar no baú quando o inventário encher        ·  F8",
                    variable=var_guardar, command=on_guardar).pack(anchor="w", pady=3)
    ttk.Checkbutton(auto, text="Abrir os baús (azul/marrom) que aparecem         ·  F7",
                    variable=var_baus, command=on_baus).pack(anchor="w", pady=3)
    ttk.Checkbutton(auto, text=f"Sintetizar no cubo a cada {int(cfg.synth_interval_min)} minutos             ·  F6",
                    variable=var_synth, command=on_synth).pack(anchor="w", pady=3)

    # opcoes
    optf = ttk.LabelFrame(root, text=" Opções ", padding=(12, 8), style="Card.TLabelframe")
    optf.pack(fill="x", padx=14, pady=(0, 8))
    ttk.Checkbutton(optf, text="Iniciar junto com o Windows",
                    variable=var_startup, command=on_startup).pack(anchor="w", pady=2)
    ttk.Label(optf, text="Deixe o jogo visível, fechar no X envia para a bandeja.",
              style="Sub.TLabel").pack(anchor="w", pady=(4, 0))

    # rodape com o credito (fixado embaixo)
    cred = "feito por Lucas Spinola" + (f"   ·   {version}" if version else "")
    foot = ttk.Frame(root, padding=(16, 4, 16, 8))
    foot.pack(side="bottom", fill="x")
    ttk.Label(foot, text=cred, style="Sub.TLabel").pack(anchor="center")

    # atividade (log)
    logf = ttk.LabelFrame(root, text=" Atividade ", padding=(4, 4), style="Card.TLabelframe")
    logf.pack(fill="both", expand=True, padx=14, pady=(0, 8))
    logbox = tk.Text(logf, height=7, wrap="word", state="disabled", relief="flat",
                     bg="#0f1117", fg="#cdd2dc", font=("Consolas", 9), padx=10, pady=8,
                     highlightthickness=0, borderwidth=0)
    logbox.pack(fill="both", expand=True)

    icon = _make_tray(root, engine)
    tray_ok = icon is not None

    def hide_to_tray():
        if tray_ok:
            root.withdraw()
        else:
            root.iconify()

    root.protocol("WM_DELETE_WINDOW", hide_to_tray)

    def poll():
        # status + sincroniza caixinhas com o estado real (teclas/bandeja)
        status_var.set(engine.status)
        any_on = engine.running.is_set() or engine.chests.is_set() or engine.synth.is_set()
        dot.configure(fg="#22c55e" if any_on else "#9aa0a6")  # verde = ativo, cinza = parado
        if var_guardar.get() != engine.running.is_set():
            var_guardar.set(engine.running.is_set())
        if var_baus.get() != engine.chests.is_set():
            var_baus.set(engine.chests.is_set())
        if var_synth.get() != engine.synth.is_set():
            var_synth.set(engine.synth.is_set())
        text = log.drain()
        if text:
            logbox.configure(state="normal")
            logbox.insert("end", text)
            logbox.see("end")
            # limita o tamanho
            if int(logbox.index("end-1c").split(".")[0]) > 500:
                logbox.delete("1.0", "200.0")
            logbox.configure(state="disabled")
        if engine.quit.is_set():
            _do_quit(root, engine, icon)
            return
        root.after(180, poll)

    threading.Thread(target=engine.loop, daemon=True).start()
    print("Pronto! Marque o que quer automatizar acima.")
    print("Atalhos: F8 guardar · F7 baús · F6 síntese · F9 sair.")
    root.after(200, poll)
    root.mainloop()
    hot.stop()
    return 0
