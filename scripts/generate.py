#!/usr/bin/env python3
"""research/candidates.json から、選んだ商品で docs/index.html を生成する（API呼び出しなし）。"""
from __future__ import annotations

import html
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sitemap  # noqa: E402
from safety import (check_items_have_affiliate, docs_dir, esc, json_for_script, orphan_blog_pages,  # noqa: E402
                    GUIDE_PAGES, hold_site_lock, is_publishable, publishable_posts, warn, write_all)

ROOT = Path(__file__).resolve().parent.parent
SITE_NAME = "Refind travel"
TAGLINE = "実際に泊まった宿を、写真と動画でまるごと紹介する旅のサイト"
GOODS_TAGLINE = "旅行の荷物と準備を、ちょっとラクにするグッズ集"
SITE_URL = "https://garagerefind-create.github.io/travel-goods/"
GOOGLE_SITE_VERIFICATION = "SzZWEITRdzKd3c99CG40kZVERlz_qep6-tLqyId-0cs"
GA_MEASUREMENT_ID = "G-E5KN18EGMZ"

GA_SNIPPET = """  <script async src="https://www.googletagmanager.com/gtag/js?id={id}"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{ dataLayer.push(arguments); }}
    gtag('js', new Date());
    gtag('config', '{id}');
  </script>"""

PROMO = re.compile(r"【[^】]*】|＼[^／]*／|★[^★]*★|\[[^\]]*\]|《[^》]*》|「[^」]*」")

HERO_HTML = '  <div class="hero"><img src="refind-travel-header.jpg" alt="Refind Travel — まだ知らない、好きな場所を見つけに行こう" width="1536" height="576" loading="eager"></div>'
SOCIAL_LINKS = [
    ("TikTok", "https://www.tiktok.com/@garagerefind2023", "宿の動画はここがメイン。アプリからそのまま空室チェックと予約ができます"),
    ("Instagram", "https://www.instagram.com/refind.travel/", "リールで宿の雰囲気を。ハイライトに宿ごとの予約リンクをまとめています"),
    ("YouTube", "https://www.youtube.com/@refindtravel", "ショート動画で宿をサクッと紹介"),
    ("Threads", "https://www.threads.com/@refind.travel", "旅のゆるい話と、新しく泊まった宿のお知らせ"),
    ("X", "https://x.com/refindtravel", "新しい宿泊記の更新情報"),
    ("note", "https://note.com/refindtravel", "泊まった宿の正直な感想"),
]
SOCIAL_HTML = ('    <p class="footer-social-title">Refind travel をフォロー</p>\n'
               '    <ul class="footer-social">' + "".join(
                   f'<li><a href="{url}" target="_blank" rel="noopener me">{name}</a></li>'
                   for name, url, _ in SOCIAL_LINKS) + '</ul>')
FOOTER_LINKS_HTML = SOCIAL_HTML + "\n" + ('    <p class="footer-links"><a href="about.html">運営者情報</a> '
                     '<a href="privacy.html">プライバシーポリシー</a> '
                     '<a href="affiliate.html">アフィリエイトについて</a></p>')


def clean_name(name: str, limit: int = 46) -> str:
    n = PROMO.sub(" ", name)
    n = re.sub(r"\s+", " ", n).strip()
    return n if len(n) <= limit else n[:limit].rstrip() + "…"


def image_of(it: dict) -> str:
    imgs = it.get("mediumImageUrls") or []
    img = imgs[0] if imgs else ""
    if isinstance(img, dict):
        img = img.get("imageUrl", "")
    return img.split("?")[0] + "?_ex=400x400" if img else ""


