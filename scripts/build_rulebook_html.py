# -*- coding: utf-8 -*-
"""日本語ルールブック → A4印刷向け HTML

    python3 scripts/build_rulebook_html.py   → dist/feudum-rulebook-ja.html

図版は原稿（docs/feudum-rulebook-ja.md）に ![...](figures/...) として直接書かれており、
mdbook が base64 で埋め込む。表紙だけはこのスクリプトが差し込む。
用語集は別冊（build_glossary_html.py）に分離してある。
"""
import os, re, sys, base64, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mdbook

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_SCALE = 0.75

# 主要な区切りだけ改ページ（紙を節約しつつ引きやすさを保つ）
NEWPAGE = {"1", "5", "9", "10", "12", "17", "18"}

IMGDIR = os.path.join(ROOT, "figures")
_b64 = {}


def data_uri(name):
    if name not in _b64:
        with open(os.path.join(IMGDIR, "fig-%s.jpg" % name), "rb") as f:
            _b64[name] = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()
    return _b64[name]


# ---------------- 図版まわりの追加CSS ----------------
FIG_CSS = r"""
/* ---- figures ---- */
.fig{margin:1em auto 1.3em;break-inside:avoid;page-break-inside:avoid;text-align:center}
.fig img{
  max-width:100%; height:auto; border:1px solid var(--line); border-radius:3px;
  background:#fff; box-shadow:0 1px 3px rgba(60,45,20,.13); width:auto;
}
.fig figcaption{
  font-family:"Hiragino Sans","Yu Gothic",sans-serif; font-size:8pt; color:#7d6c55;
  margin-top:.4em; line-height:1.5; text-align:center;
}
.size-full img{width:100%;max-height:198mm;object-fit:contain}
.size-wide img{width:68%;max-height:150mm}
.size-half img{width:52%;max-height:105mm}
.size-small img{width:30%;max-height:80mm}
.figrow{
  display:flex; flex-wrap:wrap; gap:.6em 1.4em; justify-content:center;
  align-items:flex-start; margin:1em 0 1.2em;
}
.figrow .fig{flex:1 1 42%; max-width:47%; margin:.2em 0 .6em}
.figrow .fig img{width:auto;max-width:100%;max-height:58mm}

/* ---- illustrated cover ---- */
.cover.art{display:block;padding:0;border:0;background:none;text-align:center}
.cover.art img{
  width:70%; max-height:170mm; object-fit:contain;
  border:1px solid var(--line); box-shadow:0 2px 8px rgba(60,45,20,.2);
}
.cover.art .band{
  margin:8mm auto 0; padding:6mm 8mm; max-width:78%;
  border-top:2px solid var(--gold); border-bottom:2px solid var(--gold);
  background:var(--parch);
}
"""

# ---------------- サマリー ----------------
SUMMARY = """
<h2 id="summary">このゲームについて（サマリー）</h2>

<p class="lead"><strong>Feudum（フューダム）</strong></p>

<p>Mark K. Swanson デザイン／Odd Bird Games 発行、2017年にKickstarterで資金調達された中世ファンタジーテーマの経済系ユーロゲームです。デザイナーはミズーリ大学の教授で、Kickstarter経由で世に出ました。アートは Justin Schultz による、黒い太線と沈んだ色調の表現主義的な絵柄で、独特の「おどろおどろしさ」があります。</p>

<p>タイトルはラテン語で「封土」、つまり封建領主から授けられた土地の意味。プレイヤーは追放され、わずかな小銭と食べ残ししか持たない身から、異国の地で名誉を取り戻そうとする——という設定で、<strong>崇敬点（vp）</strong>を最も稼いだ人が勝ちます。</p>
<p class="src">出典: Board Game Bliss</p>

<h3>基本構造</h3>
<ul>
<li>2〜5人（拡張・ソロ変種で1人〜）、プレイ時間おおむね3〜4時間</li>
<li>5つの「時代」を通じて、1手番あたり4アクションを最適化していく構成。実際のラウンド数は7〜10程度で、時代＝ラウンドではない点が要注意 <span class="src-inline">出典: Game Nerdz</span></li>
<li>全員が同じ11枚のアクションカードを持ち、各ラウンドの開始時に秘密裏に4枚を選んで残りは伏せる。以降、手番順に1枚ずつ出して解決していく（同時プロット＋アクションキュー）。各カードに基本／上級の2種類のアクションがあります <span class="src-inline">出典: Blogger</span></li>
<li>ポーンは6面ダイス型の駒で、6つの面がそれぞれ職業（農民・商人・錬金術師・騎士・貴族・修道士）を表し、どの職業を上に向けているかで能力が変わります <span class="src-inline">出典: SPACE-BIFF!</span></li>
</ul>

<h3>目玉となる「ギルド循環経済」</h3>

<p>盤面は6つの地域（海・島・森・砂漠・荒地・山）に分かれ、その両脇を6つのギルド（農民・商人・錬金術師・騎士・貴族・修道士）が挟みます。この6ギルドは一方向の輪としてつながっていて、農民が商品を商人に送り、商人が錬金術師を装備させ、錬金術師がクルド（火薬）を発明し、それが騎士を武装させ……という循環サイクルを回します（最終的に修道士から農民へ戻る）。</p>
<p class="src">出典: UltraBoardGames</p>

<p>ギルド内での地位は、ポーンの職業、フューダムの支配、複数の拠点の支配などで上がっていき、ギルドマスターや職人になると、資源をギルドに引き込む（pull）／押し出す（push）追加権限が得られ、点数を稼ぎつつ経済を動かせます。他人の押し込んだ資源を横取りするような絡みもあり、ここがこのゲーム最大の個性です。</p>

<h3>フューダムとリスク</h3>

<p>町を「王の印」を使ってフューダムに格上げできますが、フューダムの所有者は軍役によって王に忠誠を示さねばならず、怠れば不忠の罪に問われます。強力だが義務も重い、というジレンマ。加えて上級ルールではベヒモスやシーサーペントを手懐けて移動力にしたり他人のポーンを拘束したり、錬金術師ギルドで飛行機械や潜水艇を買って移動手段を広げたりできます。</p>
<p class="src">出典: Game Nerdz</p>

<h3>評判</h3>

<p>BGGのウェイト（複雑さ）は4.5前後で、事実上最重量級の一角。最も複雑で、最も個性的で、そして最も評価が二分するユーロゲームの一つという評判を得ています。アイコンだけで書かれたカードは初見では解読不能に近く、ルール説明そのものが一仕事、という声が日本のレビューでも目立ちます。逆にハマった人は「生涯のベスト」と言うタイプのゲームです。</p>
<p class="src">出典: Beastie Geeks</p>

<h3>版と拡張</h3>

<p>拡張は <em>Rudders &amp; Ramparts</em> をはじめ5本以上出ています。現在いちばん揃っているのは7周年記念の <em>Septennial Edition</em> で、<em>Alter Ego</em> 拡張、<em>The Queen's Army</em> 拡張（ソロ変種）、金属製のベヒモスなど多数のボーナスが同梱されています。</p>
<p class="src">出典: Odd Bird</p>

<p>初プレイなら、まず基本ゲーム（ベヒモス等なし）から入り、経験者にインストしてもらうのが現実的です。</p>
"""

