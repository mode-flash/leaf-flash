"""取得元の一覧（観葉植物トレンドサイト用）.

LOVEGREENとGardenstoryは検索フィード（WordPressの`?s=語&feed=rss2`）を
検索語ごとに取得する（mode="search"）。Gardening Know HowとGardenistaは
観葉植物専門のフィードが無いため、全体フィードを取得してタイトルと概要に
採用キーワードが含まれる記事だけに絞る（mode="filter"）。

検索フィードはWordPressの機能であり、媒体が公式に提供しているものではない。
取得できなくなった場合は取得件数が0件になる（scripts/fetch_feeds.pyが警告ログを出す）。

取得元を追加または変更するときは、URLの実在を必ず確認してから編集する。
"""

from __future__ import annotations

from urllib.parse import quote

# 検索語（LOVEGREENとGardenstory共通）。
# 残り3語（塊根植物とビカクシダとエアプランツ）はTask 8の実データ検証で確認済み
# （design doc 9節）。LOVEGREEN・Gardenstoryとも各語で8〜10件の記事が返り、
# 0件の取得元は無かった（2026-10-08確認）。
SEARCH_TERMS = ["観葉植物", "多肉植物", "塊根植物", "ビカクシダ", "エアプランツ"]

SEARCH_MEDIA = [
    {"name": "LOVEGREEN", "base_url": "https://lovegreen.net/"},
    {"name": "Gardenstory", "base_url": "https://gardenstory.jp/"},
]

FILTER_SOURCES: list[dict] = [
    {"name": "Gardening Know How", "url": "https://www.gardeningknowhow.com/feed", "mode": "filter"},
    {"name": "Gardenista", "url": "https://www.gardenista.com/feed/", "mode": "filter"},
]


def _build_search_sources() -> list[dict]:
    sources = []
    for media in SEARCH_MEDIA:
        for term in SEARCH_TERMS:
            sources.append({
                "name": media["name"],
                "url": f"{media['base_url']}?s={quote(term)}&feed=rss2",
                "mode": "search",
            })
    return sources


FEED_SOURCES: list[dict] = _build_search_sources() + FILTER_SOURCES
