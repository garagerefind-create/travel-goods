"""安全性改善（2026-10）の再発防止テスト。

外部API・GitHub・本番フォルダには一切触れない。リポジトリを一時フォルダへコピーし、
ダミーのアフィリエイトID（DUMMYAFF）と偽のAPI応答だけで検証する。
実行: python3 -m unittest discover -s tests -v
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PY = sys.executable
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}

# ---------- テストで使う日付 ----------
# 日付を決め打ちにすると、新しい記事を足すたびに「その記事はまだ公開日前」と扱われてテストが落ちる。
# そこで、実データ（research/）の公開済み記事のいちばん新しい公開日から、テスト用の日付を毎回求める。
#   TODAY  … 公開判定に使う「今日」。本当の今日（日本時間）か「最新の公開日の翌日」の遅い方
#   NEWER  … テストで足す「いちばん新しい記事」の公開日（= TODAY。既存のどの記事よりも新しい）
#   FUTURE … まだ公開してはいけない未来日（TODAY の7日後）
def _test_dates():
    from datetime import date, datetime, timedelta, timezone
    real_today = datetime.now(timezone(timedelta(hours=9))).date()
    entries = (json.loads((REPO / "research/blog_posts.json").read_text(encoding="utf-8"))
               + json.loads((REPO / "research/articles.json").read_text(encoding="utf-8")))
    dates = [date.fromisoformat(e["published"]) for e in entries
             if e.get("status") != "draft" and e.get("published")]
    published = [d for d in dates if d <= real_today]
    scheduled = [d for d in dates if d > real_today]  # 予約投稿（公開日がまだ先の記事）
    today = max([real_today] + [d + timedelta(days=1) for d in published])
    if scheduled and today >= min(scheduled):
        today = real_today  # 予約投稿をテストの中で先に公開してしまわないようにする
    return today.isoformat(), today.isoformat(), (today + timedelta(days=7)).isoformat()


TODAY, NEWER, FUTURE = _test_dates()
INITIAL_BLOG_META = json.loads((REPO / "research/blog_meta.json").read_text(encoding="utf-8"))["updated"]

FAKE_REFRESH = r'''
import sys
sys.path.insert(0, sys.argv[1] + "/scripts")
import refresh
mode = sys.argv[2]
def fake_fetch(app_id, key, aff, code):
    it = {"itemCode": code, "itemName": "X", "itemUrl": "https://item.rakuten.co.jp/x/", "itemPrice": 1234,
          "reviewAverage": 4.5, "reviewCount": 100, "shopName": "s", "mediumImageUrls": [], "availability": 1}
    if mode == "with_aff_url":
        it["affiliateUrl"] = "https://hb.afl.rakuten.co.jp/hgc/new/?pc=" + code
    return it
refresh.fetch = fake_fetch
refresh.time.sleep = lambda s: None
refresh.main()
'''


class SiteCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="tg-test-"))
        self.root = self.tmp / "site"
        shutil.copytree(REPO, self.root, ignore=shutil.ignore_patterns(".git", ".env", ".claude", "__pycache__", "tests"))
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(("RAKUTEN_", "TG_"))}
        self.env.update({"RAKUTEN_AFFILIATE_ID": "DUMMYAFF", "TG_TODAY": TODAY})

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_script(self, *args, env=None, check=True):
        r = subprocess.run([PY, *args], cwd=self.root, env=env or self.env, capture_output=True, text=True)
        if check and r.returncode != 0:
            self.fail(f"{args} failed: {r.stdout}\n{r.stderr}")
        return r

    def gen_all(self, env=None):
        for s in ("generate.py", "generate_article.py", "generate_blog.py", "generate_pages.py"):
            self.run_script(f"scripts/{s}", env=env)

    def read(self, rel):
        return (self.root / rel).read_text(encoding="utf-8")

    def write_json(self, rel, data):
        (self.root / rel).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    def json(self, rel):
        return json.loads(self.read(rel))

    def add_post(self, **kw):
        posts = self.json("research/blog_posts.json")
        post = {"slug": "zz-test", "title": "テスト記事", "type": "diary", "published": "2026-10-01",
                "updated": "2026-10-01", "excerpt": "説明", "cover": "img/x.jpg", "persona": "犬連れ"}
        post.update(kw)
        posts.append(post)
        self.write_json("research/blog_posts.json", posts)
        (self.root / "content/blog" / f"{post['slug']}.html").write_text("<p>本文</p>", encoding="utf-8")
        return post


class T1RefreshAffiliate(SiteCase):
    def test_refresh_stops_without_affiliate_id(self):
        before = self.read("research/items.json")
        env = dict(self.env, RAKUTEN_APP_ID="dummy", RAKUTEN_ACCESS_KEY="dummy")
        env.pop("RAKUTEN_AFFILIATE_ID")
        r = self.run_script("-c", FAKE_REFRESH, str(self.root), "no_aff_url", env=env, check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("RAKUTEN_AFFILIATE_ID", r.stderr + r.stdout)
        self.assertEqual(self.read("research/items.json"), before, "items.json が書き換わってはいけない")

    def test_refresh_keeps_old_affiliate_url_when_api_omits_it(self):
        old = self.json("research/items.json")
        env = dict(self.env, RAKUTEN_APP_ID="dummy", RAKUTEN_ACCESS_KEY="dummy")
        self.run_script("-c", FAKE_REFRESH, str(self.root), "no_aff_url", env=env)
        new = self.json("research/items.json")
        for code, it in old.items():
            if it.get("affiliateUrl"):
                self.assertEqual(new[code]["affiliateUrl"], it["affiliateUrl"])
        self.assertTrue(all(v["itemPrice"] == 1234 for v in new.values()), "価格は更新されること")

    def test_refresh_accepts_new_code_missing_from_items(self):
        picks = self.json("research/picks.json")
        picks[0]["items"].append({"itemCode": "new:1", "name": "新商品"})
        self.write_json("research/picks.json", picks)
        env = dict(self.env, RAKUTEN_APP_ID="dummy", RAKUTEN_ACCESS_KEY="dummy")
        self.run_script("-c", FAKE_REFRESH, str(self.root), "with_aff_url", env=env)
        new_item = self.json("research/items.json")["new:1"]
        self.assertTrue(new_item["affiliateUrl"].startswith("https://hb.afl.rakuten.co.jp/hgc/"))
        # 新しい商品を含めて、サイト全体の生成・点検まで通ること
        self.run_script("scripts/build_site.py")
        self.assertIn("hb.afl.rakuten.co.jp/hgc/new/?pc=new:1", self.read("docs/goods.html"))

    def test_generate_stops_when_listed_item_lost_affiliate_url(self):
        items = self.json("research/items.json")
        code = self.json("research/picks.json")[0]["items"][0]["itemCode"]
        items[code].pop("affiliateUrl")
        self.write_json("research/items.json", items)
        before = self.read("docs/goods.html")
        r = self.run_script("scripts/generate.py", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.read("docs/goods.html"), before)


class T2HotelAffiliate(SiteCase):
    def test_blog_generation_stops_without_affiliate_id(self):
        before = self.read("docs/blog-tokinos-ito-villa.html")
        env = dict(self.env)
        env.pop("RAKUTEN_AFFILIATE_ID")
        r = self.run_script("scripts/generate_blog.py", env=env, check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.read("docs/blog-tokinos-ito-villa.html"), before)

    def test_hotel_boxes_are_affiliate_links(self):
        self.run_script("scripts/generate_blog.py")
        for slug in ("tokinos-ito-villa", "bayside-kanaya-dog"):
            html = self.read(f"docs/blog-{slug}.html")
            self.assertIn("hb.afl.rakuten.co.jp/hgc/DUMMYAFF/", html)
            self.assertNotRegex(html, r'href="https?://travel\.rakuten\.co\.jp/HOTEL/')


class T3DraftAndFuture(SiteCase):
    def assert_not_published(self, slug):
        self.assertFalse((self.root / f"docs/blog-{slug}.html").exists())
        for page in ("docs/index.html", "docs/blog.html", "docs/sitemap.xml"):
            self.assertNotIn(slug, self.read(page), page)

    def test_draft_post_is_not_published(self):
        self.add_post(slug="zz-draft", status="draft")
        self.gen_all()
        self.assert_not_published("zz-draft")

    def test_future_post_is_not_published_until_its_date(self):
        self.add_post(slug="zz-future", published=FUTURE, updated=FUTURE)
        self.gen_all()
        self.assert_not_published("zz-future")
        self.gen_all(env=dict(self.env, TG_TODAY=FUTURE))
        self.assertTrue((self.root / "docs/blog-zz-future.html").exists())
        self.assertIn("zz-future", self.read("docs/sitemap.xml"))

    def test_invalid_status_is_rejected(self):
        self.add_post(slug="zz-bad", status="publish")
        r = self.run_script("scripts/generate_blog.py", check=False)
        self.assertNotEqual(r.returncode, 0)


class T4RemovedPages(SiteCase):
    def test_removed_post_is_reported_not_deleted(self):
        posts = [p for p in self.json("research/blog_posts.json") if p["slug"] != "iphone-travel-video"]
        self.write_json("research/blog_posts.json", posts)
        r = self.run_script("scripts/generate_blog.py")
        self.assertIn("blog-iphone-travel-video.html", r.stderr)
        self.assertTrue((self.root / "docs/blog-iphone-travel-video.html").exists(), "既存ページは削除しない")
        self.assertNotIn("iphone-travel-video", self.read("docs/sitemap.xml"))
        c = self.run_script("scripts/check_site.py", check=False)
        self.assertEqual(c.returncode, 1)
        self.assertIn("blog-iphone-travel-video.html", c.stdout)

    def test_guide_removed_from_articles_json_is_not_regenerated(self):
        arts = [a for a in self.json("research/articles.json") if a["path"] != "domestic-packing-list.html"]
        self.write_json("research/articles.json", arts)
        before = self.read("docs/domestic-packing-list.html")
        r = self.run_script("scripts/generate_article.py")
        self.assertIn("domestic-packing-list.html", r.stderr)
        self.assertEqual(self.read("docs/domestic-packing-list.html"), before)
        self.assertNotIn("domestic-packing-list", self.read("docs/sitemap.xml"))

    def test_draft_guide_is_not_generated(self):
        arts = self.json("research/articles.json")
        arts[0]["status"] = "draft"
        self.write_json("research/articles.json", arts)
        before = self.read(f"docs/{arts[0]['path']}")
        self.run_script("scripts/generate_article.py")
        self.assertEqual(self.read(f"docs/{arts[0]['path']}"), before)


class T5Escaping(SiteCase):
    EVIL_TITLE = '海の"宿"</script><script>alert(1)</script>'
    EVIL_EXCERPT = '説明"><img src=x onerror=alert(1)>'

    def test_post_title_and_excerpt_are_escaped(self):
        posts = self.json("research/blog_posts.json")
        target = next(p for p in posts if p["slug"] == "bayside-kanaya-dog")
        target["title"], target["excerpt"] = self.EVIL_TITLE, self.EVIL_EXCERPT
        self.write_json("research/blog_posts.json", posts)
        self.gen_all()
        for page in ("docs/blog-bayside-kanaya-dog.html", "docs/blog.html", "docs/index.html"):
            html = self.read(page)
            self.assertNotIn("<script>alert(1)", html, page)
            self.assertNotIn("<img src=x", html, page)
        html = self.read("docs/blog-bayside-kanaya-dog.html")
        self.assertIn("&quot;宿&quot;", html)
        ld = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1)
        self.assertNotIn("</", ld)
        self.assertIn(self.EVIL_TITLE, json.loads(ld)["headline"], "JSON-LDの中身は元の文字列のまま")

    def test_category_text_is_escaped(self):
        picks = self.json("research/picks.json")
        picks[0]["title"], picks[0]["lead"] = "<b>見出し</b>", "<i>説明</i>"
        self.write_json("research/picks.json", picks)
        self.run_script("scripts/generate.py")
        goods = self.read("docs/goods.html")
        self.assertNotIn("<b>見出し</b>", goods)
        self.assertNotIn("<i>説明</i>", goods)

    def test_non_https_tiktok_url_is_rejected(self):
        posts = self.json("research/blog_posts.json")
        next(p for p in posts if p["slug"] == "tokinos-ito-villa")["tiktok"] = "javascript:alert(1)"
        self.write_json("research/blog_posts.json", posts)
        r = self.run_script("scripts/generate_blog.py", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("javascript:", self.read("docs/blog-tokinos-ito-villa.html"))


class T6PartialFailure(SiteCase):
    def test_generate_failure_leaves_goods_and_index_untouched(self):
        # 価格を変えて「書き込まれれば goods.html が変わる」状態にしてから、トップ生成で失敗させる
        items = self.json("research/items.json")
        code = self.json("research/picks.json")[0]["items"][0]["itemCode"]
        items[code]["itemPrice"] = int(items[code]["itemPrice"]) + 1
        self.write_json("research/items.json", items)
        posts = self.json("research/blog_posts.json")
        del posts[0]["published"]
        self.write_json("research/blog_posts.json", posts)
        before = {p: self.read(p) for p in ("docs/goods.html", "docs/index.html")}
        r = self.run_script("scripts/generate.py", check=False)
        self.assertNotEqual(r.returncode, 0)
        for p, text in before.items():
            self.assertEqual(self.read(p), text, f"{p} が中途半端に更新された")

    def test_unknown_item_code_stops_before_writing(self):
        picks = self.json("research/picks.json")
        picks[0]["items"].append({"itemCode": "nope:0", "name": "存在しない"})
        self.write_json("research/picks.json", picks)
        before = self.read("docs/goods.html")
        r = self.run_script("scripts/generate.py", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.read("docs/goods.html"), before)

    def test_atomic_write_keeps_original_on_failure(self):
        sys.path.insert(0, str(self.root / "scripts"))
        try:
            import importlib
            import safety
            importlib.reload(safety)
            target = self.root / "research/meta.json"
            original = target.read_text(encoding="utf-8")
            real_replace = safety.os.replace
            safety.os.replace = lambda *a: (_ for _ in ()).throw(OSError("simulated"))
            try:
                with self.assertRaises(OSError):
                    safety.atomic_write_text(target, "{broken")
            finally:
                safety.os.replace = real_replace
            self.assertEqual(target.read_text(encoding="utf-8"), original)
            self.assertEqual(list(target.parent.glob(".meta.json.*.tmp")), [], "一時ファイルが残らない")
        finally:
            sys.path.remove(str(self.root / "scripts"))

    def test_legacy_build_does_not_overwrite_index(self):
        before = self.read("docs/index.html")
        r = self.run_script("scripts/build.py", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.read("docs/index.html"), before)


class T7WeeklyUpdate(SiteCase):
    def setUp(self):
        super().setUp()
        if not shutil.which("git"):
            self.skipTest("git が無い環境")
        self.remote = self.tmp / "remote.git"
        e = dict(self.env, **GIT_ENV)
        run = lambda *a, cwd=self.root: subprocess.run(a, cwd=cwd, env=e, check=True, capture_output=True)
        run("git", "init", "-q", "--bare", str(self.remote), cwd=self.tmp)
        # 外部APIに出ないよう refresh.py を何もしないスタブに置き換えたテスト用リポジトリ
        (self.root / "scripts/refresh.py").write_text('print("refresh stub")\n', encoding="utf-8")
        run("git", "init", "-q", "-b", "main")
        run("git", "add", "-A")
        run("git", "commit", "-qm", "init")
        run("git", "remote", "add", "origin", str(self.remote))
        run("git", "push", "-q", "origin", "main")
        self.genv = e
        self.head = lambda where: subprocess.run(["git", "rev-parse", "main"], cwd=where, env=e,
                                                 capture_output=True, text=True).stdout.strip()

    def weekly(self, *args):
        return subprocess.run(["bash", "scripts/weekly_update.sh", *args], cwd=self.root,
                              env=self.genv, capture_output=True, text=True)

    def test_never_pushes(self):
        remote_before = self.head(self.remote)
        (self.root / "research/unapproved.json").write_text("{}", encoding="utf-8")
        r = self.weekly()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.head(self.remote), remote_before, "push されてはいけない")
        self.assertIn("unapproved.json", r.stdout, "変更一覧に表示されること")

    def test_unknown_page_in_docs_stops_weekly_before_any_commit(self):
        remote_before, local_before = self.head(self.remote), self.head(self.root)
        (self.root / "docs/unapproved.html").write_text("<p>未承認</p>", encoding="utf-8")
        r = self.weekly("--commit")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual((self.head(self.remote), self.head(self.root)), (remote_before, local_before))

    def test_commit_mode_refuses_untracked_files(self):
        local_before = self.head(self.root)
        (self.root / "research/wip.json").write_text("{}", encoding="utf-8")
        r = self.weekly("--commit")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.head(self.root), local_before, "コミットされてはいけない")

    def test_commit_mode_commits_tracked_changes_only_and_does_not_push(self):
        remote_before, local_before = self.head(self.remote), self.head(self.root)
        # docs/ research/ 以外の変更（未ステージ）があっても、コミットには入らないこと
        (self.root / "README.md").write_text(self.read("README.md") + "\n作業中\n", encoding="utf-8")
        r = self.weekly("--commit")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.head(self.remote), remote_before, "push されてはいけない")
        self.assertNotEqual(self.head(self.root), local_before, "ローカルにはコミットされること")
        files = subprocess.run(["git", "show", "--name-only", "--format=", "HEAD"], cwd=self.root, env=self.genv,
                               capture_output=True, text=True).stdout.split()
        self.assertTrue(files, "コミット内容が空ではないこと")
        self.assertTrue(all(f.startswith(("docs/", "research/")) for f in files), files)

    def test_commit_mode_refuses_when_unrelated_changes_are_staged(self):
        local_before = self.head(self.root)
        (self.root / "scripts/extra.py").write_text("print(1)\n", encoding="utf-8")
        subprocess.run(["git", "add", "scripts/extra.py"], cwd=self.root, env=self.genv, check=True)
        r = self.weekly("--commit")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ステージ済み", r.stdout)
        self.assertEqual(self.head(self.root), local_before, "コミットされてはいけない")


def _git_head_docs():
    """比較の基準：リポジトリの Git HEAD（コミット済み）の docs/。Git が使えなければ作業ツリーの docs/。"""
    if shutil.which("git") and (REPO / ".git").exists():
        r = subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "--name-only", "HEAD", "docs"],
                           capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            names = r.stdout.split("\n")
            read = lambda n: subprocess.run(["git", "-C", str(REPO), "show", f"HEAD:{n}"],  # noqa: E731
                                            capture_output=True, check=True).stdout
            return "git HEAD", {n[len("docs/"):]: read(n) for n in names if n}
    return "作業ツリー", {str(p.relative_to(REPO / "docs")): p.read_bytes()
                         for p in (REPO / "docs").rglob("*") if p.is_file()}


class T8NoRegression(SiteCase):
    """修正後のコードで今のデータから作ったページが、Git HEAD（コミット済み）の公開ページと
    （表示日付・アフィリエイトIDの値を除いて）同じであること。"""

    @staticmethod
    def norm(text):
        if isinstance(text, bytes):
            text = text.decode("utf-8")
        text = re.sub(r"hgc/[^/]+/", "hgc/<AFF>/", text)
        return re.sub(r"\d{4}年\d{2}月\d{2}日時点", "<DATE>時点", text)

    def test_generated_pages_match_committed_docs(self):
        source, committed = _git_head_docs()
        self.gen_all()
        pages = {n: t for n, t in committed.items() if n.endswith(".html") or n == "sitemap.xml"}
        self.assertTrue(pages)
        for name, text in pages.items():
            with self.subTest(page=name, source=source):
                self.assertEqual(self.norm(self.read(f"docs/{name}")), self.norm(text))

    def test_build_site_matches_committed_docs_and_keeps_static_files(self):
        source, committed = _git_head_docs()
        self.run_script("scripts/build_site.py")
        after = sorted(str(p.relative_to(self.root / "docs")) for p in (self.root / "docs").rglob("*") if p.is_file())
        self.assertEqual(after, sorted(committed), f"ファイル構成（画像・.nojekyll 等を含む）が {source} と同じこと")
        for name, data in committed.items():
            with self.subTest(file=name):
                got = (self.root / "docs" / name).read_bytes()
                if name.endswith((".html", ".xml")):
                    self.assertEqual(self.norm(got), self.norm(data))
                else:
                    self.assertEqual(got, data)

    def test_check_site_passes_on_current_data(self):
        r = self.run_script("scripts/check_site.py")
        self.assertIn("点検OK", r.stdout)


class T9CodexFindings(SiteCase):
    """Codex 独立レビュー（2026-10-24）の指摘に対する再発防止テスト。"""

    def snapshot_docs(self):
        return {str(p.relative_to(self.root / "docs")): p.read_bytes()
                for p in (self.root / "docs").rglob("*") if p.is_file()}

    # --- 指摘1：下書き化・未来日化した公開済み記事は公開フォルダから外れる（案A） ---
    def test_draft_existing_post_is_removed_from_docs_but_source_kept(self):
        posts = self.json("research/blog_posts.json")
        next(p for p in posts if p["slug"] == "iphone-travel-video")["status"] = "draft"
        self.write_json("research/blog_posts.json", posts)
        r = self.run_script("scripts/build_site.py")
        self.assertIn("blog-iphone-travel-video.html", r.stdout)
        self.assertFalse((self.root / "docs/blog-iphone-travel-video.html").exists())
        self.assertTrue((self.root / "content/blog/iphone-travel-video.html").exists(), "本文は消さない")
        self.assertTrue((self.root / ".docs-prev/blog-iphone-travel-video.html").exists(), "直前の状態は控えに残る")
        self.assertTrue((self.root / "docs/.nojekyll").exists())
        self.assertTrue((self.root / "docs/img/tokinos/bath.jpg").exists())
        self.assertEqual(self.run_script("scripts/check_site.py").returncode, 0)

    def test_future_dated_existing_guide_is_removed_from_docs(self):
        arts = self.json("research/articles.json")
        arts[1]["published"] = "2099-01-01"
        self.write_json("research/articles.json", arts)
        self.run_script("scripts/build_site.py")
        self.assertFalse((self.root / f"docs/{arts[1]['path']}").exists())
        self.assertNotIn(arts[1]["path"], self.read("docs/sitemap.xml"))

    def test_unknown_handmade_page_aborts_without_touching_docs(self):
        (self.root / "docs/handmade.html").write_text("<p>手作り</p>", encoding="utf-8")
        before = self.snapshot_docs()
        r = self.run_script("scripts/build_site.py", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.snapshot_docs(), before)

    # --- 指摘2：「目的から探す」は公開対象外の記事へリンクしない ---
    def test_purpose_finder_skips_unpublished_pages(self):
        posts = self.json("research/blog_posts.json")
        next(p for p in posts if p["slug"] == "dog-travel-1night2days")["status"] = "draft"
        self.write_json("research/blog_posts.json", posts)
        code = "import sys; sys.path.insert(0,'scripts'); import generate; print(generate.purpose_finder_html())"
        out = self.run_script("-c", code).stdout
        self.assertNotIn("blog-dog-travel-1night2days.html", out)
        self.assertIn("blog-iphone-travel-video.html", out)

    # --- 指摘3：途中で失敗しても docs/ は一切変わらない ---
    def test_build_site_failure_leaves_docs_untouched(self):
        items = self.json("research/items.json")
        code = self.json("research/picks.json")[0]["items"][0]["itemCode"]
        items[code]["itemPrice"] = int(items[code]["itemPrice"]) + 1     # goods.html が変わる状態にする
        self.write_json("research/items.json", items)
        posts = self.json("research/blog_posts.json")
        next(p for p in posts if p["slug"] == "tokinos-ito-villa")["tiktok"] = "http://insecure.example/"  # 3本目で失敗
        self.write_json("research/blog_posts.json", posts)
        before = self.snapshot_docs()
        meta_before = self.read("research/blog_meta.json")
        r = self.run_script("scripts/build_site.py", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.snapshot_docs(), before, "docs/ が一部だけ更新されてはいけない")
        self.assertEqual(list(self.root.glob(".docs-staging*")), [], "作業用フォルダは片付ける")
        self.assertEqual(self.read("research/blog_meta.json"), meta_before, "research/ も変わらない")

    def test_build_site_check_failure_leaves_docs_untouched(self):
        (self.root / "content/blog/bayside-kanaya-dog.html").write_text(
            self.read("content/blog/bayside-kanaya-dog.html") + "<a href='https://item.rakuten.co.jp/shop/x/'>x</a>",
            encoding="utf-8")
        before = self.snapshot_docs()
        r = self.run_script("scripts/build_site.py", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.snapshot_docs(), before)

    # --- 指摘5：affiliateUrl は形式まで検証する ---
    def test_invalid_affiliate_urls_are_rejected(self):
        code = self.json("research/picks.json")[0]["items"][0]["itemCode"]
        for bad in ("https://item.rakuten.co.jp/shop/x/", "http://hb.afl.rakuten.co.jp/x", "javascript:alert(1)",
                    "https://hb.afl.rakuten.co.jp.evil.example/x"):
            with self.subTest(url=bad):
                items = self.json("research/items.json")
                items[code]["affiliateUrl"] = bad
                self.write_json("research/items.json", items)
                before = self.read("docs/goods.html")
                r = self.run_script("scripts/generate.py", check=False)
                self.assertNotEqual(r.returncode, 0)
                self.assertEqual(self.read("docs/goods.html"), before)
                c = self.run_script("scripts/check_site.py", check=False)
                self.assertEqual(c.returncode, 1)
                self.assertIn(code, c.stdout)

    def test_refresh_does_not_store_non_affiliate_url(self):
        env = dict(self.env, RAKUTEN_APP_ID="dummy", RAKUTEN_ACCESS_KEY="dummy")
        fake = FAKE_REFRESH.replace('"https://hb.afl.rakuten.co.jp/hgc/new/?pc=" + code', '"https://item.rakuten.co.jp/x/" + code')
        self.assertNotEqual(fake, FAKE_REFRESH, "（前提）偽応答の置き換えが効いていること")
        old = self.json("research/items.json")
        self.run_script("-c", fake, str(self.root), "with_aff_url", env=env)
        new = self.json("research/items.json")
        for code, it in old.items():
            self.assertEqual(new[code]["affiliateUrl"], it["affiliateUrl"], "形式の正しくないURLで上書きしない")

    # --- 指摘6：リンク点検は HTML を解析して判定する ---
    def test_check_site_detects_link_variants(self):
        variants = [
            "<a href='https://travel.rakuten.co.jp/HOTEL/1/1.html'>a</a>",
            '<a class="x"   href = "https://travel.rakuten.co.jp/HOTEL/2/2.html">b</a>',
            '<a href="HTTPS://TRAVEL.RAKUTEN.CO.JP/hotelinfo/plan/3">c</a>',
            '<a href="https://item.rakuten.co.jp/shop/item/">d</a>',
            '<a href="javascript:alert(1)">e</a>',
        ]
        for v in variants:
            with self.subTest(link=v):
                page = self.root / "docs/about.html"
                original = page.read_text(encoding="utf-8")
                page.write_text(original.replace("</main>", v + "</main>"), encoding="utf-8")
                c = self.run_script("scripts/check_site.py", check=False)
                page.write_text(original, encoding="utf-8")
                self.assertEqual(c.returncode, 1, v)

    def test_check_site_accepts_affiliate_and_other_links(self):
        page = self.root / "docs/about.html"
        page.write_text(self.read("docs/about.html").replace(
            "</main>", '<a href="https://hb.afl.rakuten.co.jp/hgc/x/?pc=a&amp;m=b">ok</a>'
                       '<a href="https://developers.rakuten.com/">ok</a></main>'), encoding="utf-8")
        self.assertEqual(self.run_script("scripts/check_site.py").returncode, 0)


CRASH_WRAPPER = r'''
import os, sys
sys.argv = ["build_site.py"]
sys.path.insert(0, "scripts")
import build_site
mode = MODE
real = os.rename
def fake(src, dst):
    if os.path.basename(str(dst)) == "docs" and os.path.basename(os.path.dirname(str(src))).startswith(".docs-staging-"):
        if mode == "fail":
            raise OSError("simulated rename failure")
        if mode == "crash":
            os._exit(9)      # docs/ を控えに移した直後、新しい docs/ を置く前に強制終了
    return real(src, dst)
build_site.os.rename = fake
real_w = build_site.atomic_write_text
def fake_w(path, text):
    if mode == "crash_meta" and os.path.basename(str(path)) == "blog_meta.json":
        os._exit(8)          # 新しい docs/ を置いた後、一覧の更新日を反映する前に強制終了
    return real_w(path, text)
build_site.atomic_write_text = fake_w
build_site.main()
'''


class T10SecondCodexFindings(SiteCase):
    """Codex 再レビュー（2026-10-25）の指摘 N1〜N8 に対する再発防止テスト。"""

    def snapshot_docs(self):
        return {str(p.relative_to(self.root / "docs")): p.read_bytes()
                for p in (self.root / "docs").rglob("*") if p.is_file()}

    def add_newer_post(self):
        return self.add_post(slug="zz-newer", published=NEWER, updated=NEWER)

    # --- N1：切り替えの途中で止まっても docs/ を自動で戻す ---
    def test_switch_rename_failure_restores_docs(self):
        self.add_newer_post()
        before = self.snapshot_docs()
        r = self.run_script("-c", CRASH_WRAPPER.replace("MODE", "'fail'"), check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.snapshot_docs(), before, "失敗したら元の docs/ に戻る")
        self.assertFalse((self.root / ".docs-prev-old").exists())

    def test_crash_between_renames_is_recovered_on_next_run(self):
        self.run_script("scripts/build_site.py")           # .docs-prev/ がある状態を作る
        self.add_newer_post()
        before = self.snapshot_docs()
        r = self.run_script("-c", CRASH_WRAPPER.replace("MODE", "'crash'"), check=False)
        self.assertEqual(r.returncode, 9)
        self.assertFalse((self.root / "docs").exists(), "（前提）切り替えの途中で止まり docs/ が無い状態")
        r = self.run_script("scripts/build_site.py", "--dry-run")
        self.assertIn("直前の状態に戻しました", r.stdout)
        self.assertEqual(self.snapshot_docs(), before, "直前の docs/ に戻る")
        self.assertTrue((self.root / ".docs-prev").exists(), "前々回の控えも失われない")
        self.assertFalse((self.root / ".docs-prev-old").exists())
        self.run_script("scripts/build_site.py")
        self.assertTrue((self.root / "docs/blog-zz-newer.html").exists())

    # --- N2：同時に2つ動かない ---
    def test_concurrent_run_is_refused(self):
        import fcntl
        before = self.snapshot_docs()
        with open(self.root / ".build_site.lock", "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            r = self.run_script("scripts/build_site.py", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("実行中", r.stdout + r.stderr)
        self.assertEqual(self.snapshot_docs(), before)

    def test_each_run_uses_its_own_staging_folder_and_cleans_up(self):
        stale = self.root / ".docs-staging-stale"
        (stale / "docs").mkdir(parents=True)
        self.run_script("scripts/build_site.py")
        self.assertEqual(list(self.root.glob(".docs-staging*")), [])

    # --- N3：dry-run・失敗時に research/ を書き換えない ---
    def test_dry_run_changes_nothing(self):
        self.add_newer_post()
        before_docs = self.snapshot_docs()
        before_research = {p.name: p.read_bytes() for p in (self.root / "research").glob("*.json")}
        self.run_script("scripts/build_site.py", "--dry-run")
        self.assertEqual(self.snapshot_docs(), before_docs)
        self.assertEqual({p.name: p.read_bytes() for p in (self.root / "research").glob("*.json")}, before_research)
        self.run_script("scripts/build_site.py")
        self.assertEqual(self.json("research/blog_meta.json")["updated"], NEWER, "本番実行では更新される")
        self.assertIn(f"<lastmod>{NEWER}</lastmod>", self.read("docs/sitemap.xml"))

    def test_check_failure_does_not_change_research(self):
        self.add_newer_post()
        (self.root / "content/blog/zz-newer.html").write_text('<a href="javascript:alert(1)">x</a>', encoding="utf-8")
        meta = self.read("research/blog_meta.json")
        r = self.run_script("scripts/build_site.py", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.read("research/blog_meta.json"), meta)

    # --- N4：手置きページを消さない ---
    def test_handmade_blog_page_is_not_deleted(self):
        (self.root / "docs/blog-special.html").write_text("<p>手作り</p>", encoding="utf-8")
        before = self.snapshot_docs()
        r = self.run_script("scripts/build_site.py", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("blog-special.html", r.stdout + r.stderr)
        self.assertEqual(self.snapshot_docs(), before)

    def test_post_removed_from_list_stops_with_draft_guidance(self):
        posts = [p for p in self.json("research/blog_posts.json") if p["slug"] != "iphone-travel-video"]
        self.write_json("research/blog_posts.json", posts)
        before = self.snapshot_docs()
        r = self.run_script("scripts/build_site.py", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("draft", r.stdout + r.stderr)
        self.assertNotIn("GENERATED_PAGES", r.stdout + r.stderr, "誤解を招く案内を出さない")
        self.assertEqual(self.snapshot_docs(), before)

    # --- N5：一覧から消したガイドへリンクしない ---
    def test_purpose_finder_skips_guide_removed_from_articles(self):
        arts = [a for a in self.json("research/articles.json") if a["path"] != "domestic-packing-list.html"]
        self.write_json("research/articles.json", arts)
        code = "import sys; sys.path.insert(0,'scripts'); import generate; print(generate.purpose_finder_html())"
        out = self.run_script("-c", code).stdout
        self.assertNotIn("domestic-packing-list.html", out)
        self.assertIn("packing-checklist.html", out)

    def test_guide_page_list_matches_generator(self):
        code = ("import sys; sys.path.insert(0,'scripts'); import generate_article, safety; "
                "print(sorted(generate_article.ARTICLES) == sorted(safety.GUIDE_PAGES))")
        self.assertEqual(self.run_script("-c", code).stdout.strip(), "True")

    # --- N8：URL検査の境界 ---
    def test_affiliate_url_rules(self):
        code = r"""
