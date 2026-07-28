# -*- coding: utf-8 -*-
"""Markdown → A4印刷向け HTML の共通部品。

冊子ビルダー（build_rulebook_html.py / build_glossary_html.py）から読み込む。
- convert()      : Markdown をブロック単位で HTML へ変換（見出し・表・引用・リスト・コードフェンス）
- css()          : 基本スタイルを返す。font_scale で全体の文字サイズを一括変更
- document()     : <!doctype html> ごと組み立てる
"""
import re, html, os

# ---------------- inline ----------------
GOODS = {"食料": "food", "木材": "wood", "鉄": "iron", "硫黄": "sulfur", "硝石": "saltpeter"}


def inline(s):
    s = s.replace("\\*", "\x00AST\x00")
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", lambda m: "<code>%s</code>" % m.group(1), s)
    s = re.sub(r":(食料|木材|鉄|硫黄|硝石):",
               lambda m: '<span class="goods goods-%s"></span>%s' % (GOODS[m.group(1)], m.group(1)), s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", s)
    s = s.replace("\x00AST\x00", "*")
    return s

def slug(t):
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"[*`]", "", t).strip().lower()
    t = re.sub(r"[（）()：:.,、。「」/／—–\"'’]", "", t)
    t = re.sub(r"\s+", "-", t)
    return re.sub(r"-+", "-", t).strip("-")

