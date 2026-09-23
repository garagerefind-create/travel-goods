#!/usr/bin/env python3
"""research/blog_posts.json をもとに、旅行記（ブログ）のページを生成する。

- 各記事の本文は content/blog/<slug>.html に書く（<article> の中身のみ）
- 記事が1件もなくても、一覧ページ(docs/blog.html)は生成する（近日公開のプレースホルダー）
- 書き方の詳しいルールは content/blog/README.md を参照
"""
import html
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sitemap  # noqa: E402
from generate import SITE_NAME, page_shell  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
POSTS_PATH = ROOT / "research" / "blog_posts.json"
META_PATH = ROOT / "research" / "blog_meta.json"
CONTENT_DIR = ROOT / "content" / "blog"

TYPE_LABEL = {"diary": "体験記", "guide": "ガイド"}


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
