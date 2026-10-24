#!/usr/bin/env python3
"""サイト全体を一時フォルダで作り直し、点検に合格したときだけ docs/ と入れ替える（2026-10 追加、10-25 改訂）。

手順：
  0. 排他ロック（.build_site.lock）を取る。build_site / refresh / 生成スクリプトのどれかが動いていれば何もせず終了する
     前回の切り替えが途中で止まっていた場合は、まず docs/ を直前の状態に戻す（または切り替えを完了させる）
     --refresh を付けると、ロックを持ったまま価格の再取得（refresh.py）を先に行う
  1. 実行ごとの作業フォルダ（.docs-staging-XXXX/）に docs/ を複製し、生成ページ（*.html, sitemap.xml, robots.txt）を外す
     → 画像・CSS・.nojekyll など手置きのファイルはそのまま引き継ぐ
  2. 生成スクリプト4本を、作業フォルダへ出力させて実行（research/ は書き換えない）
     → 公開対象（下書きでも未来日でもない記事）のページだけが作られる
  3. 作業フォルダを check_site.py で点検
  4. すべて成功したら docs/ を切り替える（直前の docs/ は .docs-prev/ に控える）
     research/blog_meta.json（一覧の更新日）は、切り替えと同じ「確定記録」（.build_site.pending.json）で管理し、
     切り替えが完了したときだけ反映する。どこで止まっても、次回の実行で「完了させる」か「元に戻す」かを判定する
生成・点検の途中で1つでも失敗したら docs/ と research/ には一切触れずに終了する（新旧混在にしない）。
（--refresh を付けた場合の価格データの更新は、refresh.py 自身の判定で行われる）

公開をやめる記事は、一覧（blog_posts.json / articles.json）から消さずに "status": "draft" にする。
一覧に無いのに docs/ にある blog-*.html と、生成スクリプトが作らない .html は、手作りの可能性があるため
消さずに中止する（必要なら人が確認して移動・削除する）。

使い方：
  python3 scripts/build_site.py            # 作り直して入れ替える
  python3 scripts/build_site.py --dry-run  # 作って点検し、変更内容を表示するだけ（docs/ と research/ は変えない）
  python3 scripts/build_site.py --refresh  # 価格を再取得してから作り直す（weekly_update.sh が使う）
※ --dry-run でも、前回の切り替えが途中で止まっていた場合の復旧と、以前の作業フォルダの片付けだけは行う。
"""
from __future__ import annotations

import filecmp
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from safety import GUIDE_PAGES, LOCK_HELD_ENV, atomic_write_text, hold_site_lock  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
PREV = ROOT / ".docs-prev"          # 直前の docs/（控え）
OLD = ROOT / ".docs-prev-old"       # 切り替え中だけ存在する、前々回の控え
PENDING = ROOT / ".build_site.pending.json"   # 切り替えの確定記録（切り替え中だけ存在する）
STAGING_PREFIX = ".docs-staging-"
BLOG_META = ROOT / "research" / "blog_meta.json"
GENERATORS = ["generate.py", "generate_article.py", "generate_blog.py", "generate_pages.py"]
# 生成スクリプトが作る固定ページ。blog-<slug>.html は blog_posts.json に載っている slug のものだけを生成物とみなす。
GENERATED_PAGES = {"index.html", "goods.html", "blog.html", "about.html", "privacy.html", "affiliate.html",
                   *GUIDE_PAGES}
GENERATED_OTHER = {"sitemap.xml", "robots.txt"}


def known_slugs() -> set[str]:
    p = ROOT / "research" / "blog_posts.json"
    return {x.get("slug") for x in json.loads(p.read_text(encoding="utf-8"))} if p.exists() else set()


def is_generated(name: str, slugs: set[str]) -> bool:
    if name in GENERATED_PAGES or name in GENERATED_OTHER:
        return True
    return name.startswith("blog-") and name.endswith(".html") and name[len("blog-"):-len(".html")] in slugs


def generated_files(d: Path, slugs: set[str]) -> set[str]:
    return {p.name for p in d.iterdir() if p.is_file() and is_generated(p.name, slugs)}


def dir_id(p: Path) -> list[int]:
    st = os.stat(p)
    return [st.st_dev, st.st_ino]


def finish_pending(resumed: bool = True) -> None:
    """確定記録が残っていたら、切り替えが完了していたかを docs/ の実体（inode）で判定し、
    完了していれば blog_meta を反映、していなければ何も反映せずに記録を消す。"""
    if not PENDING.exists():
        return
    rec = json.loads(PENDING.read_text(encoding="utf-8"))
    if DOCS.exists() and dir_id(DOCS) == rec["new_docs_id"]:
        if rec.get("blog_meta") is not None:
            atomic_write_text(BLOG_META, rec["blog_meta"])
        if resumed:
            print("⚠ 前回の切り替えの後処理（一覧の更新日の反映）を完了しました")
    PENDING.unlink()