def card(it: dict, name: str, desc: str = "", for_whom: str = "", used: dict | None = None) -> str:
    url = html.escape(it.get("affiliateUrl") or it["itemUrl"])
    name = html.escape(name)
    used = used or {}
    badge = '<p class="used-badge">✓ 実際に使っています</p>' if used.get("is_used") else ""
    for_whom_html = f'<p class="for-whom">🎯 {html.escape(for_whom)}</p>' if for_whom else ""
    return f"""        <li class="card">
          <a href="{url}" target="_blank" rel="noopener sponsored nofollow"><img src="{html.escape(image_of(it))}" alt="{name}" loading="lazy"></a>
          <div class="body">
            {badge}
            <h3>{name}</h3>
            <p class="desc">{html.escape(desc)}</p>
            {for_whom_html}
            <p class="meta">★{it['reviewAverage']}（レビュー{int(it['reviewCount']):,}件）</p>
            <p class="shop">{html.escape(it['shopName'])}</p>
            <p class="price">¥{int(it['itemPrice']):,}</p>
            <a class="btn" href="{url}" target="_blank" rel="noopener sponsored nofollow">楽天市場で見る</a>
          </div>
        </li>"""


# 「目的から探す」の項目。(アイコン, ラベル, リンク先)
# リンク先は、今あるページの中でいちばん近いものを選んでいる。
# 旅行撮影・犬連れ旅行・荷物を減らすは、それぞれ対応する体験記の公開に
# 合わせて更新済み。
PURPOSES = [
    ("🗾", "国内旅行", "domestic-packing-list.html"),
    ("✈️", "海外旅行", "packing-checklist.html"),
    ("♨️", "ホテル・温泉旅行", "goods.html#hanger-laundry"),
    ("💺", "移動を快適にする", "goods.html#neckpillow"),
    ("🎒", "荷物を減らす", "blog-reduce-luggage-1night2days.html"),
    ("🔋", "スマホ・充電", "goods.html#battery"),
    ("📷", "旅行撮影", "blog-iphone-travel-video.html"),
    ("🐶", "犬連れ旅行", "blog-dog-travel-1night2days.html"),
]


def _is_published_href(href: str) -> bool:
    """「目的から探す」のリンク先が、下書き・未来日・一覧から外れた記事でないか。"""
    page = href.split("#", 1)[0]
    if page.startswith("blog-") and page.endswith(".html"):
        return page[len("blog-"):-len(".html")] in {p["slug"] for p in load_blog_posts()}
    if page in GUIDE_PAGES:
        # ガイド記事は articles.json に登録され、公開対象のときだけリンクする（一覧から消したら出さない）
        articles_path = ROOT / "research" / "articles.json"
        articles = json.loads(articles_path.read_text(encoding="utf-8")) if articles_path.exists() else []
        return any(a["path"] == page and is_publishable(a, page) for a in articles)
    return True


def purpose_finder_html(base: str = "") -> str:
    """トップページ上部の「目的から探す」エリア。base はリンク先の先頭に付ける（記事ページ等からの利用は今のところ想定していない）。

    ※ 2026-10 時点ではどのページからも呼ばれていない。使う場合も、公開対象外の記事へのリンクは出さない。
    """
    items = "\n".join(
        f'        <li><a href="{esc(base + href)}"><span class="purpose-icon">{icon}</span>{esc(label)}</a></li>'
        for icon, label, href in PURPOSES if _is_published_href(href)
    )
    return f"""    <section class="purpose-finder">
      <h2>目的から探す</h2>
      <p class="lead">旅のスタイルから、記事やおすすめグッズをまとめて見られます。</p>
      <ul class="purpose-grid">
{items}
      </ul>
    </section>"""


def site_nav(base: str = "goods.html", blog_active: bool = False, active: str = "") -> str:
    """全ページ共通のヘッダーナビ。

    以前はカテゴリ一覧を全ページに並べていたが、宿泊記を主役にするため、
    ナビは「ホーム／宿泊記・旅行記／持ち物・グッズ」の3つにした。
    カテゴリ一覧は持ち物・グッズページ（goods.html）の中だけに出す。
    base 引数は互換のために残している（使っていない）。
    """
    if blog_active:
        active = "blog"
    items = [("home", "index.html", "ホーム"), ("blog", "blog.html", "宿泊記・旅行記"), ("goods", "goods.html", "持ち物・グッズ")]
    out = []
    for key, href, label in items:
        cls = ' class="active"' if key == active else ""
        out.append(f'<a href="{href}"{cls}>{label}</a>')
    return "".join(out)


def goods_category_nav() -> str:
    picks = json.loads((ROOT / "research" / "picks.json").read_text(encoding="utf-8"))
    return "".join(f'<a href="#{esc(p["id"])}">{esc(p["title"])}</a>' for p in picks if not p.get("hidden_from_index"))


