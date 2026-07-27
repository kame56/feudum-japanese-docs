# -*- coding: utf-8 -*-
"""figures/nice/（Dized から取得した高解像度素材）を各ドキュメントのスロットへ配置する。

    python3 scripts/place_nice_figures.py

素材は figures/nice/ に原寸で置いたまま触らず、ここから figures/*.jpg を生成する。
原寸は 295×478 前後なので、印刷と Retina 表示に耐えるよう 2〜3 倍に拡大している。
対応表は figures/nice/CATALOG.md を参照。
"""
import os, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NICE = os.path.join(ROOT, "figures", "nice")
FIG = os.path.join(ROOT, "figures")
IC = os.path.join(FIG, "icons")

ACTIONS = ["migrate", "move", "influence", "improve", "explore", "harvest",
           "tax", "conquer", "defend", "repeat", "guild"]


def src(name):
    for ext in (".png", ".jpg"):
        p = os.path.join(NICE, name + ext)
        if os.path.exists(p):
            return p
    raise SystemExit("素材が見つかりません: " + name)


def run(args):
    subprocess.run(["magick"] + args, check=True)


def flat(a, dst, scale=2, quality=92):
    """1枚を拡大して白背景のJPEGにする。"""
    run([src(a), "-filter", "Lanczos", "-resize", "%d%%" % (scale * 100),
         "-background", "white", "-alpha", "remove", "-alpha", "off",
         "-quality", str(quality), os.path.join(FIG, dst)])


def row(names, dst, height, gap=30, scale=2):
    """横一列に並べる。高さを揃え、間に余白を入れる（-splice は画像を割るので border を使う）。"""
    a = []
    for n in names:
        a += ["(", src(n), "-filter", "Lanczos", "-resize", "x%d" % (height * scale),
              "-background", "white", "-alpha", "remove", "-alpha", "off",
              "-bordercolor", "white", "-border", "%dx0" % (gap * scale // 2), ")"]
    a += ["-background", "white", "-gravity", "center", "+append",
          "-bordercolor", "white", "-border", "%dx%d" % (10 * scale, 10 * scale),
          "-quality", "92", os.path.join(FIG, dst)]
    run(a)


def grid(names, dst, cols, height, scale=2):
    a = ["montage"] + [src(n) for n in names] + [
        "-tile", "%dx" % cols,
        "-geometry", "x%d+%d+%d" % (height * scale, 9 * scale, 9 * scale),
        "-background", "white", "-quality", "92", os.path.join(FIG, dst)]
    run(a)


def anatomy():
    """収穫カードを3倍に拡大し、左右の余白に番号を打って部位を示す。"""
    S, M = 3, 150                       # 拡大率 / 左右の余白
    W = 295 * S                          # 拡大後のカード幅
    # (番号, 余白側の中心x, y, 引出線の終点x)
    marks = [("1", M // 2,          99, M + 90),      # ギルドコストの紋章
             ("2", M + W + M // 2, 102, M + 700),     # アクション名
             ("3", M // 2,        400, M + 60),       # 通常アクションの効果
             ("4", M + W + M // 2, 1215, M + W - 40), # 上級ゲームの特殊能力
             ("5", M // 2,       1404, M + 60)]       # 各国語のアクション名
    draw = []
    for _, cx, y, tx in marks:
        draw += ["-stroke", "#8c2f24", "-strokewidth", "5",
                 "-draw", "line %d,%d %d,%d" % (cx, y, tx, y)]
    for n, cx, y, _ in marks:
        draw += ["-stroke", "none", "-fill", "#8c2f24",
                 "-draw", "circle %d,%d %d,%d" % (cx, y, cx, y - 42),
                 "-fill", "white", "-pointsize", "56", "-gravity", "none",
                 "-annotate", "+%d+%d" % (cx - 16, y + 20), n]
    run([src("action-harvest"), "-filter", "Lanczos", "-resize", "%d%%" % (S * 100),
         "-background", "white", "-alpha", "remove", "-alpha", "off",
         "-bordercolor", "white", "-border", "%dx0" % M] + draw +
        ["-quality", "92", os.path.join(FIG, "card-anatomy.jpg")])


JOBS = [
    # --- アクションカード11種（リファレンス各節） ---
] + [("card-%s.jpg" % a, (lambda a=a: flat("action-" + a, "card-%s.jpg" % a, 2)))
     for a in ACTIONS] + [
    # --- カードの見方（番号つき） ---
    ("card-anatomy.jpg", anatomy),
    # --- カード記号（確認できた4種） ---
    ("card-symbols.jpg", lambda: row(["sym-repeat-x2", "sym-no-repeat",
                                      "sym-not-last-card", "sym-either-or"],
                                     "card-symbols.jpg", 150)),
    # --- 地形4種（低解像度版を差し替え） ---
    ("landscapes-4.jpg", lambda: row(["tile-orchard-food", "tile-archery-butt-targets",
                                      "tile-silver-mine-shillings", "tile-sulfur-mine-sulfur"],
                                     "landscapes-4.jpg", 150)),
    # --- 資材キューブと拠点（低解像度版を差し替え） ---
    ("goods-cubes.jpg", lambda: flat("goods-cubes-and-location", "goods-cubes.jpg", 2)),
    # --- 王命状カードの例（指令と特許状） ---
    ("writ-examples.jpg", lambda: flat("writ-mandate-and-charter", "writ-examples.jpg", 1)),
    # --- 11枚一覧（はじめてガイド。低解像度版を差し替え） ---
    ("cards-11.jpg", lambda: grid(["action-" + a for a in ACTIONS], "cards-11.jpg", 6, 240)),
]

if __name__ == "__main__":
    for name, fn in JOBS:
        fn()
        p = os.path.join(FIG, name)
        size = subprocess.run(["magick", "identify", "-format", "%wx%h", p],
                              capture_output=True, text=True).stdout
        print("  %-22s %-12s %5d KB" % (name, size, os.path.getsize(p) // 1024))
    # 残りの記号は素材として icons/ に置く
    n = 0
    for f in sorted(os.listdir(NICE)):
        if f.startswith(("sym-", "tile-")):
            dst = os.path.join(IC, "nice-" + f)
            if not os.path.exists(dst):
                subprocess.run(["cp", os.path.join(NICE, f), dst], check=True)
            n += 1
    print("素材コピー: icons/nice-*  %d 点" % n)
    print("配置: %d 点" % len(JOBS))
