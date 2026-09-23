#!/usr/bin/env python3
"""docs/sitemap.xml と docs/robots.txt を、サイト内の全ページぶんまとめて書き出す。

- トップページの更新日は research/meta.json から取る
- 記事ページの一覧は research/articles.json（generate_article.py が書き込む）から取る
generate.py / generate_article.py の両方から、生成の最後に呼ばれる。
"""
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE_URL = "https://garagerefind-create.github.io/travel-goods/"


def build() -> None:
    meta = json.loads((ROOT / "research" / "meta.json").read_text(encoding="utf-8"))
    pages = [{"path": "", "lastmod": meta["updated"], "changefreq": "weekly"}]
    articles_path = ROOT / "research" / "articles.json"
    if articles_path.exists():
        for a in json.loads(articles_path.read_text(encoding="utf-8")):
            pages.append({"path": a["path"], "lastmod": a.get("updated", a["published"]), "changefreq": "monthly"})

    urls = "\n".join(
        f'  <url><loc>{SITE_URL}{p["path"]}</loc><lastmod>{p["lastmod"]}</lastmod>'
        f'<changefreq>{p["changefreq"]}</changefreq></url>'
        for p in pages
    )
    (ROOT / "docs" / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n',
        encoding="utf-8",
    )
    (ROOT / "docs" / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}sitemap.xml\n", encoding="utf-8"
    )
    print(f"sitemap.xml を書き出しました（{len(pages)}ページ）")


if __name__ == "__main__":
    build()
