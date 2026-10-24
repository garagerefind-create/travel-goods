#!/usr/bin/env python3
"""選定済み商品(research/picks.json)を商品コードで再取得し、価格・評価を更新する。

- 取得できなかった/在庫なしの商品は、前回の情報を残して警告を出す（ページからは外さない）
- 更新後は scripts/build_site.py でページを作り直す（weekly_update.sh は build_site.py --refresh でまとめて実行）
- RAKUTEN_AFFILIATE_ID が無いときは実行しない（アフィリエイトURLの消失防止）
- APIの返却に正しい形式（https://hb.afl.rakuten.co.jp/…）の affiliateUrl が無い場合は、前回の値を引き継ぐ
- items.json / meta.json は一時ファイル経由で書き込む（途中失敗で壊さない）
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import DEFAULT_ORIGIN, ENDPOINT, ROOT, load_dotenv  # noqa: E402
from safety import atomic_write_text, hold_site_lock, is_affiliate_url, require_affiliate_id  # noqa: E402

ITEMS = ROOT / "research" / "items.json"
PICKS = ROOT / "research" / "picks.json"
META = ROOT / "research" / "meta.json"


def fetch(app_id, key, aff, code):
    params = {"applicationId": app_id, "accessKey": key, "itemCode": code, "formatVersion": 2, "hits": 1}
    if aff:
        params["affiliateId"] = aff
    req = urllib.request.Request(f"{ENDPOINT}?{urllib.parse.urlencode(params)}",
                                 headers={"Origin": os.environ.get("RAKUTEN_ORIGIN", DEFAULT_ORIGIN)})
    for _ in range(5):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                d = json.load(r)
            items = d.get("Items") or d.get("items") or []
            return (items[0].get("Item", items[0]) if items else None)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(3)
                continue
            raise
    raise RuntimeError("レート制限が解消しません")


def main():
    _lock = hold_site_lock(ROOT)  # noqa: F841  同時に書き換えないためのロック（プロセス終了まで保持）
    load_dotenv(ROOT / ".env")
    app_id, key, aff = (os.environ.get(k) for k in ("RAKUTEN_APP_ID", "RAKUTEN_ACCESS_KEY", "RAKUTEN_AFFILIATE_ID"))
    if not (app_id and key):
        sys.exit("RAKUTEN_APP_ID / RAKUTEN_ACCESS_KEY が未設定です")
    aff = require_affiliate_id("商品の価格・評価の更新")
    items = json.loads(ITEMS.read_text(encoding="utf-8"))
    codes = [i["itemCode"] for s in json.loads(PICKS.read_text(encoding="utf-8")) for i in s["items"]]
    changed, missing, kept_aff = [], [], []
    aff_before = sum(1 for c in codes if is_affiliate_url((items.get(c) or {}).get("affiliateUrl")))
    for code in codes:
        new = fetch(app_id, key, aff, code)
        time.sleep(1.5)
        if not new or not int(new.get("availability", 1)):
            missing.append(code)
            continue
        old = items.get(code)
        if old is None:
            changed.append(f"新規 {code}")
        elif (old["itemPrice"], old["reviewAverage"], old["reviewCount"]) != (new["itemPrice"], new["reviewAverage"], new["reviewCount"]):
            changed.append(f"{old['itemPrice']}→{new['itemPrice']} ★{old['reviewAverage']}→{new['reviewAverage']} {code}")
        # APIの返却に正しい形式の affiliateUrl が無ければ、前回の正しい affiliateUrl を引き継ぐ
        if old and is_affiliate_url(old.get("affiliateUrl")) and not is_affiliate_url(new.get("affiliateUrl")):
            new = {**new, "affiliateUrl": old["affiliateUrl"]}
            kept_aff.append(code)
        items[code] = new
    if len(missing) > len(codes) // 2:
        sys.exit(f"取得できない商品が多すぎます({len(missing)}/{len(codes)})。更新を中止しました")
    aff_after = sum(1 for c in codes if is_affiliate_url((items.get(c) or {}).get("affiliateUrl")))
    if aff_after < aff_before:
        sys.exit(f"アフィリエイトURLが減るため更新を中止しました({aff_before}→{aff_after})")
    atomic_write_text(ITEMS, json.dumps(items, ensure_ascii=False, indent=1))
    atomic_write_text(META, json.dumps({"updated": date.today().isoformat()}))
    print(f"更新: {len(codes) - len(missing)}点 / 変更あり: {len(changed)}点 / 取得不可: {len(missing)}点")
    for c in changed:
        print("  変更:", c)
    for c in missing:
        print("  ⚠ 取得できず前回の情報を維持:", c)
    for c in kept_aff:
        print("  ⚠ APIの返却に正しいaffiliateUrlが無く、前回のURLを引き継ぎ:", c)


if __name__ == "__main__":
    main()
