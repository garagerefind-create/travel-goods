#!/bin/bash
# 価格を更新してサイトを作り直し、点検と変更一覧の表示まで行う（定期実行用）。
#
# 2026-10 変更（安全性改善）：
#   - 価格の再取得とサイトの生成は scripts/build_site.py --refresh で行う（同じロックの中で、一時フォルダで全ページ生成→点検→合格時だけ docs/ と入れ替え）。
#     下書き・未来日・一覧から外した記事のページは、公開フォルダ docs/ から外れる。
#   - 自動コミット・自動プッシュはしない。公開は人が差分を確認してから手動で行う。
#   - --commit を付けた場合だけ、docs/ research/ の追跡済みファイルの変更をコミットする。
#     ・すでにステージ済み（git add 済み）の変更があるときは、無関係な変更の混入を防ぐため中止する。
#     ・docs/ research/ に新しいファイル（未追跡）があるときも中止する。
#     ・コミットの対象は docs/ research/ に限定する。
#   - git push はこのスクリプトでは一切行わない。
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="/usr/local/bin:/usr/bin:/bin"
COMMIT=0
if [ "${1:-}" = "--commit" ]; then COMMIT=1; fi
echo "=== $(date '+%Y-%m-%d %H:%M:%S') 開始 ==="

if [ "$COMMIT" = "1" ] && ! git diff --cached --quiet; then
  echo "すでにステージ済み（git add 済み）の変更があるため中止しました。先に内容を確認してください。"
  exit 1
fi

# 価格の再取得とサイトの作り直しを、同じロックの中で続けて行う
python3 scripts/build_site.py --refresh

echo "--- docs/ research/ の変更一覧（未コミット）---"
git status --short --untracked-files=all -- docs research

if [ "$COMMIT" = "1" ]; then
  if [ -n "$(git status --porcelain --untracked-files=all -- docs research | grep '^??' || true)" ]; then
    echo "docs/ research/ に未追跡の新しいファイルがあるため、コミットを中止しました。内容を確認してください。"
    exit 1
  fi
  if git diff --quiet -- docs research; then
    echo "変更なし（コミットしません）"
  else
    git add -u -- docs research
    git commit -q -m "価格・評価を自動更新 ($(date '+%Y-%m-%d'))" -- docs research
    echo "コミットしました（docs/ research/ のみ。push はしていません）"
  fi
fi
echo "公開（git push）は自動では行いません。差分を確認してから手動で実行してください。"
echo "=== 終了 ==="
