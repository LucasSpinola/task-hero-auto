"""Tracker, Engine (loop principal) e Hotkeys."""
from __future__ import annotations

import threading
import time

import actions
import ui
import vision
from assets import Assets


class Tracker:
    """Acompanha a regiao/escala do jogo (ancorado no botao amarelo)."""

    def __init__(self, A: Assets):
        self.A = A
        self.scale: float | None = None
        self.roi: tuple[int, int, int, int] | None = None     # gameplay (trigger rapido)
        self.region: tuple[int, int, int, int] | None = None  # monitor do jogo (store_flow)

    def acquire(self, scr: "vision.Screen") -> bool:
        m = vision.locate(scr.gray, self.A.btn_open)
        if m is None or m.conf < actions.OPEN_CONF:
            self.scale = self.roi = self.region = None
            return False
        self.scale = m.scale
        self.region = vision.region_for_point(scr, m.cx, m.cy)
        off = self.A.layout["scene_from_btn_open"]
        f = m.scale
        H, W = scr.gray.shape[:2]
        l = max(0, int(m.cx + f * off[0]) - 18)
        t = max(0, int(m.cy + f * off[1]) - 18)
        r = min(W, int(m.cx + f * off[2]) + 18)
        b = min(H, int(m.cy + f * off[3]) + 18)
        if r - l < 20 or b - t < 20:
            self.roi = None
            return False
        self.roi = (l, t, r, b)
        return True

    def inven_full_conf(self, scr: "vision.Screen") -> float | None:
        if self.roi is None:
            return None
        l, t, r, b = self.roi
        sub = scr.gray[t:b, l:r]
        mb = vision.locate(sub, self.A.btn_open, vision.near(self.scale))
        if mb is None or mb.conf < actions.OPEN_CONF:
            self.roi = None
            return None
        mi = vision.locate(sub, self.A.inven_full, vision.near(self.scale))
        return 0.0 if mi is None else mi.conf


