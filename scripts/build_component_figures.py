# -*- coding: utf-8 -*-
"""原書 p.2「The Bits」の一覧図から、コンポーネントを1点ずつ切り出す。

    python3 scripts/build_component_figures.py

出力: figures/comp-*.png（ルールブック §3 のグリッド表示で使う）

座標は figures/fig-components.jpg（1400×1528）を 1000px 幅に縮めたときの値で書いてある。
図を差し替えたときは SCALE と BOXES を見直すこと。
物資5個のキューブだけは一覧図では小さすぎるので、figures/icons/ の素材を使う。
"""
import os, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "figures", "fig-components.jpg")
IC = os.path.join(ROOT, "figures", "icons")
FIG = os.path.join(ROOT, "figures")

SCALE = 1.4          # 1000px 幅の座標 → 実寸 1400px
OUT_H = 260          # 出力の高さの目安（横長のものは幅で決まる）
PARCH = "rgb(192,184,148)"   # 原書 p.2 の羊皮紙色。切り出しと物資キューブの背景を揃える

# name: (x0, y0, x1, y1)  ※1000px 幅での座標
BOXES = {
    "board":        (40,  74, 340, 200),
    "action-cards": (40, 244, 124, 362),
    "writ-cards":   (40, 434, 124, 554),
    "pawns":        (36, 600, 188, 652),
    "discs":        (36, 700, 120, 750),
    "influence":    (36, 806, 150, 846),
    "tiles":        (36, 900, 190, 972),
    "vessels":     (380,  80, 614, 140),
    "locations":   (380, 200, 616, 260),
    "seals":       (378, 322, 464, 366),
    "targets":     (380, 400, 420, 442),
    "epoch":       (380, 484, 420, 524),
    "start":       (380, 564, 414, 632),
    "shillings":   (378, 672, 496, 730),
    "die":         (380, 800, 430, 852),
    "pouch":       (686,  76, 774, 162),
    "haversack":   (684, 556, 796, 638),
    "monsters":    (684, 666, 876, 788),
    "rulebooks":   (684, 846, 874, 962),
}

# 物資は icons/ の素材から（一覧図では 18px しかなく使えない）
GOODS = {
    "goods-food":      "cube-food",
    "goods-wood":      "cube-wood",
    "goods-iron":      "cube-iron",
    "goods-sulfur":    "cube-sulfur",
    "goods-saltpeter": "icon-cube-white",
}


def crop(name, box):
    x0, y0, x1, y1 = [int(v * SCALE) for v in box]
    dst = os.path.join(FIG, "comp-%s.png" % name)
    subprocess.run(["magick", SRC,
                    "-crop", "%dx%d+%d+%d" % (x1 - x0, y1 - y0, x0, y0), "+repage",
                    "-filter", "Lanczos", "-resize", "x%d>" % (OUT_H * 2),
                    "-bordercolor", PARCH, "-border", "8x8",
                    dst], check=True)
    return dst


def from_icon(name, src):
    dst = os.path.join(FIG, "comp-%s.png" % name)
    # 一覧図から切り出したものと同じ背景に載せて、並べたときの見た目を揃える
    subprocess.run(["magick", os.path.join(IC, src + ".png"),
                    "-filter", "Lanczos", "-resize", "x88",
                    "-background", PARCH, "-alpha", "remove", "-alpha", "off",
                    "-gravity", "center", "-extent", "190x150",
                    dst], check=True)
    return dst


if __name__ == "__main__":
    made = []
    for n, b in BOXES.items():
        made.append(crop(n, b))
    for n, s in GOODS.items():
        made.append(from_icon(n, s))
    total = sum(os.path.getsize(p) for p in made)
    print("切り出し: %d 点 / %d KB" % (len(made), total // 1024))
    for p in sorted(made):
        size = subprocess.run(["magick", "identify", "-format", "%wx%h", p],
                              capture_output=True, text=True).stdout
        print("  %-28s %s" % (os.path.basename(p), size))