def article_json_ld(*, title: str, desc: str, page_url: str, published: str | None, updated: str | None) -> str:
    """記事・旅行記ページ用の Article 構造化データ(JSON-LD)。published が無ければ出さない。"""
    if not published:
        return ""
    data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": desc,
        "image": f"{SITE_URL}og-image.jpg",
        "author": {"@type": "Organization", "name": SITE_NAME},
        "publisher": {"@type": "Organization", "name": SITE_NAME, "url": SITE_URL, "sameAs": [u for _, u, _ in SOCIAL_LINKS]},
        "datePublished": published,
        "dateModified": updated or published,
        "mainEntityOfPage": {"@type": "WebPage", "@id": page_url},
    }
    return f'\n  <script type="application/ld+json">{json_for_script(data)}</script>'


def page_shell(*, title: str, desc: str, body: str, path: str, og_type: str = "article", extra_head: str = "",
               published: str | None = None, updated: str | None = None, og_image: str | None = None) -> str:
    """記事・旅行記など、商品一覧を持たないページ共通のテンプレート。

    published/updated (YYYY-MM-DD) を渡すと、Article構造化データ(JSON-LD)を出力する。
    """
    full_title_raw = f"{title} | {SITE_NAME}"
    page_url = f"{SITE_URL}{path}"
    blog_active = path.startswith("blog")
    og_img = esc(f"{SITE_URL}{og_image}" if og_image else f"{SITE_URL}og-image.jpg")
    json_ld_html = article_json_ld(title=full_title_raw, desc=desc, page_url=page_url,
                                    published=published, updated=updated) if og_type == "article" else ""
    # HTMLに埋め込む値はここでエスケープする（記事タイトルや説明文に " や < が入っても崩れないように）
    full_title, desc, page_url = esc(full_title_raw), esc(desc), esc(page_url)
    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{full_title}</title>
  <meta name="description" content="{desc}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{page_url}">
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="style.css">

  <meta property="og:type" content="{og_type}">
  <meta property="og:site_name" content="{SITE_NAME}">
  <meta property="og:locale" content="ja_JP">
  <meta property="og:title" content="{full_title}">
  <meta property="og:description" content="{desc}">
  <meta property="og:url" content="{page_url}">
  <meta property="og:image" content="{og_img}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{full_title}">
  <meta name="twitter:description" content="{desc}">
  <meta name="twitter:image" content="{og_img}">
{json_ld_html}
{extra_head}
{GA_SNIPPET.format(id=GA_MEASUREMENT_ID)}
</head>
<body>
{HERO_HTML}
  <header>
    <p class="site-name"><a href="index.html">{SITE_NAME}</a></p>
    <p class="ad">※ 当サイトは楽天アフィリエイトを利用した広告（PR）を含みます。</p>
    <nav>{site_nav("goods.html", blog_active, active="blog" if blog_active else "")}</nav>
  </header>
  <main>
{body}
  </main>
  <footer>
    <p>記事の内容は{date.today():%Y年%m月%d日}時点の情報です。ルールや規定、商品の内容は変わることがあるため、必ず公式情報でご確認ください。</p>
{FOOTER_LINKS_HTML}
    <p><a href="index.html">← {SITE_NAME} トップへ戻る</a></p>
  </footer>
