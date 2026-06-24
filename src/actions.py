"""Abrir inventario/stash/cubo e executar guardar e sintese."""
from __future__ import annotations

import os
import time

import cv2
import numpy as np
import pyautogui

import ui
import vision
from assets import Assets
from config import Config

pyautogui.FAILSAFE = True       # jogar o mouse no canto sup-esq aborta
pyautogui.PAUSE = 0.04

MOUSE_TOL = 8        # px: se o mouse saiu de onde o macro deixou, foi o usuario

OPEN_CONF = 0.58     # confianca minima p/ clicar num botao (amarelo / bau)
BANNER_CONF = 0.65   # confianca minima p/ o banner do STASH (durante o guardar)
STATE_CONF = 0.72    # confianca p/ DECIDIR que algo "ja esta aberto" (mais rigoroso)
OPEN_SETTLE_S = 1.0  # espera o painel abrir/assentar

# raridade do material, do mais fraco pro mais forte (nivel = indice na lista).
RARITY_ORDER = ["cinza", "verde", "azul", "amarelo", "vermelho", "roxo"]


def _hue_rarity(h: float):
    """Matiz (HSV do OpenCV, 0..179) -> (nome, nivel). Azul medido ao vivo ~106."""
    if h <= 8 or h >= 166:
        return ("vermelho", 4)
    if h <= 34:
        return ("amarelo", 3)
    if h <= 85:
        return ("verde", 1)
    if h <= 129:
        return ("azul", 2)
    return ("roxo", 5)   # 130..165


class UserBusy(Exception):
    """O usuario mexeu o mouse durante a automacao: pausar (sem desligar)."""


_LAST_MACRO_POS = None   # ultima posicao onde o macro deixou o mouse


def reset_macro_pos() -> None:
    """Zera a referencia (chamar no inicio de cada fluxo)."""
    global _LAST_MACRO_POS
    _LAST_MACRO_POS = None


def _click_abs(x: int, y: int, backend: str) -> None:
    global _LAST_MACRO_POS
    # se entre um clique e outro o mouse saiu de onde o macro deixou, foi o usuario
    if _LAST_MACRO_POS is not None:
        cur = pyautogui.position()
        if abs(cur[0] - _LAST_MACRO_POS[0]) > MOUSE_TOL or abs(cur[1] - _LAST_MACRO_POS[1]) > MOUSE_TOL:
            raise UserBusy()
    try:
        if backend == "pydirectinput":
            import pydirectinput

            pydirectinput.moveTo(int(x), int(y))
            pydirectinput.click()
        else:
            pyautogui.click(int(x), int(y))
    except pyautogui.FailSafeException:
        raise UserBusy()
    _LAST_MACRO_POS = pyautogui.position()


