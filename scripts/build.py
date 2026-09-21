#!/usr/bin/env python3
"""楽天商品検索APIで商品を取得し、site/index.html を生成する。

使い方:
    export RAKUTEN_APP_ID=xxxx RAKUTEN_ACCESS_KEY=xxxx   # もしくは .env に書く
    python3 scripts/build.py
"""
import html
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEYWORD = "パッキングキューブ"
HITS = 10
DEFAULT_ORIGIN = "https://garagerefind-create.github.io"
ENDPOINT = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"


def load_dotenv(path: Path) -> None:
    """.env があれば読み込む（既存の環境変数は上書きしない）。"""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def fetch_items(app_id: str, access_key: str) -> list[dict]:
    params = {
        "applicationId": app_id,
        "accessKey": access_key,
        "keyword": KEYWORD,
        "hits": HITS,
        "format": "json",
        "formatVersion": 2,
        "imageFlag": 1,
    }
    url = f"{ENDPOINT}?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": "travel-goods-builder"}
    # アプリ登録の「許可されたウェブサイト」と一致する Origin が必要
    headers["Origin"] = os.environ.get("RAKUTEN_ORIGIN", DEFAULT_ORIGIN)
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            data = json.load(res)
    except urllib.error.HTTPError as e:
        sys.exit(f"APIエラー {e.code}: {e.read().decode('utf-8', 'replace')}")
    return data.get("Items") or data.get("items") or []


def normalize(item: dict) -> dict:
    item = item.get("Item", item)  # formatVersion 1/2 の両対応
    images = item.get("mediumImageUrls") or []
    img = images[0] if images else ""
    if isinstance(img, dict):
        img = img.get("imageUrl", "")
    return {
        "name": item.get("itemName", ""),
        "price": item.get("itemPrice", 0),
        "image": img.split("?")[0] + "?_ex=400x400" if img else "",
        "url": item.get("itemUrl", ""),
    }


def render(items: list[dict]) -> str:
    cards = []
    for it in items:
        cards.append(
            f"""      <li class="card">
        <a href="{html.escape(it['url'])}" target="_blank" rel="noopener sponsored">
          <img src="{html.escape(it['image'])}" alt="{html.escape(it['name'])}" loading="lazy">
        </a>
        <div class="body">
          <h2>{html.escape(it['name'])}</h2>
          <div class="price">¥{it['price']:,}</div>
          <a class="btn" href="{html.escape(it['url'])}" target="_blank" rel="noopener sponsored">楽天市場で見る</a>
        </div>
      </li>"""
        )
    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>パッキングキューブ おすすめ{len(items)}選 | 旅行グッズ紹介</title>
  <meta name="description" content="旅行に便利なパッキングキューブを楽天市場からピックアップ。">
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header>
    <h1>パッキングキューブ {len(items)}選</h1>
    <p>荷物をすっきり整理できる旅行の定番アイテム</p>
  </header>
  <main>
    <ul class="grid">
{chr(10).join(cards)}
    </ul>
  </main>
  <footer>
    <p>価格・在庫は{date.today():%Y年%m月%d日}時点の楽天市場の情報です。最新情報はリンク先でご確認ください。</p>
  </footer>
</body>
</html>
"""


def main() -> None:
    load_dotenv(ROOT / ".env")
    app_id = os.environ.get("RAKUTEN_APP_ID")
    access_key = os.environ.get("RAKUTEN_ACCESS_KEY")
    if not app_id or not access_key:
        sys.exit("環境変数 RAKUTEN_APP_ID / RAKUTEN_ACCESS_KEY が未設定です（.env.example を参照）")
    items = [normalize(i) for i in fetch_items(app_id, access_key)]
    if not items:
        sys.exit("商品が取得できませんでした")
    out = ROOT / "site" / "index.html"
    out.write_text(render(items), encoding="utf-8")
    print(f"{len(items)}件を書き出しました: {out}")


if __name__ == "__main__":
    main()
