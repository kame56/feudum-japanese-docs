# -*- coding: utf-8 -*-
"""ルールブック §3 のコンポーネント一覧に並べる画像を作る。

    python3 scripts/build_component_figures.py

出力: figures/comp-*.png（透過PNG）

素材は原則 figures/icons/ の透過済みアイコン。
そこに見当たらないものだけ、原書 p.2 の一覧図（figures/fig-components.jpg）から
切り出して背景を抜く。

すべて 220×150 の透過キャンバスに載せて出力するので、並べたときの相対的な大きさが
素材の解像度どおりに保たれる（盤は大きく、キューブは小さく見える）。
"""
import os, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "figures", "fig-components.jpg")
IC = os.path.join(ROOT, "figures", "icons")
FIG = os.path.join(ROOT, "figures")

CANVAS = "220x150"

# 出力名: icons/ の素材名
# カタログの名前が実物と食い違っていたものは、目視で確認した対応に直してある。
ICONS = {
    "board":        "art-board-full",
    "vessels":      "icon-vessels-3",
    "locations":    "icon-locations-4",
    "action-cards": "card-action-09",
    "seals":        "icon-markers-2",        # 赤い王の印と緑のロザリオ玉
    "targets":      "icon-archery-target",
    "epoch":        "misc-190",              # 水色の丸いマーカー
    "writ-cards":   "card-writ-back",
    "pawns":        "art-pawn-faces-6",
    "discs":        "icon-shillings",        # 実物はプレイヤーディスクと代官ディスク
    "influence":    "icon-hexes-5",          # 黄色い六角柱5個
    "start":        "art-pawn-piece",        # 実物は開始プレイヤーマーカーの円柱
    "haversack":    "art-haversack-cloth",
    "shillings":    "icon-seal-and-bead",    # 実物は金貨と銀貨
    "monsters":     "art-monsters-2",
    "die":          "misc-152",              # 水色の進行ダイス
    "tiles":        "icon-epoch-1",          # 地域タイルと地形タイル
    "rulebooks":    "art-rulebook-cover",
    "goods-food":      "cube-food",
    "goods-wood":      "cube-wood",
    "goods-iron":      "cube-iron",
    "goods-sulfur":    "cube-sulfur",
    "goods-saltpeter": "icon-cube-white",
}

# 透過素材が見当たらないもの。原書 p.2 から切り出して背景を抜く。
# 座標は fig-components.jpg を 1000px 幅に縮めたときの値（実寸は 1.4 倍）。
CROPS = {
    "pouch": (686, 76, 774, 162),
}
SCALE = 1.4


def fit(args, dst):
    """透過を保ったまま 220×150 のキャンバス中央に載せる。"""
    subprocess.run(["magick"] + args + [
        "-filter", "Lanczos", "-resize", CANVAS + ">",
        "-background", "none", "-gravity", "center", "-extent", CANVAS,
        dst], check=True)


# 物資キューブは素材ごとに解像度が違う（硝石だけ2倍以上ある）ので、高さを揃えてから載せる
CUBE_H = 66


def from_icon(name, src):
    dst = os.path.join(FIG, "comp-%s.png" % name)
    args = [os.path.join(IC, src + ".png")]
    if name.startswith("goods-"):
        args += ["-filter", "Lanczos", "-resize", "x%d" % CUBE_H]
    fit(args, dst)
    return dst


def from_sheet(name, box):
    x0, y0, x1, y1 = [int(v * SCALE) for v in box]
    dst = os.path.join(FIG, "comp-%s.png" % name)
    # 四隅から羊皮紙色を塗りつぶして透過にし、余白を切り詰める
    args = [SRC, "-crop", "%dx%d+%d+%d" % (x1 - x0, y1 - y0, x0, y0), "+repage",
            "-alpha", "set", "-fuzz", "16%"]
    for x, y in ((0, 0), (x1 - x0 - 1, 0), (0, y1 - y0 - 1), (x1 - x0 - 1, y1 - y0 - 1)):
        args += ["-fill", "none", "-draw", "color %d,%d floodfill" % (x, y)]
    args += ["-trim", "+repage"]
    fit(args, dst)
    return dst


if __name__ == "__main__":
    made = []
    for n, s in sorted(ICONS.items()):
        made.append(from_icon(n, s))
    for n, b in sorted(CROPS.items()):
        made.append(from_sheet(n, b))
    total = sum(os.path.getsize(p) for p in made)
    print("生成: %d 点 / %d KB" % (len(made), total // 1024))
    print("  icons/ から %d 点 ／ 原書 p.2 から切り出し %d 点"
          % (len(ICONS), len(CROPS)))