def _save_shot(scr: "vision.Screen", pt, label: str, shots_dir, idx: int) -> None:
    if not shots_dir or scr.bgr is None:
        return
    img = scr.bgr.copy()
    x, y = int(pt[0]), int(pt[1])
    cv2.circle(img, (x, y), 9, (0, 0, 255), 2)
    cv2.putText(img, label, (x + 10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    h, w = img.shape[:2]
    crop = img[max(0, y - 170):min(h, y + 170), max(0, x - 240):min(w, x + 240)]
    cv2.imwrite(os.path.join(shots_dir, f"{idx:02d}_{label}.png"), crop)


def _has_tab(A: Assets, tab_key: str, scale_hint, search_region) -> bool:
    """Existe a aba `tab_key` do STASH? (slot quente/marrom = aba; cinza = botao '+')."""
    off = A.layout["offsets_from_banner_center"].get(tab_key)
    if off is None:
        return False
    s = vision.grab_screen(color=True)
    if s.bgr is None:
        return False
    g = s.gray
    if search_region:
        l, t, r, b = search_region
        m = vision.locate(g[t:b, l:r], A.stash_banner, vision.near(scale_hint))
        if m is not None:
            m.left += l
            m.top += t
    else:
        m = vision.locate(g, A.stash_banner, vision.near(scale_hint))
    if m is None or m.conf < BANNER_CONF:
        return False
    ox, oy = off
    x, y = int(m.cx + m.scale * ox), int(m.cy + m.scale * oy)
    h, w = s.bgr.shape[:2]
    if not (12 <= x < w - 12 and 12 <= y < h - 12):
        return False
    p = s.bgr[y - 12:y + 12, x - 12:x + 12].reshape(-1, 3).mean(0)
    return (p[2] - p[0]) > 25  # aba e quente (R>B); o "+" e cinza


def store_flow(A: Assets, cfg: Config, scale_hint: float | None = None,
               search_region=None, verbose: bool = False, shots_dir: str | None = None) -> bool:
    """Garante o STASH aberto, guarda em cada aba e fecha. True se concluiu."""
    reset_macro_pos()
    wait = cfg.ui_wait_ms / 1000.0
    backend = cfg.click_backend
    shots = bool(shots_dir)
    if shots_dir:
        os.makedirs(shots_dir, exist_ok=True)
    idx = [0]

    def _locate(gray, tpl, scales):
        if search_region:
            l, t, r, b = search_region
            m = vision.locate(gray[t:b, l:r], tpl, scales)
            if m is not None:
                m.left += l
                m.top += t
            return m
        return vision.locate(gray, tpl, scales)

    def _safe(scr, ax, ay) -> bool:
        if search_region:
            l, t, r, b = search_region
            ix, iy = ax - scr.left, ay - scr.top
            return l + 2 <= ix <= r - 2 and t + 2 <= iy <= b - 2
        return True

    def do_click(scr, pt_img, label) -> bool:
        ax, ay = scr.to_abs(*pt_img)
        if not _safe(scr, ax, ay):
            ui.err(f"{label}: alvo ({ax},{ay}) fora do monitor do jogo -- ignorado (falso positivo).")
            return False
        idx[0] += 1
        _save_shot(scr, pt_img, label, shots_dir, idx[0])
        if verbose:
            ui.step(f"{label}  @ ({ax}, {ay})")
        _click_abs(ax, ay, backend)
        return True

    def find(tpl, conf=OPEN_CONF):
        s = vision.grab_screen(color=shots)
        m = _locate(s.gray, tpl, vision.near(scale_hint))
        if m is None or m.conf < conf:
            m = _locate(s.gray, tpl, None)
        return s, m

    def banner():
        s = vision.grab_screen(color=shots)
        return s, _locate(s.gray, A.stash_banner, None)

    def hero():
        s = vision.grab_screen(color=shots)
        return s, _locate(s.gray, A.hero_banner, None)

    def wait_for(fn, timeout=3.0, conf=STATE_CONF):
        """Fica re-capturando ate o painel-alvo (fn->(scr,match)) aparecer."""
        end = time.time() + timeout
        scr, m = fn()
        while (m is None or m.conf < conf) and time.time() < end:
            time.sleep(0.3)
            scr, m = fn()
        return scr, m

    scr, mb = banner()
    if mb is not None and mb.conf >= STATE_CONF:
        if verbose:
            ui.step(f"STASH ja aberto (conf={mb.conf:.2f})")
    else:
        scr, mh = hero()
        if mh is None or mh.conf < STATE_CONF:
            opened = False
            for attempt in range(2):
                scr, mo = find(A.btn_open)
                if mo is None or mo.conf < OPEN_CONF:
                    ui.err(f"nao achei o botao de abrir inventario (conf={0 if mo is None else mo.conf:.2f}).")
                    return False
                if verbose:
                    ui.step(f"abrir inventario (conf={mo.conf:.2f})" + ("" if attempt == 0 else " [retry]"))
                do_click(scr, (mo.cx, mo.cy), "abrir_inv" if attempt == 0 else "abrir_inv_retry")
                scr, mh = wait_for(hero, 3.0)
                if mh is not None and mh.conf >= STATE_CONF:
                    opened = True
                    break
            if not opened:
                ui.err(f"abri o inventario mas o painel HERO nao apareceu (conf={0 if mh is None else mh.conf:.2f}).")
                return False

        stash_ok = False
        for attempt in range(2):
            if verbose:
                ui.step(f"inventario aberto (HERO conf={mh.conf:.2f}) -> abrindo STASH"
                        + ("" if attempt == 0 else " [retry]"))
            do_click(scr, A.chest_point(mh), "abrir_stash" if attempt == 0 else "abrir_stash_retry")
            scr, mb = wait_for(banner, 3.0)
            if mb is not None and mb.conf >= STATE_CONF:
                stash_ok = True
                break
            scr, mh2 = hero()
            if mh2 is not None and mh2.conf >= STATE_CONF:
                mh = mh2
        if not stash_ok:
            ui.err(f"cliquei o bau mas o STASH nao abriu (conf={0 if mb is None else mb.conf:.2f}).")
            return False

    tabs = list(cfg.tabs)
    for tk in ("tab3", "tab4", "tab5"):
        if tk in tabs:
            continue
        if _has_tab(A, tk, scale_hint, search_region):
            tabs.append(tk)
            if verbose:
                ui.step(f"aba {tk[-1]} do STASH detectada -> vou guardar nela tambem")
        else:
            break  # as abas abrem em ordem; se a proxima nao existe, as seguintes tambem nao

    for tab in tabs:
        scr, mb = banner()
        if mb is None or mb.conf < BANNER_CONF:
            ui.err(f"painel STASH nao encontrado p/ {tab} (conf={0 if mb is None else mb.conf:.2f}).")
            return False
        do_click(scr, A.stash_points(mb)[tab], tab)
        time.sleep(wait)

        scr, mb = banner()
        if mb is None or mb.conf < BANNER_CONF:
            ui.err(f"painel STASH sumiu antes do Guardar (conf={0 if mb is None else mb.conf:.2f}).")
            return False
        do_click(scr, A.stash_points(mb)["guardar_tudo"], f"guardar_{tab}")
        time.sleep(wait)

    scr, mb = banner()
    if mb is not None and mb.conf >= BANNER_CONF:
        do_click(scr, A.stash_points(mb)["close"], "fechar_stash")
        time.sleep(0.2)
    return True


def _create_bgr(crt_img):
    """Cor media (B,G,R) do botao 'criar'. Azul (ativo) = B alto e B-R grande."""
    s = vision.grab_screen(color=True)
    x, y = int(crt_img[0]), int(crt_img[1])
    h, w = s.bgr.shape[:2]
    if not (12 <= x < w - 12 and 8 <= y < h - 8):
        return (0.0, 0.0, 0.0)
    patch = s.bgr[y - 8:y + 8, x - 12:x + 12].reshape(-1, 3).mean(0)
    return (float(patch[0]), float(patch[1]), float(patch[2]))


def _create_is_blue(crt_img) -> bool:
    b, g, r = _create_bgr(crt_img)
    return (b - r) > 20


def _grid_material(A, mc):
    """Classifica a raridade pela COR DE FUNDO da celula (nao pelo sprite do item).

    A raridade e o fundo da celula; o desenho do item fica no centro e nao conta.
    Por isso a leitura usa um ANEL ao redor do centro: fundo cinza/branco (saturacao
    baixa) = comum; fundo colorido = pela matiz. Retorna (label, nivel), nivel = indice
    em RARITY_ORDER (0=cinza .. 5=roxo), ou (label, -1) se a grade estiver vazia.
    """
    g = A.layout.get("cube_grid")
    if not g:
        return ("?", 0)
    s = vision.grab_screen(color=True)
    if s.bgr is None:
        return ("?", 0)
    hsv = cv2.cvtColor(s.bgr, cv2.COLOR_BGR2HSV)
    H, W = hsv.shape[:2]
    f = mc.scale
    r_out = max(10, int(20 * f))   # meia-celula (pega o fundo)
    r_in = max(6, int(12 * f))     # exclui o sprite central
    gray_votes = 0
    hues = []
    filled = 0
    for oy in g["rows"]:
        for ox in g["cols"]:
            x, y = int(mc.cx + f * ox), int(mc.cy + f * oy)
            if not (r_out <= x < W - r_out and r_out <= y < H - r_out):
                continue
            blk = hsv[y - r_out:y + r_out, x - r_out:x + r_out]
            mask = np.ones(blk.shape[:2], dtype=bool)
            c = r_out - r_in
            mask[c:-c, c:-c] = False           # tira o miolo (onde fica o sprite)
            ring = blk[mask]
            bright = ring[ring[:, 2] > 45]      # ignora os separadores escuros
            if len(bright) < 0.2 * len(ring):
                continue                         # celula vazia
            filled += 1
            sat = bright[bright[:, 1] > 60]
            if len(sat) < 0.30 * len(bright):
                gray_votes += 1                  # fundo sem cor = comum (cinza)
            else:
                hues.append(float(np.median(sat[:, 0])))
    if filled == 0:
        return ("vazio", -1)
    if gray_votes >= len(hues):                  # maioria dos fundos sem cor
        return ("cinza", 0)
    h = float(np.median(hues))
    name, level = _hue_rarity(h)
    return (f"{name} (H{h:.0f})", level)


def synth_flow(A, cfg, scale_hint=None, search_region=None, verbose=False, shots_dir=None) -> bool:
    """Abre o CUBE, preenche e cria so ate a raridade escolhida (cfg.synth_max_rarity).
    Apos cada item, tira o resultado do centro do cubo antes de re-preencher, e fecha no fim."""
    shots = bool(shots_dir)
    if shots_dir:
        os.makedirs(shots_dir, exist_ok=True)
    idx = [0]
    L = A.layout
    reset_macro_pos()
    try:
        max_level = RARITY_ORDER.index(str(cfg.synth_max_rarity).lower())
    except ValueError:
        max_level = RARITY_ORDER.index("azul")

    def gl(tpl, scales):
        s = vision.grab_screen(color=shots)
        if search_region:
            l, t, r, b = search_region
            m = vision.locate(s.gray[t:b, l:r], tpl, scales)
            if m is not None:
                m.left += l
                m.top += t
        else:
            m = vision.locate(s.gray, tpl, scales)
        return s, m

    def find(tpl, conf=OPEN_CONF):
        s, m = gl(tpl, vision.near(scale_hint))
        if m is None or m.conf < conf:
            s, m = gl(tpl, None)
        return s, m

    def wait(tpl, timeout=3.0, conf=STATE_CONF):
        end = time.time() + timeout
        s, m = find(tpl, conf)
        while (m is None or m.conf < conf) and time.time() < end:
            time.sleep(0.3)
            s, m = find(tpl, conf)
        return s, m

    def click(s, pt, label):
        idx[0] += 1
        _save_shot(s, pt, label, shots_dir, idx[0])
        ax, ay = s.to_abs(*pt)
        if verbose:
            ui.step(f"{label} @ ({ax},{ay})")
        _click_abs(ax, ay, cfg.click_backend)

    def close_cube():
        s2, mc2 = find(A.cube_banner, STATE_CONF)
        if mc2 is not None and mc2.conf >= STATE_CONF:
            f2 = mc2.scale
            click(s2, (mc2.cx + f2 * L["cube_close_from_banner"][0],
                       mc2.cy + f2 * L["cube_close_from_banner"][1]), "fechar_cubo")
            time.sleep(0.4)

    def ensure_cube():
        """Garante a janela CUBE aberta. Retorna (scr, match) ou (scr, None)."""
        s2, mc2 = find(A.cube_banner, STATE_CONF)
        if mc2 is not None and mc2.conf >= STATE_CONF:
            if verbose:
                ui.step(f"cubo ja aberto (conf={mc2.conf:.2f})")
            return s2, mc2
        s2, mh = find(A.hero_banner, STATE_CONF)
        if mh is None or mh.conf < STATE_CONF:
            opened = False
            for attempt in range(2):
                s2, mo = find(A.btn_open)
                if mo is None or mo.conf < OPEN_CONF:
                    ui.err("sintese: nao achei o botao de abrir inventario.")
                    return s2, None
                click(s2, (mo.cx, mo.cy), "abrir_inv" if attempt == 0 else "abrir_inv_retry")
                s2, mh = wait(A.hero_banner, 3.0)
                if mh is not None and mh.conf >= STATE_CONF:
                    opened = True
                    break
            if not opened:
                ui.err("sintese: inventario nao abriu.")
                return s2, None
        off = L["cube_from_hero_center"]
        for attempt in range(2):
            s2, mh2 = find(A.hero_banner, STATE_CONF)
            if mh2 is not None and mh2.conf >= STATE_CONF:
                mh = mh2
            click(s2, (mh.cx + mh.scale * off[0], mh.cy + mh.scale * off[1]),
                  "abrir_cubo" if attempt == 0 else "abrir_cubo_retry")
            s2, mc2 = wait(A.cube_banner, 3.0)
            if mc2 is not None and mc2.conf >= STATE_CONF:
                return s2, mc2
        ui.err("sintese: a janela CUBE nao abriu.")
        return s2, None

    def clear_center(s2, mc2):
        """Tira o item que fica no centro do cubo (resultado de uma sintese) e dá foco."""
        grid = L.get("cube_grid")
        if not grid or mc2 is None:
            return
        f2 = mc2.scale
        cox, coy = grid["cols"][1], grid["rows"][1]
        click(s2, (mc2.cx + f2 * cox, mc2.cy + f2 * coy), "tirar_centro")
        time.sleep(0.5)

    s, mc = ensure_cube()
    if mc is None:
        return False
    if verbose:
        ui.step(f"CUBE aberto (conf={mc.conf:.2f})")
    clear_center(s, mc)   # ja-aberto pode ter item no centro; comeca limpo e da foco

    made = 0
    stop_label = None
    for _ in range(40):
        s, mc = find(A.cube_banner, STATE_CONF)
        if mc is None or mc.conf < STATE_CONF:
            s, mc = ensure_cube()
        if mc is None:
            break
        f = mc.scale
        fill = (mc.cx + f * L["cube_fill_from_banner"][0], mc.cy + f * L["cube_fill_from_banner"][1])
        crt = (mc.cx + f * L["cube_create_from_banner"][0], mc.cy + f * L["cube_create_from_banner"][1])
        ready = False
        for fa in range(3):
            click(s, fill, "preencher" if fa == 0 else "preencher_retry")
            end = time.time() + 2.0
            while time.time() < end:
                time.sleep(0.3)
                if _create_is_blue(crt):
                    ready = True
                    break
            if ready:
                break
        if not ready:
            if verbose:
                b, g, r = _create_bgr(crt)
                ui.step(f"grade nao completou 9 (criar: B-R={b - r:.0f}) -> fim")
            break

        label, level = _grid_material(A, mc)
        if level < 0 or level > max_level:
            stop_label = label
            if verbose:
                ui.step(f"material {label} acima do limite ({cfg.synth_max_rarity}) -> nao vou sintetizar")
            break
        if verbose:
            ui.step(f"material {label} -> criar")
        click(s, crt, "criar")
        made += 1
        time.sleep(5.5)

        # o item criado fica no centro do cubo; tira ele de la antes de re-preencher,
        # senao o auto-preenchimento usaria a cor recem-criada.
        if L.get("cube_grid"):
            clear_center(s, mc)
        else:
            close_cube()
            s, mc = ensure_cube()

    close_cube()
    if stop_label:
        ui.good(f"Síntese: {made} item(ns) criado(s), parei no material {stop_label}.")
    else:
        ui.good(f"Síntese: {made} item(ns) criado(s).")
    return True
