# -*- coding: utf-8 -*-
"""原書PDFの埋め込み画像を、アイコン素材として使える形に整える。

    python3 scripts/enhance_embedded.py

やっていること:
  1. RGB画像と、その直後にある透過マスク（グレースケール）を対にする
  2. 色を4倍に拡大（Lanczos）し、Kuwaharaフィルタで平坦部のノイズを均してから輪郭を締める
  3. マスクを重ねて背景を透過にし、余白を切り詰める
  4. 小さすぎるもの・ほぼ単色のもの・重複を除く

出力: figures/icons/icon-PPP-NNN.png（透過PNG）＋ index.html（一覧）

注意: 元画像は75 ppiで、文字や数字はもともと判読できません。これは解像度を上げる処理ではなく、
      拡大したときの見苦しさ（JPEGのにじみ・ブロックノイズ）を抑えるための処理です。
"""
import os, re, sys, json, shutil, hashlib, subprocess, tempfile
from PIL import Image, ImageStat

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "source", "extracted", "embedded")
OUT = os.path.join(ROOT, "figures", "icons")

SCALE = 4              # 色の拡大率
MAX_SIDE = 1000        # 出力の長辺の上限（大きすぎるとファイルが重い）
MIN_SIDE = 22          # これ未満の画像は捨てる
MIN_STDDEV = 8         # ほぼ単色（背景の塗り）は捨てる
KUWAHARA = "3"         # 平坦化の強さ
UNSHARP = "0x1+0.7+0.02"


def listing():
    """(RGB画像, マスク or None) の組を返す。マスクは直後のグレースケール画像。"""
    files = sorted(f for f in os.listdir(SRC) if f.lower().endswith(".png"))
    info = []
    for f in files:
        try:
            im = Image.open(os.path.join(SRC, f))
            info.append((f, im.mode, im.size))
        except Exception:
            pass
    out = []
    for i, (f, mode, size) in enumerate(info):
        if mode != "RGB":
            continue
        mask = None
        if i + 1 < len(info):
            nf, nmode, nsize = info[i + 1]
            # マスクは同じか2倍の寸法のグレースケール
            if nmode == "L" and abs(nsize[0] / size[0] - nsize[1] / size[1]) < 0.06 \
               and 0.9 <= nsize[0] / size[0] <= 2.2:
                mask = nf
        out.append((f, mask, size))
    return out


def enhance(src_path, mask_path, dst_path):
    im = Image.open(src_path).convert("RGB")
    w, h = im.size
    big = im.resize((w * SCALE, h * SCALE), Image.LANCZOS)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
        tmp = tf.name
    big.save(tmp)
    subprocess.run(["magick", tmp, "-kuwahara", KUWAHARA, "-unsharp", UNSHARP, tmp],
                   check=True, capture_output=True)
    big = Image.open(tmp).convert("RGB")
    os.unlink(tmp)

    if mask_path:
        m = Image.open(mask_path).convert("L").resize(big.size, Image.LANCZOS)
        big = big.convert("RGBA")
        big.putalpha(m)
        bbox = big.getbbox()          # 透明な余白を切る
        if bbox:
            big = big.crop(bbox)
    if max(big.size) > MAX_SIDE:
        r = MAX_SIDE / max(big.size)
        big = big.resize((max(1, int(big.width * r)), max(1, int(big.height * r))), Image.LANCZOS)
    if big.mode == "RGBA":
        big = big.quantize(colors=192, method=Image.FASTOCTREE).convert("RGBA")
    big.save(dst_path, optimize=True)
    return big.size


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    seen, made, skipped = set(), [], {"小さい": 0, "単色": 0, "重複": 0}
    for f, mask, size in listing():
        if min(size) < MIN_SIDE:
            skipped["小さい"] += 1; continue
        p = os.path.join(SRC, f)
        digest = hashlib.md5(open(p, "rb").read()).hexdigest()
        if digest in seen:
            skipped["重複"] += 1; continue
        im = Image.open(p).convert("RGB")
        if max(ImageStat.Stat(im).stddev) < MIN_STDDEV:
            skipped["単色"] += 1; continue
        seen.add(digest)
        name = "icon-" + re.sub(r"^img-", "", f)
        try:
            outsize = enhance(p, os.path.join(SRC, mask) if mask else None,
                              os.path.join(OUT, name))
        except subprocess.CalledProcessError:
            continue
        made.append((name, size, outsize, bool(mask)))

    made.sort(key=lambda r: -(r[1][0] * r[1][1]))
    cards = "".join(
        '<figure><img src="%s" alt=""><figcaption>%s<br><span>%d×%d → %d×%d%s</span>'
        "</figcaption></figure>" % (n, n, s[0], s[1], o[0], o[1], " 透過" if m else "")
        for n, s, o, m in made)
    html = """<!doctype html><html lang="ja"><meta charset="utf-8">
<title>Feudum アイコン素材</title>
<style>
body{margin:0;padding:24px;background:#faf7f0;color:#2a2119;
     font-family:"Hiragino Sans","Yu Gothic",sans-serif}
h1{font-size:19px;margin:0 0 4px} p.lead{font-size:13px;color:#7d6c55;margin:0 0 20px;max-width:70ch;line-height:1.8}
.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(150px,1fr))}
figure{margin:0;padding:10px;background:#fff;border:1px solid #e3d7c0;border-radius:8px;text-align:center}
figure img{max-width:100%%;max-height:120px;height:auto;
  background:repeating-conic-gradient(#eee 0 25%%,#fff 0 50%%) 0 0/14px 14px}
figcaption{font-size:10.5px;color:#57493a;margin-top:8px;line-height:1.5;word-break:break-all}
figcaption span{color:#a08e70;font-size:9.5px}
</style>
<h1>Feudum アイコン素材（原書PDFの埋め込み画像を加工）</h1>
<p class="lead">元画像は75 ppi のため、文字や数字は判読できません。輪郭と色面を整え、透過を復元したものです。
使いたいものが決まったら、<code>figures/</code> へ用途名でコピーしてください（例 <code>fig-goods-5.jpg</code>）。
市松模様は透過部分です。</p>
<div class="grid">%s</div>
</html>""" % cards
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(html)

    total = sum(os.path.getsize(os.path.join(OUT, n)) for n, _, _, _ in made)
    print("出力:", OUT)
    print("  生成: %d 点 / %d KB" % (len(made), total // 1024))
    print("  透過あり:", sum(1 for r in made if r[3]), "点")
    print("  除外:", ", ".join("%s %d" % (k, v) for k, v in skipped.items()))
    print("  一覧:", os.path.join(OUT, "index.html"))


if __name__ == "__main__":
    main()
