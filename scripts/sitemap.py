#!/usr/bin/env python3
"""docs/sitemap.xml と docs/robots.txt を、サイト内の全ページぶんまとめて書き出す。

- トップページの更新日は research/meta.json から取る
- 記事ページの一覧は research/articles.json（generate_article.py が書き込む）から取る
- 旅行記の一覧は research/blog_posts.json / blog_meta.json（generate_blog.py が書き込む）から取る
- 運営者情報等の固定ページは research/site_pages.json から取る
generate.py / generate_article.py / generate_blog.py / generate_pages.py のいずれからも、生成の最後に呼ばれる。
"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from safety import atomic_write_text, blog_meta_path, docs_dir, is_publishable  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SITE_URL = "https://garagerefind-create.github.io/travel-goods/"


def build() -> None:
    meta = json.loads((ROOT / "research" / "meta.json").read_text(encoding="utf-8"))
    pages = [{"path": "", "lastmod": meta["updated"], "changefreq": "weekly"},
             {"path": "goods.html", "lastmod": meta["updated"], "changefreq": "weekly"}]
    articles_path = ROOT / "research" / "articles.json"
    if articles_path.exists():
        for a in json.loads(articles_path.read_text(encoding="utf-8")):
            if not is_publishable(a, a["path"]):
                continue  # 下書き・未来日の記事はサイトマップに載せない
            pages.append({"path": a["path"], "lastmod": a.get("updated", a["published"]), "changefreq": "monthly"})

    meta_path = blog_meta_path(ROOT)
    if not meta_path.exists():
        meta_path = ROOT / "research" / "blog_meta.json"
    blog_posts_path = ROOT / "research" / "blog_posts.json"
    if meta_path.exists():
        blog_meta = json.loads(meta_path.read_text(encoding="utf-8"))
        pages.append({"path": "blog.html", "lastmod": blog_meta["updated"], "changefreq": "weekly"})
    if blog_posts_path.exists():
        for p in json.loads(blog_posts_path.read_text(encoding="utf-8")):
            if not is_publishable(p, p.get("slug", "")):
                continue  # 下書き・未来日の記事はサイトマップに載せない
            pages.append({"path": f"blog-{p['slug']}.html", "lastmod": p.get("updated", p["published"]),
                          "changefreq": "monthly"})

    site_pages_path = ROOT / "research" / "site_pages.json"
    if site_pages_path.exists():
        for p in json.loads(site_pages_path.read_text(encoding="utf-8")):
            pages.append({"path": p["path"], "lastmod": p["updated"], "changefreq": "yearly"})

    urls = "\n".join(
        f'  <url><loc>{SITE_URL}{p["path"]}</loc><lastmod>{p["lastmod"]}</lastmod>'
        f'<changefreq>{p["changefreq"]}</changefreq></url>'
        for p in pages
    )
    atomic_write_text(
        docs_dir(ROOT) / "sitemap.xml",
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n',
    )
    atomic_write_text(docs_dir(ROOT) / "robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}sitemap.xml\n")
    print(f"sitemap.xml を書き出しました（{len(pages)}ページ）")


if __name__ == "__main__":
    build()