# ---------------- block ----------------
def convert(md, heading_shift=0, collect=None):
    lines = md.split("\n")
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]

        if not ln.strip():
            i += 1; continue

        # code fence
        if ln.startswith("```"):
            i += 1; buf = []
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(html.escape(lines[i])); i += 1
            i += 1
            out.append("<pre class=\"diagram\">%s</pre>" % "\n".join(buf))
            continue

        # hr
        if re.fullmatch(r"-{3,}", ln.strip()):
            out.append('<hr>'); i += 1; continue

        # heading
        m = re.match(r"^(#{1,6})\s+(.*)$", ln)
        if m:
            lvl = min(len(m.group(1)) + heading_shift, 6)
            txt = m.group(2).strip()
            sid = slug(txt)
            body = inline(txt)
            # ページ注記を小さく
            body = re.sub(r"<em>\((p{1,2}\.[^)]*)\)</em>",
                          r'<span class="pref">\1</span>', body)
            out.append('<h%d id="%s">%s</h%d>' % (lvl, sid, body, lvl))
            if collect is not None:
                collect.append((lvl, sid, re.sub(r"<[^>]+>", "", body).strip()))
            i += 1; continue

        # table
        if ln.lstrip().startswith("|"):
            block = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                block.append(lines[i].strip()); i += 1
            out.append(table_html(block))
            continue

        # blockquote
        if ln.lstrip().startswith(">"):
            buf = []
            while i < len(lines) and (lines[i].lstrip().startswith(">") or
                                      (lines[i].strip() == "" and
                                       i + 1 < len(lines) and lines[i + 1].lstrip().startswith(">"))):
                if lines[i].strip() == "":
                    buf.append("")
                else:
                    buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            inner = convert("\n".join(buf), heading_shift)
            cls = "callout"
            joined = "\n".join(buf)
            if re.search(r"（上級ゲーム）|（Reeves）|上級ゲーム", joined):
                cls = "callout adv"
                # 見出しバッジで示すので本文中の「（上級ゲーム）」は削る
                inner = inner.replace("（上級ゲーム）", "")
            elif re.search(r"^\s*豆知識", joined):
                cls = "callout trivia"
            elif re.search(r"\*\*注:|\*\*重要:|\*\*ヒント:|\*\*表に関する注:", joined):
                cls = "callout note"
            out.append('<div class="%s">%s</div>' % (cls, inner))
            continue

        # list
        m = re.match(r"^(\s*)([-*])\s+(.*)$", ln)
        if m:
            block = []
            while i < len(lines):
                if re.match(r"^\s*[-*]\s+", lines[i]):
                    block.append(lines[i]); i += 1
                elif lines[i].startswith("  ") and lines[i].strip() and block:
                    block[-1] += " " + lines[i].strip(); i += 1
                else:
                    break
            out.append(list_html(block))
            continue

        # ::: コンテナ（グリッド・フロー等）。セルの区切りは +++
        m = re.match(r"^:::\s*([a-z0-9-]+)\s*$", ln)
        if m:
            kind = m.group(1)
            i += 1
            buf, depth = [], 1
            while i < len(lines):
                if re.match(r"^:::\s*[a-z0-9-]+\s*$", lines[i]):
                    depth += 1
                elif lines[i].strip() == ":::":
                    depth -= 1
                    if depth == 0:
                        i += 1
                        break
                buf.append(lines[i]); i += 1
            # サイトだけに出す内容（A4版では丸ごと落とす）
            if kind == "web-only":
                if WEB_ONLY:
                    out.append('<div class="web-only">%s</div>'
                               % convert("\n".join(buf), heading_shift))
                continue
            cells = re.split(r"^\+\+\+\s*$", "\n".join(buf), flags=re.M)
            if kind == "story":
                # 先頭の figure を肖像として残し、見出しと本文は story-body でまとめる
                parts = []
                for c in cells:
                    if not c.strip():
                        continue
                    h = convert(c, heading_shift)
                    m2 = re.match(r"\s*(<figure\b.*?</figure>)(.*)$", h, re.S)
                    fig, body = (m2.group(1), m2.group(2)) if m2 else ("", h)
                    parts.append('<div class="cell">%s<div class="story-body">%s</div></div>'
                                 % (fig, body))
                out.append('<div class="blk blk-story">%s</div>' % "".join(parts))
                continue
            inner = "".join('<div class="cell">%s</div>' % convert(c, heading_shift)
                            for c in cells if c.strip())
            if kind == "flow":
                parts = re.findall(r"<div class=\"cell\">.*?</div>(?=<div class=\"cell\">|$)", inner, re.S)
                inner = '<div class="arrow" aria-hidden="true"></div>'.join(parts) if parts else inner
            out.append('<div class="blk blk-%s">%s</div>' % (kind, inner))
            continue

        # 生HTMLブロック（行頭が < のブロック要素）
        m = re.match(r"^<(div|section|figure|table|details|aside|svg|dl|blockquote|p|pre|ul|ol|h[1-6])\b", ln)
        if m:
            tag = m.group(1)
            buf = [ln]; i += 1
            close = "</%s>" % tag
            depth = ln.count("<" + tag) - ln.count(close)
            while i < len(lines) and depth > 0:
                buf.append(lines[i])
                depth += lines[i].count("<" + tag) - lines[i].count(close)
                i += 1
            out.append("\n".join(buf))
            continue

        # image（単独行の ![caption|size](path)）
        m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", ln)
        if m:
            out.append(image_html(m.group(1), m.group(2)))
            i += 1; continue

        # paragraph
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(
                r"^(#{1,6}\s|>|\s*[-*]\s|\||```|-{3,}$)", lines[i]):
            buf.append(lines[i].strip()); i += 1
        if buf:
            out.append("<p>%s</p>" % inline(" ".join(buf)))
        else:
            i += 1
    return "\n".join(out)