</body>
</html>
"""


def product_ld(it: dict, name: str, position: int) -> dict:
    url = it.get("affiliateUrl") or it["itemUrl"]
    return {
        "@type": "ListItem",
        "position": position,
        "item": {
            "@type": "Product",
            "name": name,
            "image": image_of(it),
            "url": url,
            "offers": {
                "@type": "Offer",
                "price": int(it["itemPrice"]),
                "priceCurrency": "JPY",
                "availability": "https://schema.org/InStock",
                "url": url,
            },
            "aggregateRating": {
                "@type": "AggregateRating",
                "ratingValue": it["reviewAverage"],
                "reviewCount": int(it["reviewCount"]),
            },
        },
    }


# 宿の型。宿泊記（blog_posts.json の persona）と同じ表記にする。
PERSONAS = [
    ("anniv", "記念日・ご褒美", "非日常の特別な宿"),
    ("dog", "犬連れ", "愛犬と泊まれる宿"),
    ("value", "コスパ・ビジホ", "安くて便利な宿"),
    ("family", "ファミリー・グループ", "みんなで泊まれる宿"),
    ("solo", "一人旅・ワーケーション", "ひとりで落ち着ける宿"),
]


def load_blog_posts() -> list[dict]:
    path = ROOT / "research" / "blog_posts.json"
    posts = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    # 下書き（status: draft）と公開日が未来の記事はトップに出さない
    return sorted(publishable_posts(posts), key=lambda p: p["published"], reverse=True)


def stay_card(p: dict) -> str:
    persona = f'<span class="stay-type">{html.escape(p["persona"])}</span>' if p.get("persona") else ""
    return f"""        <li class="stay-card">
          <a href="blog-{p['slug']}.html">
            <img src="{html.escape(p['cover'])}" alt="{html.escape(p['title'])}" loading="lazy">
            <span class="stay-body">{persona}
              <span class="stay-title">{html.escape(p['title'])}</span>
              <span class="stay-desc">{html.escape(p.get('excerpt', ''))}</span>
            </span>
          </a>
        </li>"""


def build_home() -> str:
    posts = load_blog_posts()
    stays = [p for p in posts if p.get("cover")]
    others = [p for p in posts if not p.get("cover")]
    stays_html = ("\n".join(stay_card(p) for p in stays[:6]) if stays else
                  '        <li class="stay-empty">宿泊記は準備中です。</li>')
    counts = {name: sum(1 for p in stays if p.get("persona") == name) for _, name, _ in PERSONAS}
    personas_html = "\n".join(
        f'        <li><a href="blog.html#{key}"><span class="p-name">{name}</span><span class="p-note">{note}</span>'
        f'<span class="p-count">{counts[name]}件</span></a></li>' if counts[name] else
        f'        <li class="soon"><span class="p-name">{name}</span><span class="p-note">{note}</span><span class="p-count">準備中</span></li>'
        for key, name, note in PERSONAS)
    tips_html = "\n".join(
        f'        <li><a href="blog-{p["slug"]}.html">{html.escape(p["title"])}</a></li>' for p in others)
    desc = f"{TAGLINE}。記念日のご褒美宿から犬連れOKの宿、コスパのいいビジネスホテルまで、実際に泊まった感想を紹介します。"
    title = f"{SITE_NAME}｜泊まってよかった宿の宿泊記と旅の持ち物"
    cover = esc(f"{SITE_URL}{stays[0]['cover']}" if stays else f"{SITE_URL}og-image.jpg")
    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <meta name="description" content="{desc}">
  <meta name="robots" content="index, follow">
  <meta name="google-site-verification" content="{GOOGLE_SITE_VERIFICATION}">
  <link rel="canonical" href="{SITE_URL}">
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="style.css">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="{SITE_NAME}">
  <meta property="og:locale" content="ja_JP">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{desc}">
  <meta property="og:url" content="{SITE_URL}">
  <meta property="og:image" content="{cover}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title}">
  <meta name="twitter:description" content="{desc}">
  <meta name="twitter:image" content="{cover}">
  <script type="application/ld+json">{json_for_script({"@context": "https://schema.org", "@graph": [{"@type": "WebSite", "name": SITE_NAME, "url": SITE_URL}, {"@type": "Organization", "name": SITE_NAME, "url": SITE_URL, "logo": f"{SITE_URL}favicon.svg", "sameAs": [u for _, u, _ in SOCIAL_LINKS]}]})}</script>
{GA_SNIPPET.format(id=GA_MEASUREMENT_ID)}
</head>
<body class="home">
{HERO_HTML}
  <header>
    <h1>{SITE_NAME}</h1>
    <p>{TAGLINE}</p>
    <p class="ad">※ 当サイトはアフィリエイト広告（PR）を含みます。</p>
    <nav>{site_nav(active="home")}</nav>
  </header>
  <main>
    <section class="stays">
      <h2>最新の宿泊記</h2>
      <p class="lead">実際に泊まって、写真と動画で全部撮ってきた宿です。</p>
      <ul class="stay-grid">
{stays_html}
      </ul>
      <p class="more"><a href="blog.html">宿泊記・旅行記をすべて見る →</a></p>
    </section>
    <section class="personas">
      <h2>旅のスタイルから探す</h2>
      <p class="lead">あなたの旅行に合う宿を、タイプ別にまとめています。</p>
      <ul class="persona-grid">
{personas_html}
      </ul>
    </section>
    <section class="goods-entry">
      <h2>旅の持ち物・ノウハウ</h2>
      <ul class="tip-list">
{tips_html}
        <li><a href="domestic-packing-list.html">国内旅行 持ち物リスト</a></li>
        <li><a href="packing-checklist.html">初めての海外旅行 持ち物リスト</a></li>
      </ul>
      <p class="more"><a href="goods.html">旅の持ち物・グッズを見る →</a></p>
    </section>
    <section class="intro">
      <h2>このサイトについて</h2>
      <p>Refind travel は、実際に泊まった宿を、撮影した写真と動画でまるごと紹介するサイトです。1軒の宿で何十本も動画を撮って、部屋・お風呂・食事・まわりの景色まで、泊まる前に知りたいところを全部見せます。</p>
      <p>宿泊記には、楽天トラベルなどの予約ページへのリンクを載せています。料金や空室、プランの内容は変わるので、予約の前にリンク先で最新の情報を確認してください。</p>
    </section>
  </main>
  <footer>
{FOOTER_LINKS_HTML}
    <p><a href="https://developers.rakuten.com/" target="_blank" rel="noopener">Supported by Rakuten Developers</a></p>
  </footer>
</body>
</html>
"""


