"""RSSフィードを取得して data/items.json を更新するスクリプト."""

from __future__ import annotations

import calendar
import json
import logging
import re
import socket
import urllib.request
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

import feedparser

from theme.sources import FEED_SOURCES
from theme.keywords import EXCLUDE_KEYWORDS, INCLUDE_KEYWORDS
from theme.site import USER_AGENT as _USER_AGENT

logger = logging.getLogger(__name__)

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "items.json"


def parse_feed(source: str, source_name: str) -> list[dict]:
    """RSS/AtomのURLまたはXML文字列をパースしてアイテムのリストを返す."""
    parsed = feedparser.parse(source)
    if parsed.bozo and not parsed.entries:
        raise ValueError(f"feed parse error: {parsed.bozo_exception}")

    items = []
    for entry in parsed.entries:
        url = entry.get("link", "").strip()
        image_url = _extract_image(entry)
        items.append({
            "title": entry.get("title", "").strip(),
            "url": url if _is_safe_url(url) else "",
            "source": source_name,
            "published": _to_iso(entry.get("published_parsed")),
            "summary": entry.get("summary", "").strip(),
            "image_url": image_url if _is_safe_url(image_url) else None,
        })
    return items


def _is_safe_url(url: str | None) -> bool:
    """http/https のURLのみを安全とみなす（javascript: 等の危険なスキームを拒否する）."""
    return bool(url) and url.startswith(("http://", "https://"))


def _to_iso(struct_time) -> str:
    if struct_time is None:
        return ""
    dt = datetime.fromtimestamp(calendar.timegm(struct_time), tz=timezone.utc)
    return dt.isoformat()


# description(summary)内の最初の<img src="...">からURLを取り出す正規表現。
# 属性値はダブルクオート・シングルクオートどちらの場合にも対応する。
_IMG_SRC_RE = re.compile(r'<img[^>]*\ssrc=["\']([^"\']+)["\']', re.IGNORECASE)


def _extract_image_from_html(html_text: str | None) -> str | None:
    """HTML断片（RSSのdescription/summary）内の最初の<img src="...">からURLを抽出する.

    一部の媒体は、画像はmedia:thumbnail/media:contentのような
    RSS拡張要素ではなく、description内に埋め込まれた<img>タグとしてのみ提供される
    （実際のRSSを取得して確認済み）。抽出したURLはXMLの二重エンティティエスケープ
    （例: クエリ文字列中の`&amp;`）を`unescape()`で解いたうえで、
    `_is_safe_url()`でスキームを検証する。安全でなければNoneを返す。
    """
    match = _IMG_SRC_RE.search(html_text or "")
    if not match:
        return None
    url = unescape(match.group(1))
    return url if _is_safe_url(url) else None


def _extract_image(entry) -> str | None:
    if entry.get("media_thumbnail"):
        url = entry["media_thumbnail"][0].get("url")
        return url if _is_safe_url(url) else None
    if entry.get("media_content"):
        url = entry["media_content"][0].get("url")
        return url if _is_safe_url(url) else None
    # フォールバック1: media拡張要素が無い場合、description内のimgタグから抽出する
    # （一部の媒体はここで見つかる）
    image = _extract_image_from_html(entry.get("summary", ""))
    if image:
        return image
    # フォールバック2: descriptionに画像が無い場合、content:encoded
    # （entry.content[0].value、feedparserがlistで公開する）内のimgタグから抽出する。
    # 別の媒体の実データはdescriptionに画像を一切含まず、content:encodedにのみ
    # <img>タグとして埋め込まれている（実際のフィードで確認済み）。
    content_list = entry.get("content") or [{}]
    return _extract_image_from_html(content_list[0].get("value", ""))


# 記事ページ本体のog:image metaタグを抽出する正規表現。
# property="og:image"の前後どちらにcontent属性が来ても対応する
# （サイトによって属性の並び順が異なるため）。
_OG_IMAGE_RE = re.compile(
    r'<meta[^>]+property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']'
    r'|<meta[^>]+content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']',
    re.IGNORECASE,
)


