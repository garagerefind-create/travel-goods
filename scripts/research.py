#!/usr/bin/env python3
"""カテゴリごとに楽天商品検索APIで候補を集め、research/candidates.md に書き出す。

レビュー件数の多い順に取得し、評価とレビュー件数でふるいにかける。
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import DEFAULT_ORIGIN, ENDPOINT, ROOT, load_dotenv  # noqa: E402

CATEGORIES = {
    "バックパック": ["トラベルバックパック", "トラベルバックパック 40L 拡張"],
    "スーツケース": ["スーツケース 機内持ち込み"],
    "圧縮袋・トラベルポーチ": ["旅行 圧縮袋", "トラベルポーチ 圧縮 衣類 仕分け"],
    "モバイルバッテリー": ["モバイルバッテリー 軽量 旅行"],
    "変換プラグ": ["海外旅行 変換プラグ"],
    "ネックピロー": ["ネックピロー トラベル"],
    "アイマスク": ["アイマスク 遮光 立体 睡眠 旅行", "トラベル アイマスク 耳栓 セット"],
}
MIN_REVIEWS = 30
MIN_AVERAGE = 4.0
PER_CATEGORY = 8
NG_WORDS = "中古 訳あり"

# カテゴリごとの「必ず含む語」「含んではいけない語」
MUST = {"アイマスク": ["アイマスク"], "バックパック": ["バックパック", "リュック"]}
MUST_NOT = {"アイマスク": ["ネックピロー", "首枕"], "バックパック": ["ビジネス", "登山", "スノーボード", "スキー"]}


def search(app_id, access_key, keyword):
    params = {
        "applicationId": app_id,
        "accessKey": access_key,
        "keyword": keyword,
        "hits": 30,
        "sort": "-reviewCount",
        "imageFlag": 1,
        "availability": 1,
        "NGKeyword": NG_WORDS,
        "formatVersion": 2,
    }
    if os.environ.get("RAKUTEN_AFFILIATE_ID"):
        params["affiliateId"] = os.environ["RAKUTEN_AFFILIATE_ID"]
    url = f"{ENDPOINT}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Origin": os.environ.get("RAKUTEN_ORIGIN", DEFAULT_ORIGIN)})
    for _ in range(4):
        try:
            with urllib.request.urlopen(req, timeout=20) as res:
                d = json.load(res)
            return d.get("Items") or d.get("items") or []
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2)
                continue
            sys.exit(f"APIエラー {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")
    sys.exit("レート制限が解消しませんでした")


def flat(item):
    return item.get("Item", item)


def main():
    load_dotenv(ROOT / ".env")
    app_id, key = os.environ.get("RAKUTEN_APP_ID"), os.environ.get("RAKUTEN_ACCESS_KEY")
    if not app_id or not key:
        sys.exit("RAKUTEN_APP_ID / RAKUTEN_ACCESS_KEY が未設定です")
    out = ["# 商品候補（レビュー件数順）", "",
           f"条件: 評価{MIN_AVERAGE}以上 / レビュー{MIN_REVIEWS}件以上 / 在庫あり / 中古・訳あり除外", ""]
    raw = {}
    for cat, kws in CATEGORIES.items():
        seen, picked = set(), []
        for kw in kws:
            for it in map(flat, search(app_id, key, kw)):
                code = it.get("itemCode")
                if code in seen:
                    continue
                seen.add(code)
                name = it.get("itemName", "")
                if any(w not in name for w in [] ) or (cat in MUST and not any(w in name for w in MUST[cat])):
                    continue
                if any(w in name for w in MUST_NOT.get(cat, [])):
                    continue
                if float(it.get("reviewAverage", 0)) >= MIN_AVERAGE and int(it.get("reviewCount", 0)) >= MIN_REVIEWS:
                    picked.append(it)
            time.sleep(1.5)
        picked = picked[:PER_CATEGORY]
        raw[cat] = picked
        out += [f"## {cat}（{len(picked)}件）", "",
                "| # | 商品名 | 価格 | 評価 | 件数 | ショップ |", "|---|---|---|---|---|---|"]
        for i, it in enumerate(picked, 1):
            name = it["itemName"].replace("|", "/")[:60]
            out.append(f"| {i} | {name} | ¥{it['itemPrice']:,} | {it['reviewAverage']} | {it['reviewCount']} | {it['shopName']} |")
        out.append("")
    d = ROOT / "research"
    d.mkdir(exist_ok=True)
    (d / "candidates.md").write_text("\n".join(out), encoding="utf-8")
    (d / "candidates.json").write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