import sys; sys.path.insert(0, 'scripts'); import safety
ok = ['https://hb.afl.rakuten.co.jp/hgc/abc/?pc=x&m=y']
ng = ['https://hb.afl.rakuten.co.jp:8443/hgc/abc/', 'https://user@hb.afl.rakuten.co.jp/hgc/abc/',
      'https://hb.afl.rakuten.co.jp/other/abc/', 'https://hb.afl.rakuten.co.jp:bad/hgc/']
print(all(safety.is_affiliate_url(u) for u in ok), any(safety.is_affiliate_url(u) for u in ng))
print(safety.link_problems('<a href="https://notrakuten.co.jp/x">a</a><a href="https://rakuten.co.jp/x">b</a>'))
"""
        lines = self.run_script("-c", code).stdout.strip().splitlines()
        self.assertEqual(lines[0], "True False")
        self.assertNotIn("notrakuten", lines[1], "別ドメインを楽天と誤判定しない")
        self.assertIn("rakuten.co.jp/x", lines[1])


class T11FinalFindings(SiteCase):
    """Codex 3回目のレビュー（2026-10-25）の指摘に対する再発防止テスト。"""

    def snapshot_docs(self):
        return {str(p.relative_to(self.root / "docs")): p.read_bytes()
                for p in (self.root / "docs").rglob("*") if p.is_file()}

    def add_newer_post(self):
        return self.add_post(slug="zz-newer", published=NEWER, updated=NEWER)

    # --- 指摘1：docs/ と blog_meta の確定処理 ---
    def test_crash_after_switch_completes_blog_meta_on_next_run(self):
        self.add_newer_post()
        r = self.run_script("-c", CRASH_WRAPPER.replace("MODE", "'crash_meta'"), check=False)
        self.assertEqual(r.returncode, 8)
        self.assertTrue((self.root / "docs/blog-zz-newer.html").exists(), "（前提）新しい docs/ は置かれている")
        self.assertEqual(self.json("research/blog_meta.json")["updated"], INITIAL_BLOG_META, "（前提）更新日は未反映")
        r = self.run_script("scripts/build_site.py", "--dry-run")
        self.assertIn("後処理", r.stdout)
        self.assertEqual(self.json("research/blog_meta.json")["updated"], NEWER, "次回の実行で反映が完了する")
        self.assertFalse((self.root / ".build_site.pending.json").exists())

    def test_normal_run_does_not_report_recovery(self):
        self.add_newer_post()
        r = self.run_script("scripts/build_site.py")
        self.assertNotIn("前回の切り替え", r.stdout, "通常の実行で復旧メッセージを出さない")
        self.assertEqual(self.json("research/blog_meta.json")["updated"], NEWER)

    def test_switch_failure_keeps_blog_meta_and_clears_record(self):
        self.add_newer_post()
        meta = self.read("research/blog_meta.json")
        r = self.run_script("-c", CRASH_WRAPPER.replace("MODE", "'fail'"), check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.read("research/blog_meta.json"), meta, "切り替えていないので更新日も変えない")
        self.assertFalse((self.root / ".build_site.pending.json").exists())
        self.run_script("scripts/build_site.py", "--dry-run")
        self.assertEqual(self.read("research/blog_meta.json"), meta, "次回の実行でも反映しない")

    def test_crash_before_new_docs_does_not_apply_blog_meta(self):
        self.run_script("scripts/build_site.py")
        self.add_newer_post()
        meta = self.read("research/blog_meta.json")
        r = self.run_script("-c", CRASH_WRAPPER.replace("MODE", "'crash'"), check=False)
        self.assertEqual(r.returncode, 9)
        self.run_script("scripts/build_site.py", "--dry-run")
        self.assertEqual(self.read("research/blog_meta.json"), meta, "元に戻した場合は更新日も変えない")

    # --- 指摘2：更新処理どうしの排他 ---
    def test_generators_and_refresh_refuse_while_locked(self):
        import fcntl
        env = dict(self.env, RAKUTEN_APP_ID="dummy", RAKUTEN_ACCESS_KEY="dummy")
        before = self.snapshot_docs()
        items = self.read("research/items.json")
        with open(self.root / ".build_site.lock", "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            for script in ("scripts/generate.py", "scripts/generate_blog.py", "scripts/generate_article.py",
                           "scripts/generate_pages.py"):
                with self.subTest(script=script):
                    r = self.run_script(script, check=False)
                    self.assertNotEqual(r.returncode, 0)
                    self.assertIn("実行中", r.stdout + r.stderr)
            r = self.run_script("-c", FAKE_REFRESH, str(self.root), "with_aff_url", env=env, check=False)
            self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.snapshot_docs(), before)
        self.assertEqual(self.read("research/items.json"), items)

    def test_build_site_refresh_runs_refresh_inside_the_lock(self):
        (self.root / "scripts/refresh.py").write_text(
            "import pathlib; pathlib.Path('research/refresh_ran.txt').write_text('ok')\n", encoding="utf-8")
        self.run_script("scripts/build_site.py", "--refresh")
        self.assertTrue((self.root / "research/refresh_ran.txt").exists())
        r = self.run_script("scripts/build_site.py", "--refresh", "--dry-run", check=False)
        self.assertNotEqual(r.returncode, 0)

    # --- 指摘3：公開記事が0件のとき ---
    def test_zero_published_posts_updates_blog_meta(self):
        posts = self.json("research/blog_posts.json")
        for p in posts:
            p["status"] = "draft"
        self.write_json("research/blog_posts.json", posts)
        self.run_script("scripts/build_site.py")
        self.assertEqual(self.json("research/blog_meta.json")["updated"], TODAY)
        self.assertEqual(list((self.root / "docs").glob("blog-*.html")), [])


if __name__ == "__main__":
    unittest.main()
