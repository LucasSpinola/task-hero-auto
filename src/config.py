"""Carrega e cria o config.json."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path


def base_dir() -> Path:
    """Pasta GRAVAVEL (config.json): ao lado do .exe, ou raiz do projeto."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_dir() -> Path:
    """Pasta dos recursos EMBUTIDOS (templates): _MEIPASS no .exe, ou raiz do projeto."""
    mei = getattr(sys, "_MEIPASS", None)
    if mei:
        return Path(mei)
    return Path(__file__).resolve().parent.parent


CONFIG_PATH = base_dir() / "config.json"


@dataclass
class Config:
    # abas do STASH em que guardar (ordem importa). Ex.: ["tab1","tab2"]
    tabs: list = field(default_factory=lambda: ["tab1", "tab2"])
    trigger_threshold: float = 0.74      # confianca minima p/ "INVEN FULL"
    poll_interval_s: float = 1.2         # intervalo entre checagens
    ui_wait_ms: int = 450                # espera entre cliques (abrir/trocar aba)
    cooldown_s: float = 5.0              # tempo minimo entre dois "guardar"
    auto_open_chests: bool = False       # F7: clicar os baus (azul/marrom) ao aparecerem
    chest_threshold: float = 0.78        # confianca minima p/ detectar um bau
    auto_synth: bool = False             # F6: sintese no cubo a cada X min
    synth_interval_min: float = 10.0     # intervalo da sintese (minutos)
    synth_max_rarity: str = "azul"       # sintetiza ate esta cor (cinza..roxo)
    hotkeys: dict = field(default_factory=lambda: {
        "toggle": "f8", "chests": "f7", "synth": "f6", "quit": "f9"})
    click_backend: str = "pyautogui"     # ou "pydirectinput"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        d = cls()
        d.tabs = list(data.get("tabs", d.tabs)) or ["tab1", "tab2"]
        d.trigger_threshold = float(data.get("trigger_threshold", d.trigger_threshold))
        d.poll_interval_s = float(data.get("poll_interval_s", d.poll_interval_s))
        d.ui_wait_ms = int(data.get("ui_wait_ms", d.ui_wait_ms))
        d.cooldown_s = float(data.get("cooldown_s", d.cooldown_s))
        d.auto_open_chests = bool(data.get("auto_open_chests", d.auto_open_chests))
        d.chest_threshold = float(data.get("chest_threshold", d.chest_threshold))
        d.auto_synth = bool(data.get("auto_synth", d.auto_synth))
        d.synth_interval_min = float(data.get("synth_interval_min", d.synth_interval_min))
        d.synth_max_rarity = str(data.get("synth_max_rarity", d.synth_max_rarity)).lower()
        d.hotkeys = {**d.hotkeys, **dict(data.get("hotkeys", {}))}
        d.click_backend = data.get("click_backend", d.click_backend)
        return d


def load(path: Path | None = None) -> Config:
    """Carrega o config; se nao existir, cria um padrao (zero configuracao)."""
    path = path or CONFIG_PATH
    if not path.exists():
        cfg = Config()
        save(cfg, path)
        return cfg
    with open(path, "r", encoding="utf-8") as f:
        return Config.from_dict(json.load(f))


def save(cfg: Config, path: Path | None = None) -> Path:
    path = path or CONFIG_PATH
    os.makedirs(path.parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg.to_dict(), f, indent=2, ensure_ascii=False)
    return path
