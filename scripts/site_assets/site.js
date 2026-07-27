/* Feudum 日本語ドキュメント — サイドバー開閉・表示切替・全文検索 */
(function () {
  "use strict";

  // ---------- サイドバー（狭い画面） ----------
  var burger = document.getElementById("burger");
  var backdrop = document.getElementById("backdrop");
  function closeNav() { document.body.classList.remove("nav-open"); }
  if (burger) burger.addEventListener("click", function () {
    document.body.classList.toggle("nav-open");
  });
  if (backdrop) backdrop.addEventListener("click", closeNav);

  // ---------- サイドバーの開閉（ドキュメント単位） ----------
  // 現在のドキュメントはビルド時に開いた状態で出力される。
  // 手で開閉したものは localStorage に残し、ページを移動しても保つ。
  var NAVKEY = "feudum-nav";
  var navState = {};
  try { navState = JSON.parse(localStorage.getItem(NAVKEY)) || {}; } catch (e) { navState = {}; }

  var docItems = [].slice.call(document.querySelectorAll("ul.nav > li.nav-doc"));
  docItems.forEach(function (li) {
    var id = li.getAttribute("data-doc");
    var tog = li.querySelector(".doc-tog");
    if (id in navState) li.classList.toggle("open", !!navState[id]);
    if (tog) {
      tog.setAttribute("aria-expanded", li.classList.contains("open") ? "true" : "false");
      tog.addEventListener("click", function (ev) {
        ev.preventDefault();
        var open = !li.classList.contains("open");
        li.classList.toggle("open", open);
        tog.setAttribute("aria-expanded", open ? "true" : "false");
        navState[id] = open;
        try { localStorage.setItem(NAVKEY, JSON.stringify(navState)); } catch (e) {}
      });
    }
  });

  // ---------- ライト / ダーク ----------
  var root = document.documentElement;
  var saved = localStorage.getItem("feudum-theme");
  if (saved) root.setAttribute("data-theme", saved);
  var tbtn = document.getElementById("theme");
  if (tbtn) tbtn.addEventListener("click", function () {
    var now = root.getAttribute("data-theme");
    var dark = now === "dark" ||
      (now === "auto" && window.matchMedia("(prefers-color-scheme: dark)").matches);
    var next = dark ? "light" : "dark";
    root.setAttribute("data-theme", next);
    localStorage.setItem("feudum-theme", next);
  });

  // ---------- ページ内目次の追従 ----------
  var links = [].slice.call(document.querySelectorAll(".ptoc a"));
  if (links.length) {
    var targets = links.map(function (a) {
      return document.getElementById(decodeURIComponent(a.getAttribute("href").slice(1)));
    });
    var onScroll = function () {
      var y = window.scrollY + 90, cur = 0;
      for (var i = 0; i < targets.length; i++) {
        if (targets[i] && targets[i].offsetTop <= y) cur = i;
      }
      links.forEach(function (a, i) { a.classList.toggle("active", i === cur); });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  // ---------- 全文検索 ----------
  var q = document.getElementById("q");
  var box = document.getElementById("results");
  if (!q || !box) return;

  var index = null, loading = false, sel = -1;

  // インデックスは <script> で読み込む（file:// でも動くようにするため）
  var queue = [];
  function load(cb) {
    if (index) return cb();
    queue.push(cb);
    if (loading) return;
    loading = true;
    var s = document.createElement("script");
    s.src = "assets/search.js";
    s.onload = function () {
      index = window.FEUDUM_INDEX || [];
      loading = false;
      queue.splice(0).forEach(function (f) { f(); });
    };
    s.onerror = function () {
      loading = false;
      box.hidden = false;
      box.innerHTML = '<div class="r-none">検索インデックスを読み込めませんでした</div>';
    };
    document.head.appendChild(s);
  }

  function esc(s) { return s.replace(/[&<>"]/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  function snippet(text, term) {
    var i = text.toLowerCase().indexOf(term.toLowerCase());
    if (i < 0) return "";
    var s = Math.max(0, i - 28), e = Math.min(text.length, i + term.length + 52);
    return (s > 0 ? "…" : "") +
      esc(text.slice(s, i)) + "<mark>" + esc(text.slice(i, i + term.length)) + "</mark>" +
      esc(text.slice(i + term.length, e)) + (e < text.length ? "…" : "");
  }

  function search(term) {
    var t = term.trim();
    if (!t) { box.hidden = true; box.innerHTML = ""; return; }
    var lo = t.toLowerCase(), hits = [];
    for (var i = 0; i < index.length; i++) {
      var p = index[i];
      var inTitle = p.t.toLowerCase().indexOf(lo) >= 0;
      var pos = p.x.toLowerCase().indexOf(lo);
      if (!inTitle && pos < 0) continue;
      hits.push({ p: p, score: (inTitle ? 0 : 1000) + (pos < 0 ? 0 : pos) });
    }
    hits.sort(function (a, b) { return a.score - b.score; });
    hits = hits.slice(0, 12);
    if (!hits.length) {
      box.hidden = false;
      box.innerHTML = '<div class="r-none">「' + esc(t) + '」は見つかりませんでした</div>';
      return;
    }
    box.hidden = false;
    box.innerHTML = hits.map(function (h) {
      return '<a href="' + h.p.u + '">' +
        '<div class="r-doc">' + esc(h.p.d) + "</div>" +
        '<div class="r-t">' + esc(h.p.t) + "</div>" +
        '<div class="r-x">' + snippet(h.p.x, t) + "</div></a>";
    }).join("");
    sel = -1;
  }

  var timer = null;
  q.addEventListener("input", function () {
    clearTimeout(timer);
    var v = q.value;
    timer = setTimeout(function () { load(function () { search(v); }); }, 110);
  });
  q.addEventListener("focus", function () { load(function () { if (q.value) search(q.value); }); });

  q.addEventListener("keydown", function (e) {
    var items = [].slice.call(box.querySelectorAll("a"));
    if (e.key === "Escape") { box.hidden = true; q.blur(); return; }
    if (!items.length) return;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      sel += e.key === "ArrowDown" ? 1 : -1;
      if (sel < 0) sel = items.length - 1;
      if (sel >= items.length) sel = 0;
      items.forEach(function (a, i) { a.classList.toggle("sel", i === sel); });
      items[sel].scrollIntoView({ block: "nearest" });
    } else if (e.key === "Enter" && sel >= 0) {
      e.preventDefault();
      location.href = items[sel].getAttribute("href");
    }
  });

  document.addEventListener("click", function (e) {
    if (!e.target.closest(".searchbox")) box.hidden = true;
  });

  // "/" で検索へ
  document.addEventListener("keydown", function (e) {
    if (e.key === "/" && document.activeElement !== q) {
      e.preventDefault();
      document.body.classList.add("nav-open");
      q.focus();
    }
  });
})();
