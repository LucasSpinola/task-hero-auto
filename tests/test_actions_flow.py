"""Self-test do fluxo automatico (NAO toca no jogo).

Usa um screenshot estatico com o inventario aberto (STASH+HERO visiveis) e troca o
clique real por um gravador. Verifica:
  1) o bau DERIVADO do banner HERO (chest_point) cai sobre o bau real;
  2) com o STASH ja aberto, o store_flow pula a abertura e guarda:
     tab1 -> guardar -> tab2 -> guardar -> fechar (5 cliques).

Procura o screenshot em %TEMP%/now.png (ou cur_full.png / th_inv_full.png).
Roda:  python tests/test_actions_flow.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import cv2  # noqa: E402

import actions  # noqa: E402
import vision  # noqa: E402
from assets import Assets, UI_DIR  # noqa: E402
from config import Config  # noqa: E402

TMP = tempfile.gettempdir()
CANDIDATES = [os.path.join(TMP, n) for n in ("now2.png", "now.png", "cur_full.png", "th_inv_full.png")]


def main() -> int:
    img_path = next((p for p in CANDIDATES if os.path.exists(p)), None)
    if img_path is None:
        print(f"[skip] sem screenshot de referencia em {TMP} (now.png/cur_full.png)")
        return 0

    A = Assets()
    bgr = cv2.imread(img_path)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    mb = vision.locate(gray, A.stash_banner)
    mh = vision.locate(gray, A.hero_banner)
    if min(mb.conf, mh.conf) < 0.6:
        print(f"[skip] screenshot sem STASH/HERO abertos (stash={mb.conf:.2f} hero={mh.conf:.2f})")
        return 0

    # 1) bau derivado do HERO banner cai sobre o bau real
    chest_tpl = cv2.imread(str(UI_DIR / "btn_stash.png"), cv2.IMREAD_GRAYSCALE)
    if chest_tpl is not None:
        mc = vision.locate(gray, chest_tpl)
        dx, dy = A.chest_point(mh)
        err = abs(dx - mc.cx) + abs(dy - mc.cy)
        assert err <= 8, f"bau derivado {('%.0f' % dx, '%.0f' % dy)} != real {('%.0f' % mc.cx, '%.0f' % mc.cy)} (erro {err:.0f}px)"
        print(f"OK  bau derivado do HERO banner bate no real (erro {err:.0f}px)")

    # 2) STASH aberto -> store_flow pula abertura e guarda
    pts = A.stash_points(mb)
    exp = [pts["tab1"], pts["guardar_tudo"], pts["tab2"], pts["guardar_tudo"], pts["close"]]
    exp = [(x - 1920, y) for (x, y) in exp]

    clicks = []
    vision.grab_screen = lambda color=False: vision.Screen(gray, -1920, 0, bgr=bgr if color else None)
    actions._click_abs = lambda x, y, backend: clicks.append((x, y))

    cfg = Config()
    cfg.ui_wait_ms = 0
    cfg.tabs = ["tab1", "tab2"]

    ok = actions.store_flow(A, cfg, scale_hint=1.0, verbose=True)
    assert ok, "store_flow deveria concluir"
    assert len(clicks) == 5, f"STASH aberto -> esperava 5 cliques, veio {len(clicks)}: {clicks}"

    def close(a, b, tol=10):
        return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol

    labels = ["tab1", "guardar1", "tab2", "guardar2", "fechar_stash"]
    for got, want, lab in zip(clicks, exp, labels):
        assert close(got, (round(want[0]), round(want[1]))), f"{lab}: {got} != {want}"
    print("OK  STASH ja aberto: pulou abertura e guardou:")
    for lab, c in zip(labels, clicks):
        print(f"   {lab:14} {c}")
    print("RESULT: ALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
