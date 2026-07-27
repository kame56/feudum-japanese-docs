# -*- coding: utf-8 -*-
"""日本語ドキュメント → ローカル閲覧用の静的サイト

    python3 scripts/build_site.py   → dist/site/

A4印刷版（build_rulebook_html.py / build_glossary_html.py）とは独立しており、
同じ docs/*.md を出典にしている。原稿を直せば両方に反映される。

生成物:
    dist/site/index.html          入口
    dist/site/<doc>-NN.html       章ごとのページ
    dist/site/figures/            画像（コピー）
    dist/site/assets/site.css     スタイル
    dist/site/assets/site.js      検索とサイドバー開閉
    dist/site/assets/search.js    全文検索インデックス（file:// でも読めるようJS形式）
"""
import os, re, sys, json, shutil, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mdbook

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "dist", "site")

mdbook.IMAGE_ROOT = ROOT
mdbook.IMAGE_EMBED = False          # サイトでは外部ファイル参照にする

SITE_TITLE = "Feudum 日本語ドキュメント"

DOCS = [
    dict(id="firstguide", title="はじめてガイド", sub="プレイ前に読む全体像",
         src="docs/feudum-firstguide-ja.md", split=False, shift=0,
         lead="1回目のプレイ前に読む冊子。点の出どころ、毎ラウンドやること、初手、つまずきどころ。"),
    dict(id="strategy", title="追放者の手引き", sub="攻略冊子",
         src="docs/feudum-strategy-ja.md", split=False, shift=0,
         lead="2〜4回目の初級〜中級者向け。点の三層モデルから勝ちパターンまで。"),
    dict(id="reference", title="リファレンス", sub="要素別の一覧と詳細",
         src="docs/feudum-reference-ja.md", split=False, shift=1,
         lead="アクションカード11種、6つのギルド、王命状16枚などを一覧と詳細で。卓上で引く用途。"),
    dict(id="rulebook", title="日本語ルールブック", sub="全20章",
         src="docs/feudum-rulebook-ja.md", split=False, shift=0,
         lead="英語版ルールブックの全訳。手順を通して調べるときはここ。"),
    dict(id="glossary", title="用語集", sub="英日対訳と定義",
         src="reference/feudum-glossary-ja.md", split=False, shift=0, extract="partB",
         lead="本文で使う用語の原語・訳語・定義。23分類。"),
]


# ---------------- Markdown の分解 ----------------
def strip_front(md):
    """H1タイトル・リード（引用）・目次を切り分ける。"""
    lines = md.split("\n")
    title = ""
    i = 0
    while i < len(lines):
        if lines[i].startswith("# "):
            title = lines[i][2:].strip()
            i += 1
            break
        i += 1
    rest = "\n".join(lines[i:])
    # 目次セクション（## 目次 〜 次の見出し）を落とす
    rest = re.sub(r"\n##+ 目次\n(?:(?!\n#{1,2} ).)*", "\n", rest, flags=re.S)
    return title, rest


def split_sections(md, level):
    """指定レベルの見出しで分割して [(見出し, 本文)] を返す。"""
    pat = re.compile(r"^%s (.+)$" % ("#" * level), flags=re.M)
    marks = list(pat.finditer(md))
    if not marks:
        return [("", md)]
    out = []
    pre = md[:marks[0].start()].strip()
    if pre:
        out.append(("", pre))
    for n, m in enumerate(marks):
        end = marks[n + 1].start() if n + 1 < len(marks) else len(md)
        out.append((m.group(1).strip(), md[m.start():end]))
    return out


def strip_pref(t):
    """見出し末尾の原書ページ注記（p. 10 など）を落とす。"""
    return re.sub(r"\s+pp?\.\s*[0-9–—-]+\s*$", "", t).strip()


def clean_title(t):
    """見出しからページ注記や装飾を落とした表示用タイトル。"""
    t = re.sub(r"\*\(pp?\.[^)]*\)\*", "", t)
    return re.sub(r"[*`]", "", t).strip()


# ---------------- ページの組み立て ----------------
# 1文書＝1ページ。章はページ内アンカーで辿る（ブラウザの検索を通しで効かせるため）
pages = []      # {url, doc, doc_title, title, md, shift, anchors}
page_pages = {} # 原書ページ番号 → url#アンカー（相互参照の解決用）