def fetch_og_image(url: str, timeout: int = 10) -> str | None:
    """記事ページ本体からog:image（OGP画像）を取得する.

    RSS自体に画像データを一切含まないメディアもあるため、
    RSS由来の抽出（_extract_image）で見つからなかった場合のフォールバックとして使う。
    ネットワークエラー・タイムアウト・
    og:imageタグの不在は、1記事の取得失敗でビルド全体を止めないよう
    すべて静かにNoneを返す（呼び出し側は既存の画像なし表示にフォールバックする）。
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as res:
            html_text = res.read(200_000).decode("utf-8", errors="ignore")
    except Exception as exc:  # noqa: BLE001 - 1記事の取得失敗で全体を止めない
        logger.warning("failed to fetch og:image from %s: %s", url, exc)
        return None

    match = _OG_IMAGE_RE.search(html_text)
    if not match:
        return None
    image_url = unescape(match.group(1) or match.group(2))
    return image_url if _is_safe_url(image_url) else None


def load_existing_items(path: Path) -> list[dict]:
    """Loads existing items from a JSON file. Returns empty list if file doesn't exist."""
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def merge_items(existing: list[dict], new_items: list[dict]) -> list[dict]:
    """Merges existing and new items, removing duplicates by URL and sorting by published date (descending).

    data/items.jsonは手編集される可能性があるため、urlやpublishedを欠いた
    不正な形式のアイテムがあってもKeyErrorで落ちないよう.get()で防御する。
    urlが無い（または空の）アイテムはどの既存URLとも一致しないものとして扱い、
    重複判定によってサイレントに除外されることはない（毎回そのまま残る）。
    publishedが無いアイテムは空文字列扱いとなり、降順ソートで末尾に来る。
    """
    seen_urls = {item.get("url") for item in existing if item.get("url")}
    merged = list(existing)
    for item in new_items:
        url = item.get("url")
        if not url or url not in seen_urls:
            merged.append(item)
            if url:
                seen_urls.add(url)
    merged.sort(key=lambda x: x.get("published", ""), reverse=True)
    return merged


def save_items(items: list[dict], path: Path) -> None:
    """Saves items to a JSON file, creating parent directories if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def _is_included(item: dict) -> bool:
    """filterモードの取得元で、採用キーワードに当たるか判定する.

    大文字小文字を区別しない（英語の見出しは先頭大文字や全角大文字など表記が揺れるため）。
    """
    text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
    return any(keyword.lower() in text for keyword in INCLUDE_KEYWORDS)


def _is_excluded(item: dict) -> bool:
    """簡易で不完全な非観葉植物記事フィルタ.

    タイトルと概要のいずれかにEXCLUDE_KEYWORDSのキーワードが含まれる場合、
    対象外とみなして除外する。頑健な分類器ではなく、明らかなケースのみを
    弾くための最低限のガードである。
    """
    text = f"{item.get('title', '')} {item.get('summary', '')}"
    return any(keyword in text for keyword in EXCLUDE_KEYWORDS)


def fetch_source(source: dict) -> list[dict]:
    try:
        items = parse_feed(source["url"], source["name"])
    except Exception as exc:  # noqa: BLE001 - 1メディアの失敗で全体を止めない
        logger.warning("failed to fetch %s: %s", source["name"], exc)
        return []

    if source.get("mode") == "filter":
        items = [item for item in items if _is_included(item)]

    kept = []
    for item in items:
        if _is_excluded(item):
            logger.info("excluded item (%s): %s", source["name"], item.get("title"))
        else:
            kept.append(item)

    if not kept:
        logger.warning(
            "0 items kept from %s (mode=%s, fetched=%d)",
            source["name"], source.get("mode"), len(items),
        )
    return kept

def _backfill_og_images(new_items: list[dict], existing_urls: set[str]) -> None:
    """新規アイテムのうち画像が無いものに、記事ページ本体からog:imageを補う（in-place更新）.

    既存アイテム（existing_urls）は対象外にする。RSSは毎回直近N件を返すため、
    絞らないと同じURLに実行のたびアクセスしてしまい、無駄なリクエストが
    積み重なるため。
    """
    for item in new_items:
        if not item.get("image_url") and item.get("url") and item["url"] not in existing_urls:
            item["image_url"] = fetch_og_image(item["url"])


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    socket.setdefaulttimeout(30)
    existing = load_existing_items(DATA_PATH)
    existing_urls = {item.get("url") for item in existing if item.get("url")}
    new_items: list[dict] = []
    for source in FEED_SOURCES:
        new_items.extend(fetch_source(source))
    _backfill_og_images(new_items, existing_urls)
    merged = merge_items(existing, new_items)
    save_items(merged, DATA_PATH)
    logger.info("saved %d items (was %d)", len(merged), len(existing))


if __name__ == "__main__":
    main()