def recover() -> None:
    """前回の切り替えが途中で止まっていたら、docs/ を直前の状態に戻すか、切り替えを完了させる（ロック取得後に呼ぶ）。"""
    if not DOCS.exists():
        if PREV.is_dir():
            os.rename(PREV, DOCS)
            print("⚠ 前回の切り替えが途中で止まっていたため、docs/ を直前の状態に戻しました")
        else:
            sys.exit("docs/ も控え（.docs-prev/）も見つかりません。git の状態を確認してください。")
    if OLD.exists():
        if PREV.exists():
            shutil.rmtree(OLD)          # 切り替えは完了していた。前々回の控えを片付ける
        else:
            os.rename(OLD, PREV)        # 控えの入れ替え途中で止まっていた
    finish_pending()
    for p in ROOT.glob(STAGING_PREFIX + "*"):  # 以前の実行の作業フォルダ（ロック中なので他の実行のものではない）
        shutil.rmtree(p, ignore_errors=True)


def switch(new_docs: Path, blog_meta: str | None) -> None:
    """new_docs を docs/ に切り替え、blog_meta を反映する。どの段階で止まっても recover() で整合を取れる順序にしている。"""
    atomic_write_text(PENDING, json.dumps({"new_docs_id": dir_id(new_docs), "blog_meta": blog_meta}))
    try:
        if PREV.exists():
            os.rename(PREV, OLD)        # 前々回の控えは、新しい docs/ が確定するまで消さない
        os.rename(DOCS, PREV)
        try:
            os.rename(new_docs, DOCS)
        except BaseException:
            os.rename(PREV, DOCS)
            if OLD.exists():
                os.rename(OLD, PREV)
            raise
    except BaseException:
        PENDING.unlink(missing_ok=True)  # 切り替えていないので、blog_meta も反映しない
        raise
    finish_pending(resumed=False)       # ここから先で止まっても、次回の recover() が反映を完了させる
    if OLD.exists():
        try:
            shutil.rmtree(OLD)
        except OSError as e:            # 片付けの失敗は公開内容に影響しない。次回の recover() で再度片付ける
            print(f"⚠ 前々回の控え（.docs-prev-old/）を片付けられませんでした: {e}", file=sys.stderr)


def main() -> None:
    args = sys.argv[1:]
    dry, refresh = "--dry-run" in args, "--refresh" in args
    if dry and refresh:
        sys.exit("--dry-run と --refresh は同時に使えません")
    lock = hold_site_lock(ROOT)  # noqa: F841
    recover()
    child_env = dict(os.environ, **{LOCK_HELD_ENV: "1"})
    if refresh and subprocess.run([sys.executable, str(ROOT / "scripts" / "refresh.py")], cwd=ROOT,
                                  env=child_env).returncode != 0:
        sys.exit("中止しました（docs/ は変更していません）：refresh.py が失敗しました")
    if not DOCS.is_dir():
        sys.exit("docs/ がありません")
    slugs = known_slugs()
    unknown = sorted(p.name for p in DOCS.glob("*.html") if not is_generated(p.name, slugs))
    if unknown:
        sys.exit("中止しました（docs/ は変更していません）：生成スクリプトが作らないページが docs/ にあります: "
                 + ", ".join(unknown) + "\n手作りのページを消さないために止めています。"
                 "記事の公開をやめたいときは、一覧から消さずに \"status\": \"draft\" にしてください。"
                 "不要なページだと確認できた場合は、docs/ から移動または削除してから実行してください。")

    work = Path(tempfile.mkdtemp(prefix=STAGING_PREFIX, dir=ROOT))
    try:
        staging = work / "docs"
        shutil.copytree(DOCS, staging, symlinks=True)
        for name in generated_files(staging, slugs):
            (staging / name).unlink()
        meta_out = work / "blog_meta.json"
        env = dict(child_env, TG_DOCS_DIR=str(staging), TG_BLOG_META_OUT=str(meta_out))
        for g in GENERATORS:
            if subprocess.run([sys.executable, str(ROOT / "scripts" / g)], cwd=ROOT, env=env).returncode != 0:
                sys.exit(f"中止しました（docs/ と research/ は変更していません）：{g} が失敗しました")
        if subprocess.run([sys.executable, str(ROOT / "scripts" / "check_site.py")], cwd=ROOT, env=env).returncode != 0:
            sys.exit("中止しました（docs/ と research/ は変更していません）：点検（check_site.py）が不合格でした")

        before, after = generated_files(DOCS, slugs), generated_files(staging, slugs)
        removed, added = sorted(before - after), sorted(after - before)
        changed = sorted(n for n in before & after if not filecmp.cmp(DOCS / n, staging / n, shallow=False))
        print(f"変更：更新 {len(changed)} / 追加 {len(added)} / 公開フォルダから外す {len(removed)}")
        for n in added:
            print("  ＋", n)
        for n in removed:
            print("  －（公開対象外のため外す。本文は content/ に残ります）", n)
        if dry:
            print("--dry-run のため docs/ と research/ は変更していません")
            return
        switch(staging, meta_out.read_text(encoding="utf-8") if meta_out.exists() else None)
        print("docs/ を新しい内容に切り替えました（直前の状態は .docs-prev/ に控えてあります）")
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
