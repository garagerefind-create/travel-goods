#!/usr/bin/env python3
"""運営者情報・プライバシーポリシー・アフィリエイトについて等、固定の案内ページを生成する。

内容はこのファイル内に直接書く（更新頻度が低いページのため）。
research/site_pages.json にページ一覧（sitemap用のメタ情報）を持つ。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sitemap  # noqa: E402
from generate import SITE_NAME, page_shell  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

OPERATOR_NAME = "たびのおとも運営"
SITE_STARTED = "2026年9月"


def build_about() -> str:
    title = "運営者情報"
    desc = f"{SITE_NAME}の運営者情報です。サイトの目的や運営方針、収益についてご案内しています。"
    body = f"""    <article class="article">
      <h1>{title}</h1>

      <h2>サイト名・運営者</h2>
      <ul class="checklist">
        <li>サイト名：{SITE_NAME}</li>
        <li>運営者：{OPERATOR_NAME}</li>
        <li>運営開始：{SITE_STARTED}</li>
      </ul>

      <h2>サイトの目的</h2>
      <p>{SITE_NAME}は、旅行の持ち物や準備で「何を選べばいいか分からない」と迷う時間を減らすことを目的にした、旅行メディアです。持ち物リストや準備のコツといった記事と、実際に役立つ旅行グッズの紹介をあわせて掲載しています。</p>

      <h2>商品の選び方</h2>
      <p>掲載している商品は、楽天市場のレビュー評価やレビュー件数などをもとに、独自の基準で選んでいます。基本的には商品ページの情報をもとに紹介しており、実際に使用した商品には、商品カードに「実際に使っています」のバッジを表示しています。バッジのない商品は、私たちが実際に使用したものではありません。</p>

      <h2>収益について</h2>
      <p>{SITE_NAME}は、楽天アフィリエイトをはじめとするアフィリエイトプログラムを利用しており、紹介した商品が購入された場合に、紹介料を受け取ることがあります。詳しくは、<a href="affiliate.html">アフィリエイトについて</a>のページをご覧ください。</p>

      <h2>お問い合わせ</h2>
      <p>お問い合わせの受付方法は、現在準備中です。ご案内できるようになり次第、このページに掲載します。</p>

      <p><a href="index.html">← {SITE_NAME} トップへ戻る</a></p>
    </article>"""
    return page_shell(title=title, desc=desc, body=body, path="about.html", og_type="website")


def build_privacy() -> str:
    title = "プライバシーポリシー"
    desc = f"{SITE_NAME}のプライバシーポリシーです。アクセス解析、広告配信、個人情報の取り扱いについてご案内しています。"
    body = f"""    <article class="article">
      <h1>{title}</h1>
      <p class="lead">{SITE_NAME}（以下「当サイト」）における、個人情報の取り扱いについて説明します。</p>

      <h2>アクセス解析ツールについて</h2>
      <p>当サイトでは、Googleアナリティクス（Google Analytics）を利用してアクセス状況を把握しています。Googleアナリティクスは、Cookieを利用してデータを収集しますが、個人を特定する情報は含まれません。この機能は、Cookieを無効にすることで収集を拒否することが可能ですので、お使いのブラウザの設定をご確認ください。詳しくは、<a href="https://marketingplatform.google.com/about/analytics/terms/jp/" target="_blank" rel="noopener">Googleアナリティクス利用規約</a>や、<a href="https://policies.google.com/technologies/partner-sites?hl=ja" target="_blank" rel="noopener">Googleのポリシーと規約</a>をご覧ください。</p>

      <h2>広告（アフィリエイトプログラム）について</h2>
      <p>当サイトは、楽天アフィリエイトをはじめとするアフィリエイトプログラムに参加しています。商品リンクには、購入履歴を計測するためのCookie等が利用される場合があります。詳しくは、<a href="affiliate.html">アフィリエイトについて</a>のページをご覧ください。</p>

      <h2>個人情報の取り扱い</h2>
      <p>当サイトは、現時点でお問い合わせフォームや会員登録機能を設けておらず、利用者から直接、個人情報をお預かりすることはありません。今後、お問い合わせフォーム等を設ける場合は、このページで取り扱い方法をご案内します。</p>

      <h2>免責事項</h2>
      <p>当サイトに掲載している情報（価格、在庫、商品の仕様、記事の内容など）については、可能な限り正確な情報を掲載するよう努めていますが、その正確性・安全性を保証するものではありません。情報が古くなっている場合がありますので、購入や利用の際は、必ずリンク先の公式情報をご確認ください。当サイトの情報を利用したことによって生じたいかなる損害についても、責任を負いかねます。</p>

      <h2>著作権について</h2>
      <p>当サイトに掲載している文章・画像等の著作権は、{OPERATOR_NAME}または各権利者に帰属します。商品画像は、楽天市場の商品ページから引用しています。</p>

      <h2>プライバシーポリシーの変更について</h2>
      <p>当サイトは、法令の変更や運営方針の変更に応じて、本ポリシーの内容を予告なく変更することがあります。変更後のプライバシーポリシーは、当ページに掲載した時点から効力を持つものとします。</p>

      <p class="note">※ このページは、個人が運営する情報サイト向けの一般的な内容をもとに作成した、簡易的なプライバシーポリシーです。法的な助言ではないため、内容について不安な点がある場合は、専門家にご確認ください。</p>

      <p><a href="index.html">← {SITE_NAME} トップへ戻る</a></p>
    </article>"""
    return page_shell(title=title, desc=desc, body=body, path="privacy.html", og_type="website")


def build_affiliate() -> str:
    title = "アフィリエイトについて"
    desc = f"{SITE_NAME}が参加しているアフィリエイトプログラムと、商品の選び方についてご案内しています。"
    body = f"""    <article class="article">
      <h1>{title}</h1>
      <p class="lead">{SITE_NAME}で紹介している商品のリンクについて、ご案内します。</p>

      <h2>アフィリエイトプログラムについて</h2>
      <p>当サイトは、楽天アフィリエイトをはじめとするアフィリエイトプログラムに参加しています。当サイトに掲載している商品リンクを経由して商品が購入された場合、当サイトに紹介料（成果報酬）が支払われることがあります。この報酬は、商品の購入者様に追加の費用が発生する仕組みではありません。</p>

      <h2>商品の選び方</h2>
      <p>掲載している商品は、次の基準を目安に選んでいます。</p>
      <ul class="checklist">
        <li>楽天市場で在庫があること</li>
        <li>レビュー評価が4.0以上であること</li>
        <li>レビュー件数が30件以上であること</li>
      </ul>
      <p>そのうえで、価格帯やタイプが偏らないよう、カテゴリごとに複数の商品を選んでいます。紹介料の有無によって、掲載する商品や評価を変えることはありません。</p>

      <h2>「実際に使っています」の表示について</h2>
      <p>掲載商品の多くは、商品ページの情報とレビューをもとに紹介しており、私たちが実際に使用したものではありません。実際に旅行で使用した商品には、商品カードに「実際に使っています」のバッジを表示し、使用した旅行の内容や、良かった点・気になった点などを、事実に基づいて追記します。バッジのない商品について、使用した体験があるかのような表現はいたしません。</p>

      <h2>価格・在庫について</h2>
      <p>掲載している価格やレビュー件数は、取得した時点の情報です。楽天市場の価格や在庫は変動するため、実際の価格・在庫は、必ずリンク先の商品ページでご確認ください。</p>

      <p><a href="index.html">← {SITE_NAME} トップへ戻る</a></p>
    </article>"""
    return page_shell(title=title, desc=desc, body=body, path="affiliate.html", og_type="website")


PAGES = {
    "about.html": build_about,
    "privacy.html": build_privacy,
    "affiliate.html": build_affiliate,
}


def main() -> None:
    for path, builder in PAGES.items():
        (ROOT / "docs" / path).write_text(builder(), encoding="utf-8")
    sitemap.build()
    print("生成しました:", ", ".join(f"docs/{p}" for p in PAGES))


if __name__ == "__main__":
    main()
