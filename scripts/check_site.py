#!/usr/bin/env python3
"""公開前の点検（読み取りのみ。ファイルの変更・削除はしない）。問題があれば終了コード1。

- 公開対象に無いのに docs/ に残っている旅行記・ガイド記事
- 掲載商品・記事内商品の affiliateUrl の欠落・形式不正（https://hb.afl.rakuten.co.jp/hgc/… 以外）
- ページ内リンク（HTMLを解析）：アフィリエイトでない楽天リンク、javascript: 等の危険なリンク
点検対象フォルダは既定で docs/。build_site.py からは TG_DOCS_DIR で一時フォルダを点検する。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from safety import GUIDE_PAGES, docs_dir, is_affiliate_url, is_publishable, link_problems, orphan_blog_pages  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DOCS = docs_dir(ROOT)


def load(name):
    p = ROOT / "research" / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def main() -> int:
    problems = []
    posts = [p for p in load("blog_posts.json") if is_publishable(p, p.get("slug", ""))]
    for name in orphan_blog_pages(DOCS, {p["slug"] for p in posts}):
        problems.append(f"公開対象外の旅行記ページが残っています: docs/{name}")
    articles = {a["path"] for a in load("articles.json") if is_publishable(a, a["path"])}
    for path in GUIDE_PAGES:
        if path not in articles and (DOCS / path).exists():
            problems.append(f"公開対象外のガイド記事ページが残っています: docs/{path}")

    items = load("items.json") or {}
    codes = [i["itemCode"] for s in load("picks.json") if not s.get("hidden_from_index") for i in s["items"]]
    codes += [c for p in posts for cs in (p.get("product_refs") or {}).values() for c in cs]
    for c in sorted(set(codes)):
        if c not in items:
            problems.append(f"items.json に無い商品コード: {c}")
        elif not is_affiliate_url(items[c].get("affiliateUrl")):
            problems.append(f"affiliateUrl が無いか形式が正しくない商品: {c}")

    for page in sorted(DOCS.glob("*.html")):
        for m in link_problems(page.read_text(encoding="utf-8")):
            problems.append(f"{m}（docs/{page.name}）")

    if problems:
        print("点検NG（公開前に確認してください）:")
        for m in problems:
            print("  -", m)
        return 1
    print(f"点検OK：旅行記{len(posts)}件 / ガイド{len(articles)}件 / 商品{len(set(codes))}件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