class Engine:
    """Loop de deteccao. Os controles sao Events (ligar/desligar ao vivo)."""

    def __init__(self, cfg, A: Assets):
        self.cfg = cfg
        self.A = A
        self.tr = Tracker(A)
        self.active = threading.Event()    # mestre: Iniciar/Pausar (comeca pausado)
        self.running = threading.Event()   # auto-guardar (INVEN FULL)
        self.chests = threading.Event()    # auto-abrir baus
        self.synth = threading.Event()     # auto-sintese (cubo) periodica
        self.quit = threading.Event()
        self.status = "Pausado"
        self._armed = True
        self._last_action = 0.0
        self._last_synth = 0.0
        self._last_warn = 0.0
        self._last_user_move = 0.0   # quando o usuario mexeu o mouse pela ultima vez
        self._in_flow = False        # True enquanto o macro clica (ignora moves dele)

    def click_chests(self, scr) -> int:
        if self.tr.roi is None:
            return 0
        actions.reset_macro_pos()
        l, t, r, b = self.tr.roi
        sub = scr.gray[t:b, l:r]
        n = 0
        for name, tpl in (("azul", self.A.chest_blue), ("marrom", self.A.chest_brown),
                          ("boss", self.A.chest_boss)):
            if tpl is None:
                continue
            m = vision.locate(sub, tpl, vision.near(self.tr.scale))
            if m is not None and m.conf >= self.cfg.chest_threshold:
                ax, ay = scr.to_abs(l + m.cx, t + m.cy)
                actions._click_abs(ax, ay, self.cfg.click_backend)
                n += 1
                time.sleep(0.15)
        return n

    # ---- monitor de mouse (pausa quando o usuario mexe) ----
    def _on_move(self, x, y):
        if self._in_flow:
            return
        lp = actions._LAST_MACRO_POS
        if lp is not None and abs(x - lp[0]) <= actions.MOUSE_TOL and abs(y - lp[1]) <= actions.MOUSE_TOL:
            return  # foi onde o macro deixou o mouse, nao conta como usuario
        self._last_user_move = time.time()

    def _start_mouse(self):
        try:
            from pynput import mouse
        except Exception:
            return None
        l = mouse.Listener(on_move=self._on_move)
        l.start()
        return l

    def _user_busy(self) -> bool:
        return (time.time() - self._last_user_move) < self.cfg.pause_on_mouse_s

    def _tick(self) -> None:
        if not self.active.is_set():
            self.status = "Pausado"
            return
        # pausa enquanto o usuario esta mexendo o mouse, volta sozinho quando parar
        if self._user_busy():
            self.status = "Pausado, mouse em uso"
            return

        scr = vision.grab_screen()
        if self.tr.roi is None:
            self.tr.acquire(scr)

        conf = self.tr.inven_full_conf(scr)
        present = conf is not None and conf >= self.cfg.trigger_threshold

        if conf is None:
            self.status = "Procurando o jogo na tela..."
        elif present:
            self.status = "Inventário cheio!"
        else:
            self.status = "Monitorando o jogo..."

        # F6: auto-sintese (cubo) a cada synth_interval_min
        if self.synth.is_set():
            now = time.time()
            if now - self._last_synth >= self.cfg.synth_interval_min * 60:
                ui.log("Síntese: abrindo o cubo...", ui.MAGENTA)
                self.status = "Sintetizando no cubo..."
                self._in_flow = True
                try:
                    actions.synth_flow(self.A, self.cfg, scale_hint=self.tr.scale,
                                       search_region=self.tr.region, verbose=False)
                    self._last_synth = time.time()
                    self.tr.roi = None
                except actions.UserBusy:
                    self.status = "Pausado, mouse em uso"
                    self._last_user_move = time.time()
                except Exception as e:
                    ui.err(f"síntese interrompida: {e!r}")
                    self._last_synth = time.time()
                finally:
                    self._in_flow = False
                return

        # F7: auto-abrir baus (independente do guardar)
        if self.chests.is_set():
            self._in_flow = True
            try:
                n = self.click_chests(scr)
                if n:
                    ui.log(f"Baú coletado ({n}).", ui.CYAN)
            except actions.UserBusy:
                self.status = "Pausado, mouse em uso"
                self._last_user_move = time.time()
            finally:
                self._in_flow = False

        # F8: auto-guardar
        if self.running.is_set():
            now = time.time()
            if present and self._armed and (now - self._last_action) >= self.cfg.cooldown_s:
                ui.log("Inventário cheio, guardando no baú...", ui.YELLOW)
                self.status = "Guardando no baú..."
                self._in_flow = True
                try:
                    ok = actions.store_flow(self.A, self.cfg, scale_hint=self.tr.scale,
                                            search_region=self.tr.region, verbose=False)
                    if ok:
                        ui.good("Itens guardados no baú.")
                    else:
                        ui.err("Não consegui guardar (o jogo está visível?).")
                    self._last_action = time.time()
                    self._armed = False
                    self.tr.roi = None
                except actions.UserBusy:
                    self.status = "Pausado, mouse em uso"   # tenta de novo depois, nao desarma
                    self._last_user_move = time.time()
                except Exception as e:
                    ui.err(f"guardar interrompido: {e!r}")
                    self._last_action = time.time()
                    self.tr.roi = None
                finally:
                    self._in_flow = False
            elif not present:
                self._armed = True

    def loop(self) -> None:
        listener = self._start_mouse()
        try:
            while not self.quit.is_set():
                t0 = time.time()
                try:
                    self._tick()
                except Exception as e:
                    print(f"[erro no loop] {e!r}")
                    time.sleep(0.5)
                dt = time.time() - t0
                rem = self.cfg.poll_interval_s - dt
                if rem > 0:
                    time.sleep(rem)
        finally:
            if listener is not None:
                listener.stop()


def _norm_key(key) -> str:
    try:
        return key.char.lower()
    except AttributeError:
        return key.name.lower()


class Hotkeys:
    """Teclas globais que ligam/desligam os Events do Engine."""

    def __init__(self, engine: Engine, toggle="f8", chests="f7", synth="f6", quit="f9"):
        self.e = engine
        self.toggle = toggle.lower()
        self.chests_k = chests.lower()
        self.synth_k = synth.lower()
        self.quit_k = quit.lower()
        self._l = None

    def _on_press(self, key):
        k = _norm_key(key)
        if k == self.toggle:
            ev = self.e.running
            ev.clear() if ev.is_set() else ev.set()
            print(("\n" + ui.tag(" GUARDAR: ON ", ui.GREEN)) if ev.is_set()
                  else ("\n" + ui.tag(" GUARDAR: OFF ", ui.RED)))
        elif k == self.chests_k:
            ev = self.e.chests
            ev.clear() if ev.is_set() else ev.set()
            print(("\n" + ui.tag(" BAUS: ON ", ui.CYAN)) if ev.is_set()
                  else ("\n" + ui.tag(" BAUS: OFF ", ui.RED)))
        elif k == self.synth_k:
            ev = self.e.synth
            ev.clear() if ev.is_set() else ev.set()
            print(("\n" + ui.tag(" SINTESE: ON ", ui.MAGENTA)) if ev.is_set()
                  else ("\n" + ui.tag(" SINTESE: OFF ", ui.RED)))
        elif k == self.quit_k:
            self.e.quit.set()
            return False
        return None

    def start(self):
        from pynput import keyboard

        self._l = keyboard.Listener(on_press=self._on_press)
        self._l.start()

    def stop(self):
        if self._l is not None:
            self._l.stop()
