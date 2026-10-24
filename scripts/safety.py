#!/usr/bin/env python3
"""公開事故・収益リンク消失・データ破損を防ぐための共通ルール（2026-10 追加）。

- 公開判定（下書き・未来日）
- アフィリエイトの必須チェック
- HTML / JSON-LD / URL の安全な埋め込み
- ファイルの安全な書き込み（一時ファイル → 置き換え）
- 残存ページ（一覧から外れたのに docs/ に残っているページ）の検出
"""
from __future__ import annotations

import errno
import fcntl
import html
import json
import os
import re
import sys
import tempfile
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path

JST = timezone(timedelta(hours=9))
VALID_STATUS = {None, "published", "draft"}
# 楽天アフィリエイトのリンク先として認めるホストとパス（すべて https、ポート・ユーザー情報なし）
AFFILIATE_HOSTS = {"hb.afl.rakuten.co.jp"}
AFFILIATE_PATH_PREFIXES = ("/hgc/",)
# generate_article.py が作るガイド記事（generate_article.ARTICLES と一致させる。テストで確認）
GUIDE_PAGES = ("packing-checklist.html", "domestic-packing-list.html")


def docs_dir(root: Path) -> Path:
    """生成先フォルダ。build_site.py が一時フォルダへ生成させるときは TG_DOCS_DIR で切り替える。"""
    return Path(os.environ.get("TG_DOCS_DIR") or Path(root) / "docs")


LOCK_NAME = ".build_site.lock"
LOCK_HELD_ENV = "TG_SITE_LOCK_HELD"