# ---------------- 本文 ----------------
rule = open(os.path.join(ROOT, "docs", "feudum-rulebook-ja.md"), encoding="utf-8").read()
rule_body = rule[rule.index("\n## 1. "):]

toc = []
body_html = mdbook.convert(rule_body, collect=toc)


def mark_newpage(m):
    num = m.group(2).split(".")[0].strip()
    cls = ' class="newpage"' if num in NEWPAGE else ""
    return '<h2 id="%s"%s>%s</h2>' % (m.group(1), cls, m.group(2))


body_html = re.sub(r'<h2 id="([^"]+)">(.*?)</h2>', mark_newpage, body_html, flags=re.S)

TOC = mdbook.toc_html(toc)

# ---------------- 表紙 ----------------
CREDITS = """  <dl>
    <div><dt>デザイン</dt><dd>Mark Swanson</dd></div>
    <div><dt>アートワーク</dt><dd>Justin Schultz</dd></div>
    <div><dt>発行</dt><dd>Odd Bird Games &copy; 2017</dd></div>
    <div><dt>プレイ人数</dt><dd>2〜5人</dd></div>
    <div><dt>ゲームの長さ</dt><dd>5つの時代（通常7〜10ラウンド）</dd></div>
  </dl>
  <div class="foot">
    英語版ルールブック（Feudum Rulebook, 印刷ページ1〜25）からの非公式日本語訳<br>
    用語は別冊『Feudum 用語集』に準拠<br>
    A4印刷用レイアウト
  </div>"""

COVER = f"""<section class="cover art">
  <img src="{data_uri('cover')}" alt="Feudum 原書の表紙">
  <div class="band">
  <h1>FEUDUM</h1>
  <div class="ja">フューダム</div>
  <div class="sub">日本語ルールブック</div>
  </div>
{CREDITS}
</section>"""

BODY = f"""
{COVER}

<section class="toc-page">
<h2 id="toc">目次</h2>
{TOC}
</section>

<section class="summary-page">
{SUMMARY}
</section>

<section class="content">
{body_html}
</section>

<p class="endnote">
本書はPDF版英語ルールブックを構造化して翻訳したものです。軍役トラックの印字値、ギルドの拠点アイコン、カード記号5種は未確認です。該当箇所は本文中に注記しています。<br>
用語の対訳と定義は別冊『Feudum 用語集』にまとめています。<br>
&copy; 2017 Odd Bird Games. 本訳文は個人利用を目的とした非公式翻訳です。
</p>
"""

css = mdbook.css(FONT_SCALE, FIG_CSS)
out = os.path.join(ROOT, "dist", "feudum-rulebook-ja.html")
open(out, "w", encoding="utf-8").write(mdbook.document("Feudum 日本語ルールブック", css, BODY))
print("written:", out, len(open(out, encoding="utf-8").read()), "chars")
print("  h2:", sum(1 for l, s, t in toc if l == 2),
      " h3:", sum(1 for l, s, t in toc if l == 3),
      " figures:", body_html.count("<figure"))
