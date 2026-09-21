#!/bin/bash
# 価格を更新して、変更があれば docs を作り直してコミット・プッシュする（定期実行用）
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="/usr/local/bin:/usr/bin:/bin"
echo "=== $(date '+%Y-%m-%d %H:%M:%S') 開始 ==="

python3 scripts/refresh.py
python3 scripts/generate.py

if git diff --quiet -- docs research; then
  echo "変更なし（コミットしません）"
else
  git add docs research
  git commit -q -m "価格・評価を自動更新 ($(date '+%Y-%m-%d'))"
  echo "コミットしました"
fi
git push origin main 2>&1 | tail -2
echo "=== 終了 ==="
