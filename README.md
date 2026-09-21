# travel-goods

旅行グッズの紹介サイト（静的サイト）。

## 構成
- `docs/` 公開するHTML/CSS
- `scripts/build.py` 楽天商品検索APIから商品を取得して `docs/index.html` を生成

## 使い方
```bash
cp .env.example .env      # RAKUTEN_APP_ID と RAKUTEN_ACCESS_KEY を記入（.env はgit管理外）
python3 scripts/build.py
open docs/index.html
```

## 価格の定期更新
毎週月曜9時に `scripts/weekly_update.sh` が動き、価格を再取得して `docs/` を更新・プッシュします（launchd: `~/Library/LaunchAgents/jp.travel-goods.weekly-update.plist`）。
- ログ: `~/Library/Logs/travel-goods-update.log`
- 手動実行: `bash scripts/weekly_update.sh`
- 停止: `launchctl bootout gui/$(id -u)/jp.travel-goods.weekly-update`
- リポジトリは Desktop などmacOSの保護フォルダに置かないでください（自動実行が拒否されます）。