for d in DOCS:
    raw = open(os.path.join(ROOT, d["src"]), encoding="utf-8").read()
    if d.get("extract") == "partB":
        raw = raw[raw.index("# 第2部 — 用語集"):raw.index("# 付録")]
        raw = "# 用語集\n" + raw.split("\n", 1)[1]
    title, body = strip_front(raw)
    pages.append(dict(url="%s.html" % d["id"], doc=d["id"], doc_title=d["title"],
                      title=d["title"], md=body, shift=d["shift"]))

# ---------------- 変換 ----------------
for pg in pages:
    toc = []
    pg["html"] = mdbook.convert(pg["md"], heading_shift=pg["shift"], collect=toc)
    pg["anchors"] = [(sid, txt) for lvl, sid, txt in toc if lvl == 2]
    pg["toc"] = toc
    # 見出しに残る原書ページ注記（例「9. …  p. 10–15」）から、章アンカーの対応表を作る。
    # 単独ページ指定（p. 20）を範囲指定（pp. 17–20）より優先する。
    # 細かい見出し（h3）の単独ページ指定を最優先し、次に h2、最後に範囲指定で埋める
    for want_lvl, exact in ((2, True), (2, False)):
        for lvl, sid, txt in pg["toc"]:
            if lvl != want_lvl:
                continue
            for m in re.finditer(r"pp?\.\s*([0-9]+)(?:\s*[–—-]\s*([0-9]+))?", txt):
                a = int(m.group(1)); b = int(m.group(2) or m.group(1))
                if exact != (a == b):
                    continue
                for n in range(a, b + 1):
                    page_pages.setdefault(n, "%s#%s" % (pg["url"], sid))

# 見出し名 → url#アンカー（参照ラベルとの突き合わせ用。深い見出しほど優先）
title_index = []   # (doc, lvl, 見出し名, url#anchor, 原書ページの集合)
for pg in pages:
    for lvl, sid, txt in pg["toc"]:
        # 先頭の章番号だけを落とす（「11. 6つのギルド」の 6 まで消さないよう、区切りの空白を必須にする）
        name = re.sub(r"^[A-Za-z]?[0-9０-９]+(?:[.．][0-9０-９]+)*[.．]?[\s　]+", "", strip_pref(txt)).strip()
        if not name:
            continue
        pset = set()
        for m in re.finditer(r"pp?\.\s*([0-9]+)(?:\s*[–—-]\s*([0-9]+))?", txt):
            a = int(m.group(1)); b = int(m.group(2) or m.group(1))
            pset |= set(range(a, b + 1))
        title_index.append((pg["doc"], lvl, name, "%s#%s" % (pg["url"], sid), pset))


def find_by_label(label, num=None):
    """参照ラベル（例「ギルド加入」）に一致する見出しを探す。

    同名の見出しが複数ある場合は、原書のページ番号が一致するものを優先する。
    """
    cands = [e for e in title_index if label in e[2]]
    if not cands:
        return None
    cands.sort(key=lambda e: (0 if (num and num in e[4]) else 1,
                              0 if e[0] == "rulebook" else 1,
                              0 if e[2] == label else 1,
                              len(e[2]), e[1]))
    return cands[0][3]


