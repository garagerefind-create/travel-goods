#!/usr/bin/env python3
"""research/articles.json の記事を、docs/*.html として書き出す（API呼び出しなし）。

コンテンツはこのファイル内の ARTICLES に直接書く。商品の個別紹介はせず、
docs/index.html の該当カテゴリへ内部リンクする（商品情報の二重管理を避けるため）。
"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sitemap  # noqa: E402
from generate import SITE_NAME, SITE_URL  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def checklist(items: list[str]) -> str:
    lis = "\n".join(f'        <li><label><input type="checkbox"> {i}</label></li>' for i in items)
    return f'      <ul class="checklist">\n{lis}\n      </ul>'


def cta(lead: str, links: list[tuple[str, str]]) -> str:
    buttons = "\n".join(f'        <a href="{href}">{label} を見る →</a>' for label, href in links)
    lead_html = f'      <p class="lead">{lead}</p>\n' if lead else ""
    return f"""{lead_html}      <p class="cta">
{buttons}
      </p>"""


def build_packing_checklist() -> str:
    title = "初めての海外旅行 持ち物リスト｜チェックリストと選び方"
    desc = "初めての海外旅行で困らない持ち物チェックリスト。パスポートなどの必須書類から、スーツケースや圧縮袋、モバイルバッテリーなど旅行グッズの選び方まで、カテゴリ別にまとめました。"

    body = f"""    <article class="article">
      <h1>{title}</h1>
      <p class="lead">初めての海外旅行だと、何を持って行けばいいか迷うものです。ここでは、忘れると困る必須の持ち物から、荷造りをラクにするグッズまで、順番にまとめました。最後に、出発前に確認できるチェックリストも用意しています。</p>

      <h2>まず確認したい、必須の持ち物</h2>
      <p>グッズを揃える前に、この6つがあるかを確認しましょう。忘れると、出発できない・現地で困る、といったことにつながります。</p>
      {checklist([
          "パスポート（残存有効期間を確認。多くの国で「帰国予定日から3〜6か月以上」が必要とされますが、国によって基準が違うため、渡航先の大使館・外務省の案内で確認してください）",
          "ビザ（必要かどうかは渡航先によります。ビザなしで行ける国でも、電子渡航認証（ESTAなど）が必要な場合があります）",
          "航空券（eチケットの控え、印刷またはスマホに保存）",
          "海外旅行保険の証書（現地の病院・警察の連絡先とあわせて控えておくと安心です）",
          "クレジットカードと現金（現地通貨を少額、カードは2枚以上あると安心）",
          "常備薬・お薬手帳（処方薬がある場合、機内持ち込みのルールも事前に確認を）",
      ])}
      <p class="note">※ 出入国のルールは、国や時期によって変わります。出発前に、外務省の海外安全ホームページや、渡航先の大使館の情報で、最新の内容を確認してください。</p>

      <h2>荷物を入れるバッグを選ぶ</h2>
      <p>まず、荷物をまとめるバッグを決めます。旅行日数や、機内持ち込みにするかで、選び方が変わります。</p>
      {cta(
          "身軽に動きたいならバックパック、荷物が多いならスーツケース。機内持ち込みサイズや、TSAロックの有無も選ぶポイントです。",
          [("バックパック", "index.html#backpack"), ("スーツケース", "index.html#suitcase")],
      )}

      <h2>荷造りをラクにする</h2>
      <p>衣類は、圧縮袋やトラベルポーチでまとめると、スーツケースの中が整理しやすくなります。液体物は、多くの国・航空会社で「1容器100ml以下、透明の袋にまとめて総量1L程度まで」という制限があります（詳しい基準は、利用する航空会社で確認してください）。</p>
      {cta("", [("圧縮袋・トラベルポーチ", "index.html#compression")])}

      <h2>電源まわりを忘れずに</h2>
      <p>海外では、コンセントの形が違います。行き先に合った変換プラグと、スマホの充電が心配なら、モバイルバッテリーを用意しましょう。モバイルバッテリーは、多くの航空会社で「預け荷物には入れられず、機内に持ち込む荷物に入れる」ルールになっています。容量にも上限があるため、事前に確認してください。</p>
      {cta("", [("モバイルバッテリー", "index.html#battery"), ("変換プラグ", "index.html#plug")])}

      <h2>移動中を快適に</h2>
      <p>飛行機や夜行バスでの移動が長いなら、ネックピローやアイマスクがあると、体が少し楽になります。</p>
      {cta("", [("ネックピロー", "index.html#neckpillow"), ("アイマスク", "index.html#eyemask")])}

      <h2>出発前チェックリスト</h2>
      <p>荷造りが終わったら、最後にこの項目を確認しましょう。</p>
      {checklist([
          "パスポート・航空券・保険証書は、すぐ取り出せる場所に入れた",
          "貴重品（現金・カード・パスポート）は、預け荷物ではなく手荷物に入れた",
          "モバイルバッテリーは、手荷物に入れた（預け荷物に入れていない）",
          "液体物は、規定のサイズ・容量以下で、透明の袋にまとめた",
          "変換プラグは、渡航先のプラグ形状に合っている",
          "自宅の戸締まり・電気やガスの元栓を確認した",
      ])}

      <p>このリストが、荷造りの参考になればうれしいです。カテゴリごとの商品は、<a href="index.html">トップページ</a>からご覧いただけます。</p>
    </article>"""
    return render_page(title, desc, body)


def render_page(title: str, desc: str, body: str) -> str:
    full_title = f"{title} | {SITE_NAME}"
    page_url = f"{SITE_URL}packing-checklist.html"
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

  <meta property="og:type" content="article">
  <meta property="og:site_name" content="{SITE_NAME}">
  <meta property="og:locale" content="ja_JP">
  <meta property="og:title" content="{full_title}">
  <meta property="og:description" content="{desc}">
  <meta property="og:url" content="{page_url}">
  <meta property="og:image" content="{SITE_URL}og-image.png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{full_title}">
  <meta name="twitter:description" content="{desc}">
  <meta name="twitter:image" content="{SITE_URL}og-image.png">
</head>
<body>
  <header>
    <p class="site-name"><a href="index.html">{SITE_NAME}</a></p>
    <p class="ad">※ 当サイトは楽天アフィリエイトを利用した広告（PR）を含みます。</p>
    <nav><a href="index.html#backpack">バックパック</a><a href="index.html#suitcase">スーツケース</a><a href="index.html#compression">圧縮袋・トラベルポーチ</a><a href="index.html#battery">モバイルバッテリー</a><a href="index.html#plug">変換プラグ</a><a href="index.html#neckpillow">ネックピロー</a><a href="index.html#eyemask">アイマスク</a></nav>
  </header>
  <main>
{body}
  </main>
  <footer>
    <p>記事の内容は{date.today():%Y年%m月%d日}時点の一般的な情報です。出入国のルールや航空会社の規定は変わることがあるため、必ず公式情報でご確認ください。</p>
    <p><a href="index.html">← {SITE_NAME} トップへ戻る</a></p>
  </footer>
</body>
</html>
"""


def main() -> None:
    (ROOT / "docs" / "packing-checklist.html").write_text(build_packing_checklist(), encoding="utf-8")
    sitemap.build()
    print("生成しました: docs/packing-checklist.html")


if __name__ == "__main__":
    main()
