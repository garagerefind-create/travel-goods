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
DATA_DATE = date(2026, 9, 21)  # candidates.json を取得した日

# カテゴリ: (id, 見出し, ひとこと, 載せる商品の番号[candidates.json 内の1始まり])
SECTIONS = [
    ("backpack", "バックパック", "旅行向けのバックパック。容量や拡張機能をチェックして選びましょう。", [5, 3, 2, 8]),
    ("suitcase", "スーツケース", "機内持ち込みサイズを中心に、価格帯の違うものを集めました。", [1, 3, 4, 8]),
    ("compression", "圧縮袋・トラベルポーチ", "衣類をコンパクトにまとめて、荷造りをスッキリ。", [4, 2, 1, 5]),
    ("battery", "モバイルバッテリー", "旅先の充電切れ対策に。大容量から軽量タイプまで。", [1, 4, 6, 5]),
    ("plug", "変換プラグ", "海外旅行の必需品。対応する国・地域は商品ページでご確認ください。", [1, 4, 8]),
    ("neckpillow", "ネックピロー", "飛行機や新幹線での移動を快適に。タイプの違うものを選びました。", [1, 3, 6, 8]),
    ("eyemask", "アイマスク", "移動中も宿でも、しっかり眠るための遮光アイテム。", [1, 2, 3]),
]

# 表示名（元タイトルに書かれている内容のみ）。キー: (セクションid, candidates.json 内の番号)
NAMES = {
    ("backpack", 5): "tomtoc T66 トラベルバックパック",
    ("backpack", 3): "トラベルリュック 大容量・多機能",
    ("backpack", 2): "2WAY キャリーリュック 機内持ち込みサイズ",
    ("backpack", 8): "Evoon トラベルバックパック 37L 拡張機能",
    ("suitcase", 1): "機内持込 軽量スーツケース TSAロック・USBポート付き",
    ("suitcase", 3): "グリフィンランド 超軽量スーツケース Sサイズ",
    ("suitcase", 4): "B4U キャリーケース 機内持ち込み TSAロック",
    ("suitcase", 8): "LEGEND WALKER スーツケース 機内持込サイズ",
    ("compression", 4): "YKKファスナー 圧縮トラベルポーチ",
    ("compression", 2): "圧縮トラベルポーチ 内ポケット付き",
    ("compression", 1): "旅行用圧縮袋 トラベルポーチ 2点セット",
    ("compression", 5): "衣類圧縮袋 掃除機・吸引機対応",
    ("battery", 1): "モバイルバッテリー 超マット加工 PSE認証",
    ("battery", 4): "モバイルバッテリー 軽量・小型 22800mAh",
    ("battery", 6): "半固体電池 モバイルバッテリー 20800mAh",
    ("battery", 5): "オシャモバ モバイルバッテリー 5000mAh 軽量・小型",
    ("plug", 1): "マルチ変換プラグ 世界200カ国以上対応 USB2ポート",
    ("plug", 4): "変換プラグ USB-C搭載 5台同時充電",
    ("plug", 8): "カシムラ マルチプラグ サスケ 全世界対応",
    ("neckpillow", 1): "ポンプ式 エアーネックピロー コンパクト",
    ("neckpillow", 3): "曲げられる低反発ネックピロー 綿100%カバー",
    ("neckpillow", 6): "Tabine ネックピロー 150g 折りたたみ",
    ("neckpillow", 8): "マーナ ONE-BREATH ネックピロー 140g 洗える",
    ("eyemask", 1): "3D立体 アイマスク 遮光タイプ",
    ("eyemask", 2): "サエギリ アイマスク 6層 洗える",
    ("eyemask", 3): "3D立体 アイマスク 鼻クッション付き",
}

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
    data = json.loads((ROOT / "research" / "candidates.json").read_text(encoding="utf-8"))
    key = {"backpack": "バックパック", "suitcase": "スーツケース", "compression": "圧縮袋・トラベルポーチ",
           "battery": "モバイルバッテリー", "plug": "変換プラグ", "neckpillow": "ネックピロー", "eyemask": "アイマスク"}
    nav = "".join(f'<a href="#{i}">{t}</a>' for i, t, _, _ in SECTIONS)
    body = []
    for sid, title, lead, picks in SECTIONS:
        items = [(data[key[sid]][n - 1], NAMES[(sid, n)]) for n in picks]
        body.append(f"""    <section id="{sid}">
      <h2>{title}</h2>
      <p class="lead">{lead}</p>
      <ul class="grid">
{chr(10).join(card(i, n) for i, n in items)}
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
    <p>掲載の価格・評価・レビュー件数は{DATA_DATE:%Y年%m月%d日}時点の楽天市場の情報です。変動する場合があるため、購入前に必ずリンク先でご確認ください。</p>
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
