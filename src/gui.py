"""Janela (tkinter) escura com Iniciar/Pausar, caixinhas, status, log e bandeja."""
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

# paleta escura
BG = "#16171d"
CARD = "#23252e"
COMBO = "#2c2f3a"
TXT = "#e6e8ee"
SUB = "#8b90a0"
CARDLBL = "#aeb4c2"
GREEN = "#22c55e"
GREEN_D = "#16a34a"
AMBER = "#f59e0b"
AMBER_D = "#d97706"

RAR_DISPLAY = ["Cinza", "Verde", "Azul", "Amarelo", "Vermelho", "Roxo"]


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

    def toggle_active(icon=None, item=None):
        ev = engine.active
        root.after(0, lambda: (ev.clear() if ev.is_set() else ev.set()))

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
        pystray.MenuItem("Iniciar / Pausar", toggle_active, checked=lambda i: engine.active.is_set()),
        pystray.MenuItem("Guardar", toggle_guardar, checked=lambda i: engine.running.is_set()),
        pystray.MenuItem("Abrir baus", toggle_baus, checked=lambda i: engine.chests.is_set()),
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
    root.geometry("470x630")
    root.minsize(440, 580)
    root.configure(bg=BG)
    try:
        root.iconbitmap(_icon_path())
    except Exception:
        pass

    try:
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=TXT, fieldbackground=COMBO, bordercolor=BG)
        style.configure("Card.TLabelframe", background=CARD, bordercolor=CARD, relief="flat")
        style.configure("Card.TLabelframe.Label", font=("Segoe UI Semibold", 9),
                        background=CARD, foreground=CARDLBL)
        style.configure("Dark.TCombobox", fieldbackground=COMBO, background=COMBO, foreground=TXT,
                        arrowcolor=TXT, bordercolor="#3a3d4a", lightcolor=COMBO, darkcolor=COMBO,
                        selectbackground=COMBO, selectforeground=TXT, padding=2)
        style.map("Dark.TCombobox",
                  fieldbackground=[("readonly", COMBO)], foreground=[("readonly", TXT)],
                  selectbackground=[("readonly", COMBO)], selectforeground=[("readonly", TXT)])
        root.option_add("*TCombobox*Listbox.background", CARD)
        root.option_add("*TCombobox*Listbox.foreground", TXT)
        root.option_add("*TCombobox*Listbox.selectBackground", GREEN)
        root.option_add("*TCombobox*Listbox.selectForeground", BG)
    except Exception:
        pass

    var_guardar = tk.BooleanVar(value=engine.running.is_set())
    var_baus = tk.BooleanVar(value=engine.chests.is_set())
    var_synth = tk.BooleanVar(value=engine.synth.is_set())
    var_startup = tk.BooleanVar(value=is_startup_enabled())
    cur_rar = (cfg.synth_max_rarity or "azul").capitalize()
    var_rar = tk.StringVar(value=cur_rar if cur_rar in RAR_DISPLAY else "Azul")

    def on_guardar():
        engine.running.set() if var_guardar.get() else engine.running.clear()

    def on_baus():
        engine.chests.set() if var_baus.get() else engine.chests.clear()

    def on_synth():
        if var_synth.get():
            engine._last_synth = 0.0   # roda o 1o ciclo logo ao ligar
            engine.synth.set()
        else:
            engine.synth.clear()

    def on_rar(event=None):
        cfg.synth_max_rarity = var_rar.get().lower()
        try:
            cfgmod.save(cfg)
        except Exception as e:
            print(f"[aviso] nao salvei a raridade: {e!r}")

    def on_startup():
        try:
            set_startup(var_startup.get())
        except Exception as e:
            print(f"[aviso] nao consegui ajustar inicio com Windows: {e!r}")

    def sync_button():
        if engine.active.is_set():
            btn.configure(text="⏸  Pausar", bg=AMBER, activebackground=AMBER_D)
        else:
            btn.configure(text="▶  Iniciar", bg=GREEN, activebackground=GREEN_D)

    def toggle_active():
        engine.active.clear() if engine.active.is_set() else engine.active.set()
        sync_button()

    def mkcheck(parent, text, var, cmd):
        return tk.Checkbutton(parent, text=text, variable=var, command=cmd,
                              bg=CARD, fg=TXT, selectcolor=COMBO, activebackground=CARD,
                              activeforeground=TXT, font=("Segoe UI", 10), anchor="w",
                              highlightthickness=0, bd=0, padx=0)

    # cabecalho
    head = tk.Frame(root, bg=BG)
    head.pack(fill="x", padx=18, pady=(16, 2))
    tk.Label(head, text="Task Hero Auto", bg=BG, fg=TXT,
             font=("Segoe UI Semibold", 16)).pack(anchor="w")
    tk.Label(head, text="Marque o que você quer no automático e clique Iniciar.",
             bg=BG, fg=SUB, font=("Segoe UI", 9)).pack(anchor="w")

    # status
    strow = tk.Frame(root, bg=BG)
    strow.pack(fill="x", padx=18, pady=(10, 6))
    dot = tk.Label(strow, text="●", bg=BG, fg="#6b7280", font=("Segoe UI", 12))
    dot.pack(side="left")
    status_var = tk.StringVar(value="Pausado")
    tk.Label(strow, textvariable=status_var, bg=BG, fg=TXT, font=("Segoe UI", 10)).pack(side="left", padx=(8, 0))

    # botao mestre
    btn = tk.Button(root, text="▶  Iniciar", command=toggle_active, relief="flat", cursor="hand2",
                    bg=GREEN, fg="#0c1f14", activebackground=GREEN_D, activeforeground="#0c1f14",
                    font=("Segoe UI Semibold", 13), bd=0)
    btn.pack(fill="x", padx=18, pady=(2, 12), ipady=8)

    # automacoes
    auto = ttk.LabelFrame(root, text=" Automações ", style="Card.TLabelframe", padding=(12, 10))
    auto.pack(fill="x", padx=16, pady=(0, 8))
    mkcheck(auto, "Guardar no baú quando o inventário encher", var_guardar, on_guardar).pack(anchor="w", fill="x", pady=2)
    mkcheck(auto, "Abrir os baús que aparecem (azul, marrom e boss)", var_baus, on_baus).pack(anchor="w", fill="x", pady=2)
    srow = tk.Frame(auto, bg=CARD)
    srow.pack(anchor="w", fill="x", pady=2)
    mkcheck(srow, "Sintetizar no cubo", var_synth, on_synth).pack(side="left")
    tk.Label(srow, text="até", bg=CARD, fg=SUB, font=("Segoe UI", 9)).pack(side="left", padx=(6, 4))
    combo = ttk.Combobox(srow, textvariable=var_rar, values=RAR_DISPLAY, state="readonly",
                         width=10, style="Dark.TCombobox")
    combo.pack(side="left")
    combo.bind("<<ComboboxSelected>>", on_rar)
    tk.Label(auto, text="Atalhos:  F8 guardar · F7 baús · F6 síntese · F9 sair",
             bg=CARD, fg=SUB, font=("Segoe UI", 8)).pack(anchor="w", pady=(8, 0))

    # opcoes
    optf = ttk.LabelFrame(root, text=" Opções ", style="Card.TLabelframe", padding=(12, 10))
    optf.pack(fill="x", padx=16, pady=(0, 8))
    mkcheck(optf, "Iniciar junto com o Windows", var_startup, on_startup).pack(anchor="w", pady=1)
    tk.Label(optf, text="Deixe o jogo visível. Fechar no X envia para a bandeja.",
             bg=CARD, fg=SUB, font=("Segoe UI", 8)).pack(anchor="w", pady=(4, 0))

    # rodape com o credito
    cred = "feito por Lucas Spinola" + (f"   ·   {version}" if version else "")
    foot = tk.Frame(root, bg=BG)
    foot.pack(side="bottom", fill="x", pady=(2, 8))
    tk.Label(foot, text=cred, bg=BG, fg=SUB, font=("Segoe UI", 8)).pack(anchor="center")

    # atividade (log)
    logf = ttk.LabelFrame(root, text=" Atividade ", style="Card.TLabelframe", padding=(6, 6))
    logf.pack(fill="both", expand=True, padx=16, pady=(0, 8))
    logbox = tk.Text(logf, height=7, wrap="word", state="disabled", relief="flat",
                     bg="#0f1117", fg="#cdd2dc", insertbackground="#cdd2dc",
                     font=("Consolas", 9), padx=10, pady=8, highlightthickness=0, bd=0)
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
        status_var.set(engine.status)
        on = engine.active.is_set()
        dot.configure(fg=GREEN if on else "#6b7280")
        want = "⏸  Pausar" if on else "▶  Iniciar"
        if btn.cget("text") != want:
            sync_button()
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
            if int(logbox.index("end-1c").split(".")[0]) > 500:
                logbox.delete("1.0", "200.0")
            logbox.configure(state="disabled")
        if engine.quit.is_set():
            _do_quit(root, engine, icon)
            return
        root.after(180, poll)

    threading.Thread(target=engine.loop, daemon=True).start()
    print("Pronto! Marque o que quer e clique Iniciar.")
    print("Atalhos: F8 guardar · F7 baús · F6 síntese · F9 sair.")
    root.after(200, poll)
    root.mainloop()
    hot.stop()
    return 0
