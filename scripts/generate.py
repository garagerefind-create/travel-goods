#!/usr/bin/env python3
"""research/candidates.json から、選んだ商品で docs/index.html を生成する（API呼び出しなし）。"""
import html
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE_NAME = "たびのおとも"
TAGLINE = "旅行の荷物と準備を、ちょっとラクにするグッズ集"

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


def card(it: dict, name: str) -> str:
    url = html.escape(it.get("affiliateUrl") or it["itemUrl"])
    name = html.escape(name)
    return f"""        <li class="card">
          <a href="{url}" target="_blank" rel="noopener sponsored nofollow"><img src="{html.escape(image_of(it))}" alt="{name}" loading="lazy"></a>
          <div class="body">
            <h3>{name}</h3>
            <p class="meta">★{it['reviewAverage']}（レビュー{int(it['reviewCount']):,}件）</p>
            <p class="shop">{html.escape(it['shopName'])}</p>
            <p class="price">¥{int(it['itemPrice']):,}</p>
            <a class="btn" href="{url}" target="_blank" rel="noopener sponsored nofollow">楽天市場で見る</a>
          </div>
        </li>"""


def main() -> None:
    picks = json.loads((ROOT / "research" / "picks.json").read_text(encoding="utf-8"))
    items = json.loads((ROOT / "research" / "items.json").read_text(encoding="utf-8"))
    meta = json.loads((ROOT / "research" / "meta.json").read_text(encoding="utf-8"))
    data_date = date.fromisoformat(meta["updated"])
    nav = "".join(f'<a href="#{i}">{t}</a>' for i, t in ((x["id"], x["title"]) for x in picks))
    body = []
    for sec in picks:
        sid, title, lead = sec["id"], sec["title"], sec["lead"]
        cards_data = [(items[i["itemCode"]], i["name"]) for i in sec["items"]]
        body.append(f"""    <section id="{sid}">
      <h2>{title}</h2>
      <p class="lead">{lead}</p>
      <ul class="grid">
{chr(10).join(card(i, n) for i, n in cards_data)}
      </ul>
    </section>""")
    page = f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{SITE_NAME} | 旅行グッズ紹介</title>
  <meta name="description" content="{TAGLINE}。バックパック、スーツケース、圧縮袋、モバイルバッテリーなど。">
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header>
    <h1>{SITE_NAME}</h1>
    <p>{TAGLINE}</p>
    <p class="ad">※ 当サイトは楽天アフィリエイトを利用した広告（PR）を含みます。</p>
    <nav>{nav}</nav>
  </header>
  <main>
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
    print("生成しました: docs/index.html")


if __name__ == "__main__":
    main()
