"""Carrega os templates embutidos (templates/ui) e o layout do STASH."""
from __future__ import annotations

import json

import cv2

from config import resource_dir

UI_DIR = resource_dir() / "templates" / "ui"


def _load_gray(name: str):
    p = UI_DIR / name
    img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"template ausente: {p}")
    return img


class Assets:
    def __init__(self):
        self.inven_full = _load_gray("inven_full.png")      # gatilho
        self.btn_open = _load_gray("btn_open.png")          # abrir inventario (botao amarelo)
        self.stash_banner = _load_gray("stash_banner.png")  # ancora do STASH
        self.hero_banner = _load_gray("hero_banner.png")    # ancora do inventario (HERO)
        self.chest_blue = _load_gray("chest_blue.png")      # bau azul (preview no combate)
        self.chest_brown = _load_gray("chest_brown.png")    # bau marrom (preview no combate)
        self.cube_banner = _load_gray("cube_banner.png")    # ancora da janela CUBE (sintese)
        with open(UI_DIR / "layout.json", encoding="utf-8") as f:
            self.layout = json.load(f)

    def stash_points(self, banner_match) -> dict:
        """Centros (tab1, tab2, guardar_tudo, close) a partir do match do banner.

        Offsets foram medidos na escala de referencia; multiplicam pela escala
        em que o banner foi encontrado (tolerante a redimensionamento).
        """
        f = banner_match.scale
        cx, cy = banner_match.cx, banner_match.cy
        offs = self.layout["offsets_from_banner_center"]
        return {k: (cx + f * ox, cy + f * oy) for k, (ox, oy) in offs.items()}

    def chest_point(self, hero_match) -> tuple:
        """Centro do bau (abrir STASH) derivado do banner HERO -- robusto e sem
        depender de casar o icone pequeno do bau (que da falso positivo)."""
        f = hero_match.scale
        ox, oy = self.layout["chest_from_hero_center"]
        return (hero_match.cx + f * ox, hero_match.cy + f * oy)
