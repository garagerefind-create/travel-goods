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
