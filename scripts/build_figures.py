# -*- coding: utf-8 -*-
"""見開きレンダリング（source/extracted/pages/spread-NN.png, 200dpi）から図版を切り出す。

座標は原書のポイント単位（1pt = 1/72 inch、原点は各シートの左上）。
PDFシートと印刷ページの対応: p1=表紙 / p2=2–3 / p3=4–5 / p4=6–7 / p5=8–9 /
p6=10–11 / p7=12–13 / p8=14–15 / p9=16–17 / p10=18–19 / p11=20–21 / p12=22–23 / p13=24
"""
from PIL import Image
import os

ROOT = "/Users/toshimitsu/feudum"
OUT = os.path.join(ROOT, "figures")
os.makedirs(OUT, exist_ok=True)
S = 200 / 72.0          # 200dpi レンダリングのスケール
MAXW = 1400             # 出力幅の上限

# name, sheet, x0, y0, x1, y1 (pt), caption
CROPS = [
    ("cover",      1,    0,   0,  596, 842, "原書の表紙"),
    ("components", 2,   18, 185,  595, 815, "コンポーネント一覧（原書 p. 2）"),
    ("board",      2,  560, 145, 1180, 790, "ゲームボードの構成（原書 p. 3）"),
    ("setup",      3,   45, 288, 1150, 768, "セットアップ図 ①〜⑳（原書 pp. 4–5）"),
    ("pawns",      5,   38, 640,  258, 780, "6人のポーンキャラクター（原書 p. 8）"),
    ("routes",     5,  286, 456,  432, 578, "3種の乗り物ルート（原書 p. 8）"),
    ("roles",      5,  925, 225, 1128, 375, "支配者・農奴・臣民（原書 p. 9）"),
    ("locations",  6,   33, 268,  212, 324, "拠点の4種類（原書 p. 10）"),
    ("tilechart",  6,  228, 452,  302, 588, "地域タイル表（原書 p. 10）"),
    ("military",   6,  290, 388,  578, 532, "軍役トラックの投石機スペース（原書 p. 10）"),
    ("landscapes", 6,  636, 326,  864, 490, "4種の地形（原書 p. 11）"),
    ("conquer",    7,  895, 160, 1190, 320, "フューダムへの攻撃の例（原書 p. 13）"),
    ("defend",     8,  370,  55,  595, 225, "防御アクションの例（原書 p. 14）"),
    ("payment",    8,  912, 138, 1048, 220, "階級順の支払いの例（原書 p. 15）"),
    ("guildtrack", 9,  158, 400,  302, 448, "ギルドトラックの階級（原書 p. 16）"),
    ("krud",      10,  298, 478,  594, 628, "クルド樽1個を作ったときに追加される影響マーカー（原書 p. 18）"),
    ("serpent",   10,  940, 590, 1190, 720, "シーサーペント（原書 p. 19）"),
    ("writs",     13,   18,  30,  578, 822, "王命状カード全16枚（原書 p. 24）"),
]

if __name__ == "__main__":
    total = 0
    for name, pg, x0, y0, x1, y1, cap in CROPS:
        im = Image.open(os.path.join(ROOT, "source", "extracted", "pages", "spread-%02d.png" % pg))
        box = tuple(int(round(v * S)) for v in (x0, y0, x1, y1))
        box = (max(0, box[0]), max(0, box[1]), min(im.width, box[2]), min(im.height, box[3]))
        crop = im.crop(box)
        if crop.width > MAXW:
            crop = crop.resize((MAXW, int(crop.height * MAXW / crop.width)), Image.LANCZOS)
        p = os.path.join(OUT, "fig-%s.jpg" % name)
        crop.convert("RGB").save(p, quality=88, optimize=True, progressive=True)
        kb = os.path.getsize(p) // 1024
        total += kb
        print("%-11s %4dx%-4d %5dKB  %s" % (name, crop.width, crop.height, kb, cap))
    # 旧PNGの掃除
    for f in os.listdir(OUT):
        if f.endswith(".png"):
            os.remove(os.path.join(OUT, f))
    print("\n%d 図版 / 合計 %d KB" % (len(CROPS), total))
