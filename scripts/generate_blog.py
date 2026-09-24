#!/usr/bin/env python3
"""research/blog_posts.json をもとに、旅行記（ブログ）のページを生成する。

- 各記事の本文は content/blog/<slug>.html に書く（<article> の中身のみ）
- 記事が1件もなくても、一覧ページ(docs/blog.html)は生成する（近日公開のプレースホルダー）
- 書き方の詳しいルールは content/blog/README.md を参照
"""
import html
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sitemap  # noqa: E402
from generate import SITE_NAME, image_of, page_shell  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
POSTS_PATH = ROOT / "research" / "blog_posts.json"
META_PATH = ROOT / "research" / "blog_meta.json"
CONTENT_DIR = ROOT / "content" / "blog"

TYPE_LABEL = {"diary": "体験記", "guide": "ガイド"}

# slug -> { マーカー名: リンク文言 } / { マーカー名: 差し込む見出し文 }
# マーカー名は記事ごとに独立（別記事で同じマーカー名を使っても文言は混ざらない）。
# リンク文言は「実際に使っています」「愛用品」等、確認できていない実体験を
# 示す表現を使わない。製品そのものの使用が確認できている場合のみ、
# 「記事で使用している◯◯を楽天で見る」のように、製品名を主語にした
# 中立的な言い方にする（特定の販売ページ・ショップでの購入は明言しない）。
PRODUCT_BLOCK_LINK_TEXT: dict[str, dict[str, str]] = {
    "dog-travel-1night2days": {
        "cart": "同じように、キャリーとしても使える3wayタイプを楽天で探す",
    },
    "iphone-travel-video": {
        "osmo": "記事で使用しているOsmo Pocket 4を楽天で見る",
    },
}
PRODUCT_BLOCK_HEADING: dict[str, dict[str, str]] = {
    "dog-travel-1night2days": {
        "hotel": "旅行用として選ぶなら",
    },
    "reduce-luggage-1night2days": {
        "pouch": "冬場など衣類がかさばるときは、こうした圧縮ポーチも選択肢",
    },
}


def _load_product_names() -> dict[str, str]:
    picks = json.loads((ROOT / "research" / "picks.json").read_text(encoding="utf-8"))
    return {i["itemCode"]: i["name"] for sec in picks for i in sec["items"]}


def product_mention_html(item_code: str, items: dict, names: dict, link_text: str) -> str:
    it = items[item_code]
    name = names.get(item_code, it["itemName"])
    url = html.escape(it.get("affiliateUrl") or it["itemUrl"])
    return f"""        <li class="product-mention">
          <a href="{url}" target="_blank" rel="noopener sponsored nofollow">
            <img src="{html.escape(image_of(it))}" alt="{html.escape(name)}" loading="lazy">
            <span class="pm-body">
              <span class="pm-name">{html.escape(name)}</span>
              <span class="pm-price">¥{int(it['itemPrice']):,}</span>
              <span class="pm-link">{html.escape(link_text)} →</span>
            </span>
          </a>
        </li>"""


def render_product_block(slug: str, marker: str, codes: list[str], items: dict, names: dict) -> str:
    default_link = "楽天市場で見る"
    link_text = PRODUCT_BLOCK_LINK_TEXT.get(slug, {}).get(marker, default_link)
    mentions = "\n".join(product_mention_html(c, items, names, link_text) for c in codes)
    heading = PRODUCT_BLOCK_HEADING.get(slug, {}).get(marker)
    heading_html = f'\n        <p class="pm-heading">{html.escape(heading)}</p>' if heading else ""
    return f"""      <div class="product-mentions">{heading_html}
        <ul class="pm-list">
{mentions}
        </ul>
      </div>"""


def fill_product_markers(slug: str, frag: str, product_refs: dict) -> str:
    if not product_refs:
        return frag
    items = json.loads((ROOT / "research" / "items.json").read_text(encoding="utf-8"))
    names = _load_product_names()

    def repl(m: re.Match) -> str:
        marker = m.group(1)
        codes = product_refs.get(marker)
        if not codes:
            return ""
        return render_product_block(slug, marker, codes, items, names)

    return re.sub(r"<!--\s*product:(\w[\w-]*)\s*-->", repl, frag)


def load_posts() -> list[dict]:
    posts = json.loads(POSTS_PATH.read_text(encoding="utf-8")) if POSTS_PATH.exists() else []
    for p in posts:
        if not (p.get("slug") or "").replace("-", "").isalnum():
            sys.exit(f"不正な slug です: {p.get('slug')!r}（半角英数とハイフンのみ）")
        frag = CONTENT_DIR / f"{p['slug']}.html"
        if not frag.exists():
            sys.exit(f"本文ファイルが見つかりません: {frag}")
    return sorted(posts, key=lambda p: p["published"], reverse=True)


def build_post(post: dict) -> str:
    frag = (CONTENT_DIR / f"{post['slug']}.html").read_text(encoding="utf-8")
    frag = fill_product_markers(post["slug"], frag, post.get("product_refs", {}))
    label = TYPE_LABEL.get(post.get("type"), "")
    pub = date.fromisoformat(post["published"])
    body = f"""    <article class="article">
      <p class="post-meta"><span class="tag">{html.escape(label)}</span> {pub:%Y年%m月%d日}</p>
      <h1>{html.escape(post['title'])}</h1>
{frag}
      <p><a href="blog.html">← 旅行記の一覧へ戻る</a></p>
    </article>"""
    return page_shell(title=post["title"], desc=post.get("excerpt", ""), body=body,
                       path=f"blog-{post['slug']}.html", og_type="article",
                       published=post.get("published"), updated=post.get("updated"))


def build_index(posts: list[dict]) -> str:
    if posts:
        cards = "\n".join(f"""        <li class="post-card">
          <a href="blog-{p['slug']}.html">
            <p class="post-meta"><span class="tag">{html.escape(TYPE_LABEL.get(p.get('type'), ''))}</span> {date.fromisoformat(p['published']):%Y年%m月%d日}</p>
            <h2>{html.escape(p['title'])}</h2>
            <p class="desc">{html.escape(p.get('excerpt', ''))}</p>
          </a>
        </li>""" for p in posts)
        list_html = f'      <ul class="post-list">\n{cards}\n      </ul>'
    else:
        list_html = '      <p class="lead">まだ記事がありません。近日公開予定です。お楽しみに。</p>'
    body = f"""    <section class="article">
      <h1>旅行記</h1>
      <p class="lead">実際に旅行に行ったときの記録や、荷物・グッズにまつわる話をまとめています。</p>
{list_html}
    </section>"""
    return page_shell(title="旅行記", desc=f"{SITE_NAME}の旅行記・体験談をまとめたページです。",
                       body=body, path="blog.html", og_type="website")


def main() -> None:
    posts = load_posts()
    for p in posts:
        (ROOT / "docs" / f"blog-{p['slug']}.html").write_text(build_post(p), encoding="utf-8")
    (ROOT / "docs" / "blog.html").write_text(build_index(posts), encoding="utf-8")
    if posts:
        META_PATH.write_text(json.dumps({"updated": posts[0]["published"]}), encoding="utf-8")
    sitemap.build()
    print(f"生成しました: docs/blog.html ＋ 記事{len(posts)}件")


if __name__ == "__main__":
    main()
