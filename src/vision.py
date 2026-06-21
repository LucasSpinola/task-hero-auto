"""Captura da tela e busca por template multi-escala."""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import mss
import numpy as np

DEFAULT_SCALES = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.78, 0.86, 0.94,
                  1.0, 1.08, 1.18, 1.30, 1.45, 1.62, 1.82, 2.05, 2.3]


@dataclass
class Match:
    conf: float
    left: int      # canto sup-esq dentro da imagem capturada
    top: int
    w: int         # tamanho do match (template * escala)
    h: int
    scale: float

    @property
    def cx(self) -> float:
        return self.left + self.w / 2.0

    @property
    def cy(self) -> float:
        return self.top + self.h / 2.0


@dataclass
class Screen:
    gray: np.ndarray
    left: int   # offset da tela virtual (ex.: -1920) p/ converter em coord absoluta
    top: int
    bgr: np.ndarray | None = None  # cor (so p/ prints de diagnostico)

    def to_abs(self, x: float, y: float) -> tuple[int, int]:
        return int(round(self.left + x)), int(round(self.top + y))


def grab_screen(color: bool = False) -> Screen:
    """Captura a tela virtual inteira (todos os monitores) em escala de cinza."""
    with mss.MSS() as sct:
        vs = sct.monitors[0]
        img = np.array(sct.grab(vs))[:, :, :3]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return Screen(gray=gray, left=int(vs["left"]), top=int(vs["top"]),
                  bgr=np.ascontiguousarray(img) if color else None)


def monitor_rects(screen: "Screen"):
    """Retangulos (l,t,r,b) de cada monitor, em coords da imagem capturada."""
    with mss.MSS() as sct:
        mons = sct.monitors[1:]
    out = []
    for m in mons:
        l = int(m["left"]) - screen.left
        t = int(m["top"]) - screen.top
        out.append((l, t, l + int(m["width"]), t + int(m["height"])))
    return out


def region_for_point(screen: "Screen", x: float, y: float):
    """(l,t,r,b) do monitor que contem o ponto (coords da imagem). None se nenhum."""
    for (l, t, r, b) in monitor_rects(screen):
        if l <= x < r and t <= y < b:
            H, W = screen.gray.shape[:2]
            return (max(0, l), max(0, t), min(W, r), min(H, b))
    return None


def near(scale: float | None, band: float = 0.2):
    """Escalas proximas de `scale` (p/ buscas rapidas). None se scale desconhecida."""
    if scale is None:
        return None
    return [s for s in DEFAULT_SCALES if abs(s - scale) <= band] or [scale]


def locate(screen_gray: np.ndarray, tpl_gray: np.ndarray, scales=None) -> Match | None:
    """Melhor match do template na imagem, testando varias escalas. None se vazio."""
    scales = scales or DEFAULT_SCALES
    H, W = screen_gray.shape[:2]
    th0, tw0 = tpl_gray.shape[:2]
    best: Match | None = None
    for f in scales:
        tw, th = int(round(tw0 * f)), int(round(th0 * f))
        if tw < 8 or th < 8 or tw > W or th > H:
            continue
        interp = cv2.INTER_AREA if f < 1.0 else cv2.INTER_LINEAR
        rt = cv2.resize(tpl_gray, (tw, th), interpolation=interp)
        res = cv2.matchTemplate(screen_gray, rt, cv2.TM_CCOEFF_NORMED)
        _, mx, _, loc = cv2.minMaxLoc(res)
        if best is None or mx > best.conf:
            best = Match(float(mx), int(loc[0]), int(loc[1]), tw, th, float(f))
    return best


def locate_cached(screen_gray, tpl_gray, last_scale: float | None, good: float) -> Match | None:
    """Otimizacao p/ o loop: tenta primeiro escalas perto da ultima que funcionou.

    Se achar com conf >= good, retorna na hora (rapido). Senao, faz a busca cheia.
    """
    if last_scale is not None:
        near = [s for s in DEFAULT_SCALES if abs(s - last_scale) <= 0.16] or [last_scale]
        m = locate(screen_gray, tpl_gray, near)
        if m is not None and m.conf >= good:
            return m
    return locate(screen_gray, tpl_gray)