def main() -> None:
    _lock = hold_site_lock(ROOT)  # noqa: F841  同時に書き換えないためのロック（プロセス終了まで保持）
    picks_all = json.loads((ROOT / "research" / "picks.json").read_text(encoding="utf-8"))
    # hidden_from_index の付いたカテゴリ（例: 特定の記事だけで使う商品）は、トップページには出さない
    picks = [s for s in picks_all if not s.get("hidden_from_index")]
    items = json.loads((ROOT / "research" / "items.json").read_text(encoding="utf-8"))
    meta = json.loads((ROOT / "research" / "meta.json").read_text(encoding="utf-8"))
    data_date = date.fromisoformat(meta["updated"])
    nav = site_nav(active="goods")
    body = []
    ld_items = []
    position = 0
    missing = [i["itemCode"] for sec in picks for i in sec["items"] if i["itemCode"] not in items]
    if missing:
        sys.exit(f"items.json に無い商品コードが picks.json にあります（何も書き込まずに中止）: {', '.join(missing)}")
    check_items_have_affiliate(items, [i["itemCode"] for sec in picks for i in sec["items"]], "持ち物・グッズページの生成")
    for sec in picks:
        sid, title, lead = esc(sec["id"]), esc(sec["title"]), esc(sec["lead"])
        tips = "\n".join(f"          <li>{html.escape(t)}</li>" for t in sec.get("tips", []))
        cards_data = [(items[i["itemCode"]], i["name"], i.get("desc", ""), i.get("for_whom", ""), i.get("used"))
                      for i in sec["items"]]
        for it, n, _, _, _ in cards_data:
            position += 1
            ld_items.append(product_ld(it, n, position))
        body.append(f"""    <section id="{sid}">
      <h2>{title}</h2>
      <p class="lead">{lead}</p>
      <div class="tips">
        <h3>選び方のポイント</h3>
        <ul>
{tips}
        </ul>
      </div>
      <ul class="grid">
{chr(10).join(card(i, n, d, fw, u) for i, n, d, fw, u in cards_data)}
      </ul>
    </section>""")
    any_used = any(i.get("used", {}).get("is_used") for sec in picks for i in sec["items"])
    used_note = ("一部の商品は、実際に旅行で使用したうえで紹介しています。商品カードの「実際に使っています」のバッジが目印です。"
                 if any_used else
                 "掲載している商品は、私たちが実際に使って確かめたものではありません。商品ページの情報とレビューをもとに紹介しています。")
    json_ld = json_for_script(
        {"@context": "https://schema.org", "@type": "ItemList", "name": f"{SITE_NAME} 掲載商品",
         "itemListElement": ld_items},
    )
    full_title = f"旅の持ち物・グッズ | {SITE_NAME}"
    full_desc = f"{GOODS_TAGLINE}。バックパック、スーツケース、圧縮袋、モバイルバッテリーなど、楽天市場のレビューをもとに厳選して紹介します。"
    page = f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{full_title}</title>
  <meta name="description" content="{full_desc}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{SITE_URL}goods.html">
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="style.css">

  <meta property="og:type" content="website">
  <meta property="og:site_name" content="{SITE_NAME}">
  <meta property="og:locale" content="ja_JP">
  <meta property="og:title" content="{full_title}">
  <meta property="og:description" content="{full_desc}">
  <meta property="og:url" content="{SITE_URL}goods.html">
  <meta property="og:image" content="{SITE_URL}og-image.jpg">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{full_title}">
  <meta name="twitter:description" content="{full_desc}">
  <meta name="twitter:image" content="{SITE_URL}og-image.jpg">

  <script type="application/ld+json">{json_ld}</script>

