# travel-goods

旅行グッズの紹介サイト「Refind travel」（旧：たびのおとも）（静的サイト、GitHub Pages公開）。
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
  - `generate_pages.py` 運営者情報・プライバシーポリシー・アフィリエイトについてを生成（`research/site_pages.json` に登録。内容はスクリプト内に直書き）
  - `sitemap.py` 上記すべてのページから `docs/sitemap.xml` / `robots.txt` を生成
  - `weekly_update.sh` 上記をまとめて実行し、点検と変更一覧の表示まで行う（定期実行用。自動コミット・自動プッシュはしない）
  - `build_site.py` **サイト全体の生成はこれを使う。** 作業フォルダで全ページを生成→点検→合格したときだけ `docs/` を切り替える（生成・点検の途中で失敗したら `docs/` と `research/` は変わらない。切り替えの途中で止まっても、次回の実行で自動的に「元に戻す」か「切り替えを完了させる」。build_site・refresh・生成スクリプトは同じロックで同時に動かない）。下書き・未来日の記事のページは `docs/` から外れる（本文は content/ に残り、直前の docs/ は `.docs-prev/` に控える）。`--dry-run` で変更内容だけ確認できる（前回の中断からの復旧と古い作業フォルダの片付け以外は、何も書き換えない）。`--refresh` で価格の再取得から行う
  - `check_site.py` 公開前の点検（残存ページ、affiliateUrl の欠落・形式不正、アフィリエイトでない楽天リンク・危険なリンク）。読み取りのみ
  - `safety.py` 公開判定・アフィリエイト必須チェック・エスケープ・安全な書き込みの共通処理
  - `build.py` 旧スクリプト（実行すると docs/index.html を上書きするため、通常は実行できないようにしてある）

## 使い方
```bash
cp .env.example .env      # RAKUTEN_APP_ID / RAKUTEN_ACCESS_KEY / RAKUTEN_AFFILIATE_ID を記入（.env はgit管理外）
python3 scripts/build_site.py --dry-run   # 生成と点検だけ（docs/ と research/ は変えない。中断からの復旧だけは行う）
python3 scripts/build_site.py             # 生成→点検→合格したら docs/ を切り替え
open docs/index.html
```

## 商品カテゴリを増やす
1. `scripts/research.py` などで候補を集め、評価4.0以上・レビュー30件以上・在庫ありのものを選ぶ
2. `research/picks.json` にカテゴリと商品を追記し、`research/items.json` に商品データを追記
3. `python3 scripts/build_site.py` を実行（トップページのナビ・記事のナビ・サイトマップに自動で反映される）

`picks.json` の商品1件は、次の形です。

```json
{
  "itemCode": "楽天の商品コード",
  "name": "表示する商品名（短く整えたもの）",
  "desc": "紹介文",
  "for_whom": "「〇〇な人向け」の一言（未記入なら空文字でよい）",
  "scenes": ["国内旅行", "飛行機"],
  "used": {
    "is_used": false,
    "trip": "",
    "pros": "",
    "cons": "",
    "recommend_for": "",
    "photos": []
  }
}
```
- `scenes` は `research/scenes.json` にある旅行シーンのタグから選ぶ（表記ゆれ防止のため、自由記述にしない）
- `used.is_used` は、実際に旅行で使った商品だけ `true` にする。使っていない商品は、必ず `false` のままにする（感想の推測・捏造はしない）

## 旅行記（ブログ）を増やす
`content/blog/README.md` を参照。

## 価格の定期更新
`scripts/weekly_update.sh` は、`build_site.py --refresh` で価格の再取得とサイト全体の作り直し（点検込み）を同じロックの中で行い、変更一覧の表示まで行います。
**2026-10 の安全性改善で、自動コミット・自動プッシュはしなくなりました。** 差分を確認してから、人が手動で公開してください。
- `bash scripts/weekly_update.sh --commit` とすると、Gitで追跡済みの docs/ research/ の変更だけをコミットします。すでにステージ済みの変更がある場合や、docs/ research/ に新しいファイルがある場合は中止します。push はしません。
- 価格更新には `.env` の RAKUTEN_AFFILIATE_ID が必須です（無いとアフィリエイトURLが消えるため、実行を止めます）。
- **注意：** launchd の `jp.travel-goods.weekly-update` は、このスクリプトではなく旧JARVISの `connectors.weekly_stage` を呼び出していた。2026-10-25 に停止し、plist は `~/JARVIS/backups/launchagents/` に退避済み（下の「ログ」「停止」は以前の設定の説明）。このスクリプトを定期実行する設定は現在無い。
- ログ: `~/Library/Logs/travel-goods-update.log`
- 手動実行: `bash scripts/weekly_update.sh`
- 停止: `launchctl bootout gui/$(id -u)/jp.travel-goods.weekly-update`
- リポジトリは Desktop などmacOSの保護フォルダに置かないでください（自動実行が拒否されます）。

## 記事の公開・非公開
- `research/blog_posts.json` と `research/articles.json` の各記事に `"status": "draft"` を付けると、下書きとして生成されません（省略時は公開）。
- `published`（公開日）が未来の記事は、その日（日本時間）になるまで生成されません。
- **公開をやめたい記事は、一覧から消さずに `"status": "draft"` にしてください。** `python3 scripts/build_site.py` で生成すると、そのページは `docs/` から外れます（本文は content/、直前の状態は `.docs-prev/` に残ります）。
- 一覧に無い `blog-*.html` や、生成スクリプトが作らない手作りの .html が `docs/` にあると、`build_site.py` は消さないように中止します。不要と確認できたら、人が移動・削除してから実行してください。
- 生成スクリプト（generate*.py）を1本ずつ直接実行するのは開発用です。公開対象外のページは消えず警告が出るだけなので、公開前は必ず `build_site.py` を使ってください。
- 旧JARVISの週次処理（launchd: `jp.travel-goods.weekly-update`、`connectors.weekly_stage` を実行）は 2026-10-25 に停止済み。設定ファイルは `~/JARVIS/backups/launchagents/` に退避してある。

## テスト
```bash
python3 -m unittest discover -s tests -v   # 外部APIやGitHubには接続しません
python3 scripts/build_site.py --dry-run     # 生成と点検だけ行い、docs/ の変更内容を表示
python3 scripts/check_site.py               # 公開前の点検
```

## 変更後に必ず確認すること
- ページ内の件数（カテゴリ数など）が、実データ（`picks.json`など）から動的に算出されているか（固定文字列で書かない）
- 新しく追加したページが、全ページのナビ・`sitemap.xml` に反映されているか
- `python3 scripts/build_site.py` を実行し直し（点検込み）、`docs/` の内容を目視かgrepで確認してからコミットする
