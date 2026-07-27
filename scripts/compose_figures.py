# -*- coding: utf-8 -*-
"""figures/icons/ の素材を合成して、各ドキュメントの画像スロットを埋める。

    python3 scripts/compose_figures.py

原書PDF由来のため解像度は高くありません（元は75 ppi）。実物の写真が用意できたら、
同じファイル名で上書きすれば差し替わります。対応表は figures/MANIFEST.md を参照。
"""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IC = os.path.join(ROOT, "figures", "icons")
FIG = os.path.join(ROOT, "figures")


def ic(name):
    return os.path.join(IC, name + ".png")


def run(args):
    subprocess.run(["magick"] + args, check=True, capture_output=True)


def single(src, dst, width=None):
    """1枚をそのまま白背景のJPEGに。"""
    a = [ic(src)]
    if width:
        a += ["-resize", "%dx>" % width]
    a += ["-background", "white", "-alpha", "remove", "-alpha", "off",
          "-quality", "90", os.path.join(FIG, dst)]
    run(a)


def row(srcs, dst, height=200, gap=26):
    """複数を横一列に並べる。高さを揃えて連結し、間に一定の余白を入れる。"""
    a = []
    for s in srcs:
        # 各画像の左右に余白を足してから連結する（-splice は画像を割ってしまうので border を使う）
        a += ["(", ic(s), "-resize", "x%d" % height,
              "-bordercolor", "none", "-border", "%dx0" % (gap // 2), ")"]
    a += ["-background", "white", "-gravity", "center", "+append",
          "-alpha", "remove", "-alpha", "off", "-bordercolor", "white",
          "-border", "12x12", "-quality", "90", os.path.join(FIG, dst)]
    run(a)


def grid(srcs, dst, cols, height=260, gap=18):
    a = ["montage"] + [ic(s) for s in srcs] + \
        ["-tile", "%dx" % cols, "-geometry", "x%d+%d+%d" % (height, gap // 2, gap // 2),
         "-background", "white", "-quality", "90", os.path.join(FIG, dst)]
    run(a)


JOBS = [
    # --- リファレンス ---
    ("locations-4.jpg",     lambda: single("icon-locations-4", "locations-4.jpg", 1100)),
    ("goods-5.jpg",         lambda: row(["cube-food", "cube-wood", "cube-iron",
                                         "cube-sulfur", "icon-cube-white"], "goods-5.jpg", 150)),
    ("tokens.jpg",          lambda: row(["icon-shillings", "icon-kings-seal", "icon-rosary-bead",
                                         "icon-archery-target", "art-pawn-piece"], "tokens.jpg", 190)),
    ("landscapes-4.jpg",    lambda: row(["icon-landscape-orchard", "art-archery-butt",
                                         "icon-landscape-silver-mine", "icon-landscape-sulfur-mine"],
                                        "landscapes-4.jpg", 210)),
    ("vessels-routes.jpg",  lambda: row(["art-ship", "art-flying-machine", "icon-vessels-3",
                                         "icon-routes-3"], "vessels-routes.jpg", 230)),
    ("monsters-2.jpg",      lambda: single("art-monsters-2", "monsters-2.jpg", 900)),
    ("writ-mandates.jpg",   lambda: grid(["card-mandate-%02d" % i for i in range(1, 9)],
                                         "writ-mandates.jpg", 4, 300)),
    ("writ-charters.jpg",   lambda: grid(["card-charter-%02d" % i for i in range(1, 10)],
                                         "writ-charters.jpg", 5, 300)),
    ("guild-knight.jpg",    lambda: single("board-knight-guild", "guild-knight.jpg", 1100)),
    ("guild-merchant.jpg",  lambda: single("board-merchant-guild", "guild-merchant.jpg", 1100)),
    ("roles-placement.jpg", lambda: single("board-detail-pawns", "roles-placement.jpg", 1100)),
    # --- はじめてガイド ---
    ("board-overview.jpg",  lambda: single("art-board-full", "board-overview.jpg", 1100)),
    ("beginner-ruler.jpg",  lambda: single("board-detail-pawns", "beginner-ruler.jpg", 1100)),
    ("cards-11.jpg",        lambda: grid(["card-action-%02d" % i for i in range(1, 12)],
                                         "cards-11.jpg", 6, 260)),
]

if __name__ == "__main__":
    made = []
    for name, fn in JOBS:
        try:
            fn()
            p = os.path.join(FIG, name)
            size = subprocess.run(["magick", "identify", "-format", "%wx%h", p],
                                  capture_output=True, text=True).stdout
            made.append((name, size, os.path.getsize(p) // 1024))
        except subprocess.CalledProcessError as e:
            print("失敗:", name, e.stderr.decode()[:120])
    for n, s, k in made:
        print("  %-22s %-12s %4d KB" % (n, s, k))
    print("配置: %d 点" % len(made))