{GA_SNIPPET.format(id=GA_MEASUREMENT_ID)}
</head>
<body class="goods">
{HERO_HTML}
  <header>
    <p class="site-name"><a href="index.html">{SITE_NAME}</a></p>
    <p class="ad">※ 当サイトは楽天アフィリエイトを利用した広告（PR）を含みます。</p>
    <nav>{nav}</nav>
  </header>
  <main>
    <section class="intro">
      <h1 class="page-title">旅の持ち物・グッズ</h1>
      <nav class="cat-nav">{goods_category_nav()}</nav>
      <p>旅の準備で迷いやすいグッズを、楽天市場の商品からまとめて紹介しています。荷物を入れるバッグから、荷造り、電源、移動中の快適グッズまで、{len(picks)}個のカテゴリに分けました。</p>
      <p><strong>商品の選び方：</strong>楽天市場の在庫があり、レビュー評価が4.0以上で、レビューが30件以上ある商品を候補にしています。そこから、価格帯やタイプが偏らないように選びました。</p>
      <p>{used_note} 仕様や在庫は、購入前にリンク先でご確認ください。</p>
      <p class="cta">
        <a href="packing-checklist.html">初めての海外旅行 持ち物リストを読む →</a>
        <a href="domestic-packing-list.html">国内旅行 持ち物リストを読む →</a>
      </p>
    </section>
{chr(10).join(body)}
  </main>
  <footer>
    <p>掲載の価格・評価・レビュー件数は{data_date:%Y年%m月%d日}時点の楽天市場の情報です。変動する場合があるため、購入前に必ずリンク先でご確認ください。</p>
    <p>機内持ち込みや電池容量の可否、変換プラグの対応地域は、商品・航空会社・渡航先によって異なります。ご利用の航空会社や渡航先の規定を確認してください。</p>
{FOOTER_LINKS_HTML}
    <p><a href="https://developers.rakuten.com/" target="_blank" rel="noopener">Supported by Rakuten Developers</a></p>
  </footer>
</body>
</html>
"""
    # 2ページとも作り終えてから書き込む（途中で失敗したとき goods と index が新旧混在にならないように）
    home = build_home()
    write_all({docs_dir(ROOT) / "goods.html": page, docs_dir(ROOT) / "index.html": home})

    sitemap.build()
    favicon = docs_dir(ROOT) / "favicon.svg"
    if not favicon.exists():
        favicon.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            '<rect width="64" height="64" rx="14" fill="#0b7285"/>'
            '<rect x="20" y="16" width="24" height="34" rx="4" fill="#fff"/>'
            '<rect x="27" y="10" width="10" height="8" rx="2" fill="#fff"/>'
            "</svg>",
            encoding="utf-8",
        )
    orphans = orphan_blog_pages(docs_dir(ROOT), {q["slug"] for q in load_blog_posts()})
    if orphans:
        warn("公開対象に無いのに docs/ に残っているページ（削除はしていません。公開を止めるなら手動で確認）: " + ", ".join(orphans))
    print("生成しました: docs/index.html, docs/goods.html, robots.txt, sitemap.xml, favicon.svg")


if __name__ == "__main__":
    main()