def list_html(block):
    items = []
    for ln in block:
        ind = len(ln) - len(ln.lstrip())
        txt = re.sub(r"^\s*[-*]\s+", "", ln)
        items.append((ind // 2, inline(txt)))
    html_out, stack = [], []
    for depth, txt in items:
        while len(stack) > depth + 1:
            html_out.append("</li></ul>"); stack.pop()
        if len(stack) == depth + 1:
            html_out.append("</li>")
        while len(stack) < depth + 1:
            html_out.append("<ul>"); stack.append(depth)
        html_out.append("<li>" + txt)
    while stack:
        html_out.append("</li></ul>"); stack.pop()
    return "".join(html_out)

def table_html(block):
    rows = []
    for ln in block:
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        rows.append(cells)
    if len(rows) >= 2 and all(re.fullmatch(r":?-{2,}:?", c) for c in rows[1]):
        head, body = rows[0], rows[2:]
    else:
        head, body = None, rows
    o = ['<div class="tablewrap"><table>']
    if head:
        o.append("<thead><tr>" + "".join("<th>%s</th>" % inline(c) for c in head) + "</tr></thead>")
    o.append("<tbody>")
    for r in body:
        o.append("<tr>" + "".join("<td>%s</td>" % inline(c) for c in r) + "</tr>")
    o.append("</tbody></table></div>")
    return "".join(o)


BASE_CSS = r"""
:root{
  --ink:#241c14; --ink-soft:#4a3d2f; --line:#c9b79a; --line-soft:#e3d7c0;
  --paper:#ffffff; --parch:#faf5ea; --gold:#8a6d2f; --accent:#6b2f2f;
  --adv:#f4efe0; --note:#f6f2e8; --trivia:#f2f4ee;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  margin:0; color:var(--ink); background:var(--paper);
  font-family:"Hiragino Mincho ProN","Yu Mincho","YuMincho","Noto Serif JP",serif;
  font-size:10.2pt; line-height:1.75; text-align:justify;
  font-feature-settings:"palt" 1;
}
.sheet{max-width:190mm;margin:0 auto;padding:14mm 12mm 20mm}

/* ---- headings ---- */
h1,h2,h3,h4,h5{
  font-family:"Hiragino Sans","Yu Gothic","Noto Sans JP",sans-serif;
  line-height:1.4; text-align:left; break-after:avoid; page-break-after:avoid;
}
h2{
  font-size:15pt; margin:1.9em 0 .85em; padding:.35em 0 .3em .1em;
  border-bottom:2.5px solid var(--gold); color:#2c2015;
}
h2.newpage{break-before:page;page-break-before:always;margin-top:0}
h3{
  font-size:12.2pt; margin:1.7em 0 .6em; padding-left:.5em;
  border-left:5px solid var(--gold); color:#33261a;
}
h4{
  font-size:11pt; margin:1.35em 0 .45em; color:var(--accent);
}
h4::before{content:"◆ ";font-size:.85em;color:var(--gold)}
h5{font-size:10.4pt;margin:1.1em 0 .35em;color:var(--ink-soft)}
.pref{
  font-family:"Hiragino Sans","Yu Gothic",sans-serif; font-weight:400;
  font-size:.62em; color:#8a7a63; margin-left:.7em; letter-spacing:.02em;
  white-space:nowrap;
}

p{margin:.55em 0}
strong{font-weight:700;color:#1c150e}
em{font-style:italic}
code{
  font-family:ui-monospace,"SFMono-Regular",Menlo,monospace; font-size:.88em;
  background:var(--parch); border:1px solid var(--line-soft);
  border-radius:3px; padding:0 .25em;
}
a{color:#5a4a2a;text-decoration:none;border-bottom:1px dotted #a99570}
hr{border:0;border-top:1px solid var(--line-soft);margin:1.6em 0}

ul,ol{margin:.5em 0 .7em; padding-left:1.4em}
li{margin:.22em 0; break-inside:avoid; page-break-inside:avoid}
ul ul{margin:.15em 0 .2em}

/* ---- tables ---- */
.tablewrap{margin:.8em 0 1.1em; overflow-x:auto; break-inside:avoid; page-break-inside:avoid}
table{width:100%;border-collapse:collapse;font-size:9.3pt;line-height:1.6}
th,td{border:1px solid var(--line);padding:.38em .5em;text-align:left;vertical-align:top}
th{background:#efe6d2;font-family:"Hiragino Sans","Yu Gothic",sans-serif;font-weight:600;font-size:9pt}
tbody tr:nth-child(even) td{background:#fbf8f1}

/* ---- callouts ---- */
.callout{
  margin:.9em 0 1.1em; padding:.6em .85em; border-radius:4px;
  background:var(--note); border:1px solid var(--line-soft);
  border-left:4px solid var(--line); font-size:9.6pt;
  break-inside:avoid; page-break-inside:avoid;
}
.callout p{margin:.3em 0}
.callout.adv{background:var(--adv);border-left-color:var(--gold)}
.callout.adv::before{
  content:"上級ゲーム"; display:inline-block; margin:0 0 .35em;
  font-family:"Hiragino Sans","Yu Gothic",sans-serif; font-size:7.6pt;
  letter-spacing:.12em; color:#fff; background:var(--gold);
  padding:.12em .6em; border-radius:2px;
}
.callout.trivia{background:var(--trivia);border-left-color:#8fa07d;font-style:normal}
.callout table{font-size:8.9pt}
.callout .tablewrap{margin:.5em 0}

pre.diagram{
  background:var(--parch); border:1px solid var(--line-soft); border-radius:4px;
  padding:.7em .9em; font-family:ui-monospace,Menlo,monospace; font-size:8.4pt;
  line-height:1.5; overflow-x:auto; break-inside:avoid;
}

/* ---- cover ---- */
.cover{
  height:257mm; display:flex; flex-direction:column; justify-content:center;
  align-items:center; text-align:center; break-after:page; page-break-after:always;
  border:3px double var(--gold); padding:10mm; background:var(--parch);
}
.cover .orn{font-size:26pt;color:var(--gold);line-height:1;margin-bottom:6mm}
.cover h1{
  font-size:34pt; letter-spacing:.14em; margin:0 0 3mm; color:#2b1f14;
  font-family:"Hiragino Mincho ProN","Yu Mincho",serif; font-weight:600;
}
.cover .ja{font-size:14pt;letter-spacing:.35em;color:var(--ink-soft);margin-bottom:9mm}
.cover .rule{width:60%;border-top:1px solid var(--line);margin:0 0 9mm}
.cover .sub{font-size:13pt;letter-spacing:.1em;margin:0 0 12mm;color:#33261a}
.cover dl{font-size:10pt;color:var(--ink-soft);margin:0}
.cover dl div{margin:.28em 0}
.cover dt{display:inline;font-weight:600}
.cover dd{display:inline;margin:0 0 0 .5em}
.cover .foot{margin-top:14mm;font-size:8.6pt;color:#7d6c55;line-height:1.7}

/* ---- toc ---- */
.toc-page{break-after:page;page-break-after:always}
.toc-page > h2, .summary-page > h2{break-before:auto;page-break-before:auto}
nav.toc{font-family:"Hiragino Sans","Yu Gothic",sans-serif;font-size:9.6pt;text-align:left}
nav.toc ol{list-style:none;padding-left:0}
nav.toc > ol > li{
  margin:.45em 0; padding-left:1.6em; text-indent:-1.6em;
  break-inside:avoid;
}
nav.toc > ol > li > a{font-weight:600;color:#33261a}
nav.toc ul{list-style:none;padding-left:1.7em;margin:.18em 0 .45em;
  font-size:8.9pt;color:var(--ink-soft);text-indent:0;
  display:flex;flex-wrap:wrap;gap:0 1.1em}
nav.toc ul li::before{content:"– ";color:#b0a086}
nav.toc a{border:0}
nav.toc a:hover{border-bottom:1px dotted #a99570}

/* ---- summary ---- */
.summary-page{break-after:page;page-break-after:always}
.lead{font-size:13pt;font-family:"Hiragino Sans","Yu Gothic",sans-serif;
  margin:.2em 0 .9em;color:#2b1f14}
.src{font-size:8.2pt;color:#8a7a63;margin:.1em 0 1em;text-align:right}
.src-inline{font-size:8.2pt;color:#8a7a63;white-space:nowrap}

/* ---- appendix ---- */
#appendix-glossary{break-before:page;page-break-before:always}
.gloss-intro{font-size:9.6pt;color:var(--ink-soft)}
#appendix-glossary ~ h3{break-before:auto}
.appendix table td:first-child{
  font-family:ui-monospace,Menlo,monospace;font-size:8.6pt;white-space:nowrap;color:#4a3d2f
}

.endnote{margin-top:2em;padding-top:.8em;border-top:1px solid var(--line-soft);
  font-size:8.6pt;color:#7d6c55}

/* ---- figures / placeholder ---- */
.fig{margin:1em auto 1.3em;break-inside:avoid;page-break-inside:avoid;text-align:center}
.fig img{
  max-width:100%; height:auto; width:auto; border:1px solid var(--line); border-radius:3px;
  background:#fff; box-shadow:0 1px 3px rgba(60,45,20,.13);
}
.fig figcaption{
  font-family:"Hiragino Sans","Yu Gothic",sans-serif; font-size:8pt; color:#7d6c55;
  margin-top:.4em; line-height:1.5; text-align:center;
}
.size-full img{width:100%;max-height:198mm;object-fit:contain}
.size-wide img{width:68%;max-height:150mm}
.size-half img{width:52%;max-height:105mm}
.size-small img{width:30%;max-height:80mm}
.fig.placeholder .ph{
  display:flex; flex-direction:column; align-items:center; justify-content:center; gap:.3em;
  border:1.5px dashed var(--line); border-radius:4px; background:#faf7f0;
  color:#a08e70; padding:1.2em .8em;
}
.size-full.placeholder .ph{width:100%;height:52mm}
.size-wide.placeholder .ph{width:68%;height:42mm;margin:0 auto}
.size-half.placeholder .ph{width:52%;height:34mm;margin:0 auto}
.size-small.placeholder .ph{width:30%;height:24mm;margin:0 auto}
.ph-label{
  font-family:"Hiragino Sans","Yu Gothic",sans-serif; font-size:7.6pt; letter-spacing:.1em;
  background:var(--line-soft); color:#7d6c55; padding:.1em .7em; border-radius:2px;
}
.ph-path{font-family:ui-monospace,Menlo,monospace;font-size:8.4pt;color:#8a7a63}

/* ---- layout blocks（::: grid2 / grid3 / cards / flow） ---- */
.blk{margin:1.2em 0 1.5em;break-inside:avoid;page-break-inside:avoid}
.blk .cell>*:first-child{margin-top:0}
.blk .cell>*:last-child{margin-bottom:0}
.blk-grid2,.blk-grid3{display:grid;gap:.8em}
.blk-grid2{grid-template-columns:1fr 1fr}
.blk-grid3{grid-template-columns:repeat(3,1fr)}
.blk-grid2>.cell,.blk-grid3>.cell{
  border:1px solid var(--line-soft);border-radius:5px;padding:.7em .9em;background:var(--parch);
}
.blk-grid2>.cell h4,.blk-grid3>.cell h4{margin:0 0 .3em;color:var(--ink)}
.blk-grid2>.cell h4::before,.blk-grid3>.cell h4::before{content:none}
.blk-cards{display:grid;gap:.8em;grid-template-columns:repeat(auto-fill,minmax(46mm,1fr))}
.blk-cards>.cell{border:1px solid var(--line);border-radius:6px;padding:.8em 1em;background:#fff}
.blk-flow{display:flex;align-items:stretch;gap:.4em;flex-wrap:wrap}
.blk-flow>.cell{
  flex:1 1 0;min-width:26mm;border:1px solid var(--line);border-radius:5px;
  padding:.6em .7em;background:var(--parch);text-align:center;font-size:.92em;
}
.blk-flow>.arrow{display:flex;align-items:center;color:var(--gold);font-size:1.1em}
.blk-flow>.arrow::after{content:"▶"}

/* ---- round strip（::: round） ---- */
.blk-round{display:flex;gap:.55em;counter-reset:rstep;align-items:stretch;margin:1em 0 .5em}
.blk-round>.cell{
  flex:1 1 0;position:relative;border:1px solid var(--line-soft);border-radius:4px;
  padding:.45em .55em;background:var(--parch);font-size:.8em;line-height:1.5;color:var(--ink-soft);
}
.blk-round>.cell::before{
  counter-increment:rstep;content:counter(rstep);
  display:flex;align-items:center;justify-content:center;width:11pt;height:11pt;border-radius:50%;
  background:var(--line);color:#fff;font-family:"Hiragino Sans",sans-serif;font-size:7pt;font-weight:700;
  margin-bottom:.25em;
}
.blk-round>.cell+.cell::after{
  content:"▶";position:absolute;left:-.5em;top:50%;transform:translateY(-50%);
  color:var(--line);font-size:5.5pt;
}
.blk-round>.cell strong{display:block;font-family:"Hiragino Sans",sans-serif;font-size:1.05em;color:var(--ink)}
.blk-round>.cell p{margin:0}
.blk-round>.cell:nth-child(-n+2){background:#fff;border-color:var(--gold)}
.blk-round>.cell:nth-child(-n+2)::before{background:var(--gold)}
.round-note{font-family:"Hiragino Sans",sans-serif;font-size:.8em;color:var(--ink-soft);margin:0 0 1.2em}

/* ---- tiles（::: tiles） ---- */
.blk-tiles{display:grid;gap:.5em;grid-template-columns:repeat(6,1fr);margin:.8em 0 1.2em}
.blk-tiles>.cell{
  border:1px solid var(--line-soft);border-radius:4px;padding:.5em .3em;background:var(--parch);
  text-align:center;line-height:1.4;
}
.blk-tiles>.cell p{margin:0;font-family:"Hiragino Sans",sans-serif;font-size:.72em;color:var(--ink-soft)}
.blk-tiles>.cell .fig{margin:0 0 .25em}
.blk-tiles>.cell .fig img{width:auto;height:9mm;border:0;background:none;box-shadow:none}
.blk-tiles>.cell strong{display:block;font-family:"Hiragino Sans",sans-serif;font-size:.95em;color:var(--ink)}

/* ---- steps（::: steps） ---- */
.blk-steps{display:grid;gap:.4em;counter-reset:sstep;margin:.9em 0 1.3em}
.blk-steps>.cell{
  position:relative;padding:.45em .7em .5em 2.3em;
  border:1px solid var(--line-soft);border-radius:4px;background:var(--parch);
  font-size:.9em;line-height:1.65;break-inside:avoid;
}
.blk-steps>.cell::before{
  counter-increment:sstep;content:counter(sstep);
  position:absolute;left:.55em;top:.55em;
  display:flex;align-items:center;justify-content:center;width:13pt;height:13pt;border-radius:50%;
  background:var(--gold);color:#fff;font-family:"Hiragino Sans",sans-serif;font-size:8pt;font-weight:700;
}
.blk-steps>.cell strong{display:block;font-family:"Hiragino Sans",sans-serif;font-size:1.02em}
.blk-steps>.cell p{margin:0}

/* ---- components（::: comp）コンポーネント一覧 ---- */
.blk-comp{display:grid;gap:.45em;grid-template-columns:repeat(4,1fr);margin:.9em 0 1.3em}
.blk-comp>.cell{
  display:flex;flex-direction:column;align-items:center;text-align:center;
  border:1px solid var(--line-soft);border-radius:4px;background:var(--parch);
  padding:.5em .35em .45em;break-inside:avoid;page-break-inside:avoid;
}
.blk-comp>.cell .fig{
  display:flex;align-items:center;justify-content:center;
  width:100%;height:13mm;margin:0 0 .35em;
}
.blk-comp>.cell .fig img{
  width:auto;max-width:100%;max-height:13mm;border:0;background:none;box-shadow:none;
}
.blk-comp>.cell p{margin:0;font-family:"Hiragino Sans",sans-serif;font-size:.78em;line-height:1.5}
.blk-comp>.cell p+p{margin-top:.15em;font-size:.68em;color:var(--ink-soft);line-height:1.5}

/* ---- story cards（::: story）人物の肖像＋物語 ---- */
.blk-story{display:grid;gap:.7em;margin:1em 0 1.3em}
.blk-story>.cell{
  display:flex;align-items:flex-start;gap:.9em;
  border:1px solid var(--line-soft);border-left:3px solid var(--gold);border-radius:5px;
  padding:.75em .95em;background:var(--parch);break-inside:avoid;page-break-inside:avoid;
}
.blk-story>.cell>.fig{
  flex:0 0 auto;width:22mm;margin:.1em 0 0;order:-1;
}
.blk-story>.cell>.fig img{
  width:100%;height:auto;border:0;border-radius:50%;background:#fff;
  box-shadow:0 0 0 1pt var(--line-soft), 0 1px 3px rgba(60,45,20,.16);
}
.blk-story>.cell>.fig.placeholder .ph{min-height:22mm;border-radius:50%}
.blk-story>.cell h4{
  margin:0 0 .3em;font-size:1.06em;color:var(--ink);
  font-family:"Hiragino Mincho ProN","Yu Mincho",serif;letter-spacing:.04em;
}
.blk-story>.cell h4::before{content:none}
.blk-story>.cell .story-body{flex:1 1 auto;min-width:0}
.blk-story>.cell p{margin:0 0 .45em;font-size:.94em;line-height:1.85}
.blk-story>.cell p:last-child{margin-bottom:0}

/* ---- guild ring（6ギルドの並びと資源の流れ） ---- */
.guildring{
  margin:1em auto 1.4em;padding:1em .8em .8em;max-width:118mm;
  border:1px solid var(--line-soft);border-radius:6px;background:var(--parch);
  break-inside:avoid;page-break-inside:avoid;
}
.guildring ol{display:grid;grid-template-columns:repeat(6,1fr);gap:.35em;margin:0;padding:0;list-style:none}
.guildring li{
  position:relative;border:1px solid var(--line-soft);border-radius:4px;background:#fff;
  padding:.5em .25em .45em;text-align:center;line-height:1.4;
}
.guildring li .gr-no{
  display:block;font-family:"Hiragino Sans",sans-serif;font-size:.62em;font-weight:700;
  letter-spacing:.1em;color:#fff;background:var(--gold);border-radius:2px;
  width:1.5em;margin:0 auto .3em;
}
.guildring li .gr-name{
  display:block;font-family:"Hiragino Sans",sans-serif;font-size:.82em;font-weight:600;color:var(--ink);
}
.guildring li .gr-goods{display:block;font-size:.7em;color:var(--ink-soft);margin-top:.2em}
.guildring li+li::before{
  content:"";position:absolute;left:-.32em;top:50%;width:.32em;height:1pt;background:var(--line);
}
.guildring .gr-bar{
  display:flex;align-items:center;font-family:"Hiragino Sans",sans-serif;font-size:.74em;
  line-height:1.4;white-space:nowrap;
}
.guildring .gr-bar i{flex:1 1 auto;border-top:1pt solid currentColor;margin:0 .35em;font-style:normal}
.guildring .gr-bar b{font-weight:700;margin-right:.25em}
.guildring .gr-push{color:#7a5417;margin:0 .2em .45em}
.guildring .gr-pull{color:#48604a;margin:.45em .2em 0}
.guildring .gr-wrap{
  display:block;font-family:"Hiragino Sans",sans-serif;font-size:.7em;color:var(--ink-soft);
  text-align:center;margin-top:.6em;
}

/* ---- goods swatch（:食料: などのインライン記法） ---- */
.goods{
  display:inline-block;width:.72em;height:.72em;border-radius:1.5px;
  margin-right:.3em;vertical-align:-.01em;box-shadow:0 0 0 .6pt rgba(90,80,60,.55);
}
.goods-food{background:#9ac93c}
.goods-wood{background:#8a5a2b}
.goods-iron{background:#26262a}
.goods-sulfur{background:#f2ce1b}
.goods-saltpeter{background:#fcfbf6}

/* ---- print ---- */
@page{size:A4;margin:16mm 15mm 18mm}
@media print{
  html,body{background:#fff}
  body{font-size:9.6pt}
  .sheet{max-width:none;margin:0;padding:0}
  .cover{border-color:#a98f52}
  a{color:inherit;border:0}
  .tablewrap{overflow:visible}
  *{print-color-adjust:exact;-webkit-print-color-adjust:exact}
  .no-print{display:none}
}
@media screen and (max-width:700px){
  body{font-size:11pt}
  .sheet{padding:6mm 5mm 12mm}
  .cover{height:auto;padding:14mm 6mm}
  .cover h1{font-size:26pt}
}
"""

# ---------------- 画像 ----------------
IMAGE_ROOT = ""          # ビルダーが設定する（プロジェクトルート）
IMAGE_EMBED = True       # True なら base64 で埋め込む
WEB_ONLY = True          # False なら ::: web-only ブロックを出力しない（A4版用）
_IMG_CACHE = {}

_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
         ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml"}


def _data_uri(path):
    if path not in _IMG_CACHE:
        import base64
        ext = os.path.splitext(path)[1].lower()
        with open(path, "rb") as f:
            _IMG_CACHE[path] = "data:%s;base64,%s" % (
                _MIME.get(ext, "application/octet-stream"),
                base64.b64encode(f.read()).decode())
    return _IMG_CACHE[path]


def image_html(caption, src):
    """![キャプション|サイズ](パス) を figure に変換。

    サイズは full / wide / half / small（省略時 wide）。
    ファイルが無い場合は、何を用意すべきかを示すプレースホルダを描く。
    """
    size = "wide"
    if "|" in caption:
        caption, _, s = caption.rpartition("|")
        if s.strip() in ("full", "wide", "half", "small"):
            size = s.strip()
        else:
            caption = caption + "|" + s
    caption = caption.strip()
    path = os.path.join(IMAGE_ROOT, src) if IMAGE_ROOT else src
    cap = '<figcaption>%s</figcaption>' % inline(caption) if caption else ""
    if os.path.exists(path):
        uri = _data_uri(path) if IMAGE_EMBED else src
        return ('<figure class="fig size-%s"><img src="%s" alt="%s">%s</figure>'
                % (size, uri, html.escape(caption), cap))
    return ('<figure class="fig size-%s placeholder">'
            '<div class="ph"><span class="ph-label">画像スロット</span>'
            '<span class="ph-path">%s</span></div>%s</figure>'
            % (size, html.escape(src), cap))


# ---------------- CSS ----------------
def css(font_scale=0.75, extra=""):
    """基本CSS（＋追加CSS）を返す。pt 指定をすべて font_scale 倍する。"""
    c = BASE_CSS + extra
    return re.sub(r"(\d+(?:\.\d+)?)pt",
                  lambda m: "%gpt" % round(float(m.group(1)) * font_scale, 2), c)


# ---------------- 目次 ----------------
def toc_html(entries, extra_top=None):
    """[(level, id, text)] から2階層の目次を組む。extra_top は末尾に足す (id, text, [(id,text)...])"""
    o = ['<nav class="toc"><ol>']
    open_sub = False
    for lvl, sid, txt in entries:
        if lvl == 2:
            if open_sub:
                o.append("</ul>"); open_sub = False
            o.append('<li><a href="#%s">%s</a>' % (sid, txt))
        elif lvl == 3:
            if not open_sub:
                o.append("<ul>"); open_sub = True
            o.append('<li><a href="#%s">%s</a></li>' % (sid, txt))
    if open_sub:
        o.append("</ul>")
    if extra_top:
        for sid, txt, subs in extra_top:
            o.append('<li><a href="#%s">%s</a>' % (sid, txt))
            if subs:
                o.append("<ul>")
                o += ['<li><a href="#%s">%s</a></li>' % (s, t) for s, t in subs]
                o.append("</ul>")
            o.append("</li>")
    o.append("</ol></nav>")
    return "\n".join(o)


# ---------------- 文書 ----------------
def document(title, css_text, body):
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{css_text}</style>
</head>
<body>
<div class="sheet">
{body}
</div>
</body>
</html>
"""
