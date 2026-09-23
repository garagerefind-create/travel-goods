#!/usr/bin/env python3
"""research/candidates.json から、選んだ商品で docs/index.html を生成する（API呼び出しなし）。"""
import html
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sitemap  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SITE_NAME = "たびのおとも"
TAGLINE = "旅行の荷物と準備を、ちょっとラクにするグッズ集"
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


def card(it: dict, name: str, desc: str = "") -> str:
    url = html.escape(it.get("affiliateUrl") or it["itemUrl"])
    name = html.escape(name)
    return f"""        <li class="card">
          <a href="{url}" target="_blank" rel="noopener sponsored nofollow"><img src="{html.escape(image_of(it))}" alt="{name}" loading="lazy"></a>
          <div class="body">
            <h3>{name}</h3>
            <p class="desc">{html.escape(desc)}</p>
            <p class="meta">★{it['reviewAverage']}（レビュー{int(it['reviewCount']):,}件）</p>
            <p class="shop">{html.escape(it['shopName'])}</p>
            <p class="price">¥{int(it['itemPrice']):,}</p>
            <a class="btn" href="{url}" target="_blank" rel="noopener sponsored nofollow">楽天市場で見る</a>
          </div>
        </li>"""


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


def main() -> None:
    picks = json.loads((ROOT / "research" / "picks.json").read_text(encoding="utf-8"))
    items = json.loads((ROOT / "research" / "items.json").read_text(encoding="utf-8"))
    meta = json.loads((ROOT / "research" / "meta.json").read_text(encoding="utf-8"))
    data_date = date.fromisoformat(meta["updated"])
    nav = "".join(f'<a href="#{i}">{t}</a>' for i, t in ((x["id"], x["title"]) for x in picks))
    body = []
    ld_items = []
    position = 0
    for sec in picks:
        sid, title, lead = sec["id"], sec["title"], sec["lead"]
        tips = "\n".join(f"          <li>{html.escape(t)}</li>" for t in sec.get("tips", []))
        cards_data = [(items[i["itemCode"]], i["name"], i.get("desc", "")) for i in sec["items"]]
        for it, n, _ in cards_data:
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
{chr(10).join(card(i, n, d) for i, n, d in cards_data)}
      </ul>
    </section>""")
    json_ld = json.dumps(
        {"@context": "https://schema.org", "@type": "ItemList", "name": f"{SITE_NAME} 掲載商品",
         "itemListElement": ld_items},
        ensure_ascii=False,
    )
    full_title = f"{SITE_NAME} | 旅行グッズ紹介"
    full_desc = f"{TAGLINE}。バックパック、スーツケース、圧縮袋、モバイルバッテリーなど、楽天市場のレビューをもとに厳選して紹介します。"
    page = f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{full_title}</title>
  <meta name="description" content="{full_desc}">
  <meta name="robots" content="index, follow">
  <meta name="google-site-verification" content="{GOOGLE_SITE_VERIFICATION}">
  <link rel="canonical" href="{SITE_URL}">
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="style.css">

  <meta property="og:type" content="website">
  <meta property="og:site_name" content="{SITE_NAME}">
  <meta property="og:locale" content="ja_JP">
  <meta property="og:title" content="{full_title}">
  <meta property="og:description" content="{full_desc}">
  <meta property="og:url" content="{SITE_URL}">
  <meta property="og:image" content="{SITE_URL}og-image.png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{full_title}">
  <meta name="twitter:description" content="{full_desc}">
  <meta name="twitter:image" content="{SITE_URL}og-image.png">

  <script type="application/ld+json">{json_ld}</script>

{GA_SNIPPET.format(id=GA_MEASUREMENT_ID)}
</head>
<body>
  <header>
    <h1>{SITE_NAME}</h1>
    <p>{TAGLINE}</p>
    <p class="ad">※ 当サイトは楽天アフィリエイトを利用した広告（PR）を含みます。</p>
    <nav>{nav}</nav>
  </header>
  <main>
    <section class="intro">
      <h2>このサイトについて</h2>
      <p>旅の準備で迷いやすいグッズを、楽天市場の商品からまとめて紹介しています。荷物を入れるバッグから、荷造り、電源、移動中の快適グッズまで、{len(picks)}個のカテゴリに分けました。</p>
      <p><strong>商品の選び方：</strong>楽天市場の在庫があり、レビュー評価が4.0以上で、レビューが30件以上ある商品を候補にしています。そこから、価格帯やタイプが偏らないように選びました。</p>
      <p>掲載している商品は、私たちが実際に使って確かめたものではありません。商品ページの情報とレビューをもとに紹介しています。仕様や在庫は、購入前にリンク先でご確認ください。</p>
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
    <p><a href="https://developers.rakuten.com/" target="_blank" rel="noopener">Supported by Rakuten Developers</a></p>
  </footer>
</body>
</html>
"""
    (ROOT / "docs" / "index.html").write_text(page, encoding="utf-8")

    sitemap.build()
    favicon = ROOT / "docs" / "favicon.svg"
    if not favicon.exists():
        favicon.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            '<rect width="64" height="64" rx="14" fill="#0b7285"/>'
            '<rect x="20" y="16" width="24" height="34" rx="4" fill="#fff"/>'
            '<rect x="27" y="10" width="10" height="8" rx="2" fill="#fff"/>'
            "</svg>",
            encoding="utf-8",
        )
    print("生成しました: docs/index.html, robots.txt, sitemap.xml, favicon.svg")


if __name__ == "__main__":
    main()
