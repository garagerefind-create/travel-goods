# travel-goods

旅行グッズの紹介サイト「たびのおとも」（静的サイト、GitHub Pages公開）。
https://garagerefind-create.github.io/travel-goods/

## 構成
- `docs/` 公開するHTML/CSS（生成物。直接編集しない）
- `research/` 商品データ・記事データ（`picks.json` が唯一の商品掲載リスト）
- `content/blog/` 旅行記の本文（書き方は `content/blog/README.md` を参照）
- `scripts/`
  - `research.py` 楽天商品検索APIでカテゴリごとに候補を集める（`research/candidates.json` に出力。手動で選定してから `picks.json` に反映）
  - `refresh.py` `picks.json` に載っている商品の価格・評価を再取得する（商品の入れ替えはしない）
  - `generate.py` トップページ（`docs/index.html`）を生成。共通のページテンプレート（`page_shell`）とナビ（`site_nav`）もここにある
  - `generate_article.py` 持ち物リストなどのガイド記事を生成（`research/articles.json` に登録）
  - `generate_blog.py` 旅行記を生成（`research/blog_posts.json` に登録。書き方は `content/blog/README.md`）
  - `sitemap.py` 上記すべてのページから `docs/sitemap.xml` / `robots.txt` を生成
  - `weekly_update.sh` 上記をまとめて実行し、変更があればコミット・プッシュする（定期実行用）

## 使い方
```bash
cp .env.example .env      # RAKUTEN_APP_ID / RAKUTEN_ACCESS_KEY / RAKUTEN_AFFILIATE_ID を記入（.env はgit管理外）
python3 scripts/generate.py
python3 scripts/generate_article.py
python3 scripts/generate_blog.py
open docs/index.html
```

## 商品カテゴリを増やす
1. `scripts/research.py` などで候補を集め、評価4.0以上・レビュー30件以上・在庫ありのものを選ぶ
2. `research/picks.json` にカテゴリと商品を追記し、`research/items.json` に商品データを追記
3. `python3 scripts/generate.py` を実行（トップページのナビ・記事のナビ・サイトマップに自動で反映される）

## 旅行記（ブログ）を増やす
`content/blog/README.md` を参照。

## 価格の定期更新
毎週月曜9時に `scripts/weekly_update.sh` が動き、価格を再取得してサイト全体を再生成し、変更があればプッシュします（launchd: `~/Library/LaunchAgents/jp.travel-goods.weekly-update.plist`）。
- ログ: `~/Library/Logs/travel-goods-update.log`
- 手動実行: `bash scripts/weekly_update.sh`
- 停止: `launchctl bootout gui/$(id -u)/jp.travel-goods.weekly-update`
- リポジトリは Desktop などmacOSの保護フォルダに置かないでください（自動実行が拒否されます）。

## 変更後に必ず確認すること
- ページ内の件数（カテゴリ数など）が、実データ（`picks.json`など）から動的に算出されているか（固定文字列で書かない）
- 新しく追加したページが、全ページのナビ・`sitemap.xml` に反映されているか
- `python3 scripts/generate.py && python3 scripts/generate_article.py && python3 scripts/generate_blog.py` を実行し直し、`docs/` の内容を目視かgrepで確認してからコミットする