KANJI = {"序": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
         "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11, "終": 12}


def resolve_refs(pg):
    h = pg["html"]

    # （→ 16 ページ「ギルド加入」）→ ルールブックの該当章へ
    def page_ref(m):
        num, label = int(m.group(1)), (m.group(2) or "")
        url = find_by_label(label, num) if label else None
        if not url:
            url = page_pages.get(num)
        if not url:
            return m.group(0)
        text = label if label else "ルールブック"
        return '（→ <a href="%s">%s</a>）' % (url, html.escape(text.strip("「」")))
    h = re.sub(r"（→\s*(\d+)\s*ページ(?:「([^」]*)」)?）", page_ref, h)

    # （→九章）（→ 9章）→ 同じ文書の該当章へ
    def chap_ref(m):
        raw = m.group(1); tail = m.group(2) or ""
        n = KANJI.get(raw, None)
        if n is None:
            n = int(raw) if raw.isdigit() else None
        if n is None:
            return m.group(0)
        for sid, txt in pg.get("anchors", []):
            if re.match(r"^%s[\.．　 ]" % re.escape(raw), txt) or re.match(r"^%d[\.．　 ]" % n, txt):
                return '（→ <a href="#%s">%s</a>%s）' % (sid, html.escape(re.sub(r"\s+pp?\..*$", "", txt)), html.escape(tail))
        return m.group(0)
    h = re.sub(r"（→\s*([0-9]+|[序一二三四五六七八九十]{1,2}|終)章([^）]*)）", chap_ref, h)

    pg["html"] = h


for pg in pages:
    resolve_refs(pg)


# ---------------- ナビゲーション ----------------
# サイドバー用のアイコン（外部ファイルに依存しないよう SVG を直接埋め込む）
ICON_DOC = ('<svg class="doc-ic" viewBox="0 0 16 16" aria-hidden="true">'
            '<path d="M3.6 1.6h5.6l3.2 3.2v9.6H3.6z" fill="none" stroke="currentColor" stroke-width="1.2"/>'
            '<path d="M9.2 1.6v3.2h3.2" fill="none" stroke="currentColor" stroke-width="1.2"/>'
            '<path d="M5.8 7.6h4.4M5.8 9.8h4.4M5.8 12h2.8" fill="none" stroke="currentColor" stroke-width="1.2"/>'
            '</svg>')
ICON_CARET = ('<svg viewBox="0 0 10 10" aria-hidden="true">'
              '<path d="M3.2 1.6 6.8 5 3.2 8.4" fill="none" stroke="currentColor" '
              'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def sidebar(current_url):
    o = ['<nav class="side" id="side">',
         '<a class="brand" href="index.html">%s</a>' % html.escape(SITE_TITLE),
         '<div class="searchbox"><input id="q" type="search" placeholder="検索（例: 押し出し）" autocomplete="off">'
         '<div id="results" class="results" hidden></div></div>',
         '<ul class="nav">']
    for d in DOCS:
        ps = [p for p in pages if p["doc"] == d["id"]]
        first = ps[0]["url"]
        active = " open is-cur" if any(p["url"] == current_url for p in ps) else ""
        o.append('<li class="nav-doc%s" data-doc="%s">'
                 '<div class="doc-row">'
                 '<a class="doc-t" href="%s">%s<span class="doc-name">%s</span></a>'
                 '<button class="doc-tog" type="button" aria-expanded="%s" '
                 'aria-label="%s の目次を開閉">%s</button>'
                 '</div><ul>'
                 % (active, d["id"], first, ICON_DOC, html.escape(d["title"]),
                    "true" if active else "false", html.escape(d["title"]), ICON_CARET))
        p = ps[0]
        for sid, txt in p["anchors"]:
            o.append('<li><a href="%s#%s">%s</a></li>' % (p["url"], sid, html.escape(strip_pref(txt))))
        o.append("</ul></li>")
    o.append("</ul></nav>")
    return "\n".join(o)


def page_toc(pg):
    if not pg["anchors"] or len(pg["anchors"]) < 2:
        return ""
    items = "".join('<li><a href="#%s">%s</a></li>' % (s, html.escape(strip_pref(t))) for s, t in pg["anchors"])
    return '<aside class="ptoc"><div class="ptoc-t">このページ</div><ul>%s</ul></aside>' % items


def prevnext(i):
    o = []
    if i > 0:
        p = pages[i - 1]
        o.append('<a class="pn prev" href="%s"><span>前</span>%s</a>' % (p["url"], html.escape(p["title"])))
    if i < len(pages) - 1:
        n = pages[i + 1]
        o.append('<a class="pn next" href="%s"><span>次</span>%s</a>' % (n["url"], html.escape(n["title"])))
    return '<nav class="prevnext">%s</nav>' % "".join(o) if o else ""


TPL = """<!doctype html>
<html lang="ja" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="assets/site.css">
</head>
<body>
<header class="top">
  <button class="burger" id="burger" aria-label="メニュー">≡</button>
  <a class="top-t" href="index.html">{site}</a>
  <button class="theme" id="theme" aria-label="表示切替">◐</button>
</header>
{side}
<div class="backdrop" id="backdrop"></div>
<main class="main">
  <div class="crumb">{crumb}</div>
  <article class="doc">
  <h1>{h1}</h1>
{body}
  </article>
  {prevnext}
</main>
{ptoc}
<script src="assets/site.js"></script>
</body>
</html>
"""


def render(pg, i):
    crumb = '<a href="%s">%s</a>' % ([p for p in pages if p["doc"] == pg["doc"]][0]["url"],
                                     html.escape(pg["doc_title"]))
    return TPL.format(title=html.escape("%s | %s" % (pg["title"], SITE_TITLE)),
                      site=html.escape(SITE_TITLE),
                      side=sidebar(pg["url"]), crumb=crumb,
                      h1=html.escape(pg["title"]), body=pg["html"],
                      prevnext=prevnext(i), ptoc=page_toc(pg))


# ---------------- 入口ページ ----------------
def index_page():
    cards = []
    for d in DOCS:
        ps = [p for p in pages if p["doc"] == d["id"]]
        cards.append(
            '<a class="card" href="%s"><div class="card-t">%s</div>'
            '<div class="card-s">%s</div><p>%s</p>'
            '<div class="card-n">%d 章</div></a>'
            % (ps[0]["url"], html.escape(d["title"]), html.escape(d["sub"]),
               html.escape(d["lead"]), len(ps[0]["anchors"])))
    body = """
<p class="lead">ボードゲーム <strong>Feudum</strong>（Mark Swanson / Odd Bird Games, © 2017）の日本語ドキュメントです。
目的に応じて4冊＋用語集に分かれています。</p>
<div class="cards">%s</div>

<h2>注意</h2>
<ul>
<li>非公式の翻訳です。原典は英語版ルールブック（印刷ページ1〜25）。</li>
<li>実物のボードとカードで確認できていない箇所が3つあります。<strong>軍役トラックの印字値</strong>（プレイヤーディスクに隠れて読めない）、<strong>ギルドごとの拠点アイコンの対応</strong>、<strong>vp（崇敬点）の記号の図柄</strong>。該当箇所には注記があります。</li>
<li>点線の枠は<strong>画像の配置予定地</strong>です。画像を用意すると差し替わります。</li>
</ul>
""" % "".join(cards)
    return TPL.format(title=html.escape(SITE_TITLE), site=html.escape(SITE_TITLE),
                      side=sidebar("index.html"), crumb="", h1=html.escape(SITE_TITLE),
                      body=body, prevnext="", ptoc="")


# ---------------- 検索インデックス ----------------
def plain(h):
    t = re.sub(r"<[^>]+>", " ", h)
    t = html.unescape(t)
    return re.sub(r"\s+", " ", t).strip()


def build_index():
    """章（h2）単位でインデックスを作る。1文書＝1ページなので、章まで案内できるようにする。"""
    out = []
    for p in pages:
        parts = re.split(r'(<h2 id="[^"]+"[^>]*>)', p["html"])
        head = plain(parts[0])
        if head:
            out.append(dict(u=p["url"], d=p["doc_title"], t=p["title"], x=head[:4000]))
        for i in range(1, len(parts), 2):
            sid = re.search(r'id="([^"]+)"', parts[i]).group(1)
            chunk = parts[i] + (parts[i + 1] if i + 1 < len(parts) else "")
            txt = plain(chunk)
            title = strip_pref(txt.split("\n")[0][:60].strip())
            m = re.match(r"^(.{1,60}?)(?=\s|$)", txt)
            out.append(dict(u="%s#%s" % (p["url"], sid), d=p["doc_title"],
                            t=strip_pref(plain(parts[i] + parts[i + 1].split("<")[0]) if i + 1 < len(parts) else title),
                            x=txt[:4000]))
    return out


# ---------------- 出力 ----------------
def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "assets"))
    for i, pg in enumerate(pages):
        open(os.path.join(OUT, pg["url"]), "w", encoding="utf-8").write(render(pg, i))
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(index_page())
    # GitHub Pages が Jekyll を通さないようにする（アンダースコア始まりの名前を使えるように）
    open(os.path.join(OUT, ".nojekyll"), "w").close()

    figsrc = os.path.join(ROOT, "figures")
    figdst = os.path.join(OUT, "figures")
    os.makedirs(figdst, exist_ok=True)
    for f in sorted(os.listdir(figsrc)):
        if f.lower().endswith((".jpg", ".jpeg", ".png")):
            shutil.copy2(os.path.join(figsrc, f), os.path.join(figdst, f))

    open(os.path.join(OUT, "assets", "search.js"), "w", encoding="utf-8").write(
        "window.FEUDUM_INDEX=" + json.dumps(build_index(), ensure_ascii=False) + ";")
    open(os.path.join(OUT, "assets", "site.css"), "w", encoding="utf-8").write(CSS)
    open(os.path.join(OUT, "assets", "site.js"), "w", encoding="utf-8").write(JS)

    print("written:", OUT)
    print("  ページ数:", len(pages) + 1)
    for p in pages:
        print("    %-16s %2d 章" % (p["doc_title"], len(p["anchors"])))
    print("  図版:", len(os.listdir(figdst)), "点")
    print("  検索インデックス:", os.path.getsize(os.path.join(OUT, "assets", "search.js")) // 1024, "KB")


CSS = open(os.path.join(ROOT, "scripts", "site_assets", "site.css"), encoding="utf-8").read()
JS = open(os.path.join(ROOT, "scripts", "site_assets", "site.js"), encoding="utf-8").read()

if __name__ == "__main__":
    main()
