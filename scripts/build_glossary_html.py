# -*- coding: utf-8 -*-
"""用語集 → A4印刷向け HTML（別冊）

    python3 scripts/build_glossary_html.py   → dist/feudum-glossary-ja.html

出典は reference/feudum-glossary-ja.md の第2部（B1〜B23）。
第1部（背景と文脈）と付録C（訳語の決定記録）は翻訳作業用のため冊子には載せない。
巻末に英日索引（アルファベット順）を自動生成して付ける。
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mdbook

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_SCALE = 0.75

SRC = os.path.join(ROOT, "reference", "feudum-glossary-ja.md")
raw = open(SRC, encoding="utf-8").read()
part_b = raw[raw.index("# 第2部 — 用語集"):raw.index("# 付録")]
part_b = part_b.split("\n", 1)[1]          # 「# 第2部」行を落とす
part_b = re.sub(r"^## 目次\n(?:.*\n)*?\n---\n", "", part_b, flags=re.M)

# ---------------- 索引の抽出 ----------------
def extract_terms(md):
    """各表のヘッダから English 列と 日本語列を見つけ、(英語, 日本語, カテゴリ) を集める。"""
    out, cat, header = [], None, None
    for line in md.split("\n"):
        m = re.match(r"^## (B\d+)\.\s*(.+)$", line)
        if m:
            cat = "%s %s" % (m.group(1), m.group(2)); header = None; continue
        if not line.startswith("|"):
            header = None; continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
            continue
        if header is None:                  # 最初の行＝ヘッダ
            header = [re.sub(r"[*`]", "", c) for c in cells]
            continue
        try:
            ei = next(i for i, h in enumerate(header) if h.lower().startswith("english"))
            ji = next(i for i, h in enumerate(header) if h.startswith("日本語") or "訳" in h)
        except StopIteration:
            continue
        if max(ei, ji) >= len(cells):
            continue
        en = re.sub(r"[*`\"]", "", cells[ei]).strip()
        ja = re.sub(r"[*`]", "", cells[ji]).strip()
        ja = re.sub(r"（初出のみ.*?）", "", ja).strip()
        if en and ja and en != "—":
            out.append((en, ja, cat))
    return out


terms = extract_terms(part_b)

# 同じ（英語, 日本語）が複数の分類に出る場合は1行にまとめる
merged = {}
for en, ja, cat in terms:
    merged.setdefault((en, ja), []).append(cat)
terms = [(en, ja, " / ".join(dict.fromkeys(cats))) for (en, ja), cats in merged.items()]
terms.sort(key=lambda r: r[0].lower().lstrip('"('))

rows = "".join(
    "<tr><td>%s</td><td>%s</td><td class=\"cat\">%s</td></tr>" % (mdbook.inline(en), mdbook.inline(ja), c)
    for en, ja, c in terms)
INDEX = f"""<h2 id="index" class="newpage">英日索引</h2>
<p class="note-line">本編に収録した用語をアルファベット順に並べたものです。分類欄の記号は本編の節番号に対応します。</p>
<div class="tablewrap"><table class="index"><thead>
<tr><th>English</th><th>日本語</th><th>分類</th></tr></thead>
<tbody>{rows}</tbody></table></div>"""

# ---------------- 本編 ----------------
toc = []
body = mdbook.convert(part_b, collect=toc)
TOC = mdbook.toc_html(toc, extra_top=[("index", "英日索引", [])])

EXTRA_CSS = r"""
/* ---- glossary ---- */
h2{break-before:auto}
h2.newpage{break-before:page;page-break-before:always;margin-top:0}
table td:first-child{
  font-family:ui-monospace,Menlo,monospace;font-size:8.6pt;color:#4a3d2f;
}
table.index{font-size:8.8pt}
table.index td:nth-child(2){font-family:inherit;font-size:9.3pt}
table.index td.cat{
  font-family:"Hiragino Sans","Yu Gothic",sans-serif;font-size:7.8pt;color:#8a7a63;
  white-space:nowrap;
}
.note-line{font-size:9pt;color:var(--ink-soft);margin:.2em 0 1em}
.howto{
  background:var(--parch);border:1px solid var(--line-soft);border-left:4px solid var(--gold);
  border-radius:4px;padding:.8em 1em;margin:1em 0 1.4em;font-size:9.6pt;
}
.howto p{margin:.35em 0}
"""

BODY = f"""
<section class="cover">
  <div class="orn">&#10086;</div>
  <h1>FEUDUM</h1>
  <div class="ja">用 語 集</div>
  <div class="rule"></div>
  <div class="sub">英日対訳と定義</div>
  <dl>
    <div><dt>対象</dt><dd>『Feudum 日本語ルールブック』『追放者の手引き』</dd></div>
    <div><dt>収録</dt><dd>{len(terms)} 語 / 23 分類</dd></div>
    <div><dt>発行</dt><dd>Odd Bird Games &copy; 2017（原典）</dd></div>
  </dl>
  <div class="foot">
    日本語ルールブックおよび攻略冊子で使用する用語の対訳集<br>
    A4印刷用レイアウト
  </div>
</section>

<section class="toc-page">
<h2 id="toc">目次</h2>
{TOC}
</section>

<section class="content">
<h2 id="howto">この冊子について</h2>

<div class="howto">
<p><strong>本編</strong>は用語を23の分類に分け、<strong>原語（英語）→ 日本語 → 定義</strong>の順に並べています。ゲーム中に出てくる場面ごとにまとまっているので、「ギルドまわりの用語をまとめて確認したい」といった読み方ができます。</p>
<p><strong>巻末の英日索引</strong>は全用語をアルファベット順に並べたものです。英語版のルールブックやカード、海外のレビュー記事と読み比べるときに使ってください。</p>
<p>日本語ルールブックと攻略冊子は、すべてこの冊子の訳語で統一しています。</p>
</div>

{body}
</section>

<section class="appendix">
{INDEX}
</section>

<p class="endnote">
本冊子の定義は、英語版ルールブック（Feudum Rulebook, 印刷ページ1〜25）の記述に基づきます。<br>
&copy; 2017 Odd Bird Games. 本訳文は個人利用を目的とした非公式翻訳です。
</p>
"""

css = mdbook.css(FONT_SCALE, EXTRA_CSS)
out = os.path.join(ROOT, "dist", "feudum-glossary-ja.html")
open(out, "w", encoding="utf-8").write(mdbook.document("Feudum 用語集", css, BODY))
print("written:", out, len(open(out, encoding="utf-8").read()), "chars")
print("  分類:", sum(1 for l, s, t in toc if l == 2), " 索引:", len(terms), "語")