def hold_site_lock(root: Path):
    """サイトのデータ・生成物を書き換える処理どうしの排他ロック（build_site / refresh / generate*.py 共通）。

    すでに別の処理が持っていれば、何もせずに終了する。build_site.py が子プロセスを動かすときは、
    親がロックを持っていることを環境変数 TG_SITE_LOCK_HELD=1 で伝え、子は取り直さない。
    戻り値のファイルはプロセス終了まで保持する（閉じるとロックが外れる）。
    """
    if os.environ.get(LOCK_HELD_ENV) == "1":
        return None
    f = open(Path(root) / LOCK_NAME, "w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as e:
        f.close()
        if e.errno in (errno.EAGAIN, errno.EACCES):
            sys.exit("別の処理（build_site / refresh / 生成スクリプト）が実行中のため、何もせずに終了しました。")
        raise
    return f


def blog_meta_path(root: Path) -> Path:
    """旅行記一覧の更新日（blog_meta.json）の書き込み・読み込み先。
    build_site.py の実行中は作業フォルダ側（TG_BLOG_META_OUT）を使い、research/ を書き換えない。"""
    return Path(os.environ.get("TG_BLOG_META_OUT") or Path(root) / "research" / "blog_meta.json")


# ---------- 公開判定 ----------

def today() -> date:
    """公開判定に使う「今日」（日本時間）。テスト用に TG_TODAY=YYYY-MM-DD で上書きできる。"""
    forced = os.environ.get("TG_TODAY")
    if forced:
        return date.fromisoformat(forced)
    return datetime.now(JST).date()


def is_publishable(entry: dict, label: str = "") -> bool:
    """status が draft でなく、published（公開日）が今日以前なら公開対象。

    status を省略した既存データは従来どおり公開扱い（後方互換）。
    """
    status = entry.get("status")
    if status not in VALID_STATUS:
        sys.exit(f"不正な status です: {status!r}（published / draft のどちらか）{label}")
    if status == "draft":
        return False
    published = entry.get("published")
    if not published:
        sys.exit(f"published（公開日）がありません: {label}")
    return date.fromisoformat(published) <= today()


def publishable_posts(posts: list[dict]) -> list[dict]:
    return [p for p in posts if is_publishable(p, p.get("slug", ""))]


# ---------- アフィリエイト ----------

def require_affiliate_id(purpose: str) -> str:
    """アフィリエイトIDが無いまま収益リンクを作る処理を止める。値は表示しない。"""
    aid = (os.environ.get("RAKUTEN_AFFILIATE_ID") or "").strip()
    if not aid:
        sys.exit(f"RAKUTEN_AFFILIATE_ID が未設定のため中止しました（{purpose}）。"
                 "収益リンクが通常リンクに置き換わるのを防ぐためです。.env を確認してください。")
    return aid


def is_affiliate_url(url) -> bool:
    """https://hb.afl.rakuten.co.jp/hgc/… の形（ポート・ユーザー情報なし）だけを正しいアフィリエイトURLとみなす。"""
    if not isinstance(url, str) or any(ch in url for ch in ' \t\r\n"\'<>\\'):
        return False
    u = urllib.parse.urlparse(url)
    try:
        port = u.port
    except ValueError:
        return False
    return (u.scheme == "https" and u.hostname in AFFILIATE_HOSTS and port is None and "@" not in u.netloc
            and u.path.startswith(AFFILIATE_PATH_PREFIXES))


def is_rakuten_host(host: str) -> bool:
    host = (host or "").lower().rstrip(".")
    return host == "rakuten.co.jp" or host.endswith(".rakuten.co.jp")


def check_items_have_affiliate(items: dict, codes: list[str], purpose: str) -> None:
    """掲載する商品の affiliateUrl が無い・形が正しくない場合は、通常リンクへ黙って切り替えずに止める。"""
    bad = [c for c in codes if not is_affiliate_url((items.get(c) or {}).get("affiliateUrl"))]
    if bad:
        sys.exit(f"affiliateUrl が無いか、楽天アフィリエイトの正しい形式（https://hb.afl.rakuten.co.jp/…）でない商品が"
                 f"あるため中止しました（{purpose}）: {', '.join(bad)}")


# ---------- 安全な埋め込み ----------

def esc(value) -> str:
    """HTML本文・属性用のエスケープ（" と ' も含む）。"""
    return html.escape("" if value is None else str(value), quote=True)


def json_for_script(data) -> str:
    """<script type="application/ld+json"> に入れるJSON。'<' を \\u003c にして </script> での脱出を防ぐ。"""
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")


_SAFE_URL = re.compile(r"^https://[^\s\"'<>]+$")


def require_https_url(url: str, label: str) -> str:
    if not _SAFE_URL.match(url or ""):
        sys.exit(f"https:// で始まる正しいURLではありません: {label}")
    return url


# ---------- 安全な書き込み ----------

def atomic_write_text(path: Path, text: str) -> None:
    """同じフォルダに一時ファイルを書き、最後に置き換える。途中で失敗しても元のファイルは壊れない。"""
    path = Path(path)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_all(files: dict[Path, str]) -> None:
    """中身をすべて作り終えた後で、1ファイルずつアトミックに書き込む。

    防げるのは「中身を作っている途中の例外」による新旧混在まで。書き込みの途中で失敗した場合、
    先に置き換えたファイルは戻らない。サイト全体を一度に切り替えるには scripts/build_site.py を使う。
    """
    for path, text in files.items():
        atomic_write_text(path, text)


# ---------- 残存ページの検出 ----------

def orphan_blog_pages(docs: Path, published_slugs: set[str]) -> list[str]:
    """公開対象に無いのに docs/ に残っている blog-*.html。削除はしない（報告だけ）。"""
    return sorted(p.name for p in docs.glob("blog-*.html")
                  if p.name[len("blog-"):-len(".html")] not in published_slugs)


class _LinkCollector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for k, v in attrs:
                if k == "href" and v is not None:
                    self.hrefs.append(v.strip())


def link_problems(html_text: str) -> list[str]:
    """ページ内の a[href] を解析し、危険なスキームとアフィリエイトでない楽天リンクを返す。"""
    p = _LinkCollector()
    p.feed(html_text)
    out = []
    for href in p.hrefs:
        u = urllib.parse.urlparse(href)
        scheme = (u.scheme or "").lower()
        host = (u.hostname or "").lower()
        if scheme in ("javascript", "data", "vbscript"):
            out.append(f"危険なリンク: {href[:60]}")
        elif is_rakuten_host(host) and not is_affiliate_url(href):
            out.append(f"アフィリエイトでない楽天リンク: {href[:80]}")
    return out


def warn(msg: str) -> None:
    print(f"⚠ {msg}", file=sys.stderr)
