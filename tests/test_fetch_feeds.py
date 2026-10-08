import json
from unittest.mock import MagicMock, patch

from scripts.fetch_feeds import (
    _backfill_og_images,
    _is_excluded,
    fetch_og_image,
    fetch_source,
    parse_feed,
    load_existing_items,
    merge_items,
    save_items,
)

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Sample Feed</title>
<item>
<title>サンプル記事1</title>
<link>https://example.com/item1</link>
<description>サンプルの説明文です</description>
<pubDate>Thu, 20 Aug 2026 03:00:00 GMT</pubDate>
</item>
</channel>
</rss>"""


def test_parse_feed_extracts_fields():
    items = parse_feed(SAMPLE_RSS, "SampleMedia")
    assert len(items) == 1
    item = items[0]
    assert item["title"] == "サンプル記事1"
    assert item["url"] == "https://example.com/item1"
    assert item["source"] == "SampleMedia"
    assert item["summary"] == "サンプルの説明文です"
    assert item["published"] == "2026-08-20T03:00:00+00:00"
    assert item["image_url"] is None


def test_parse_feed_empty_feed_returns_empty_list():
    empty_rss = """<?xml version="1.0"?><rss version="2.0"><channel><title>Empty</title></channel></rss>"""
    assert parse_feed(empty_rss, "SampleMedia") == []


def test_parse_feed_rejects_javascript_url_scheme():
    malicious_rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Malicious Feed</title>
<item>
<title>危険なリンク</title>
<link>javascript:alert(1)</link>
<description>説明文</description>
<pubDate>Thu, 20 Aug 2026 03:00:00 GMT</pubDate>
</item>
</channel>
</rss>"""
    items = parse_feed(malicious_rss, "SampleMedia")
    assert len(items) == 1
    assert items[0]["url"] == ""


def test_parse_feed_rejects_javascript_image_url_scheme():
    malicious_rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
<channel>
<title>Malicious Feed</title>
<item>
<title>危険な画像リンク</title>
<link>https://example.com/a</link>
<description>説明文</description>
<media:thumbnail url="javascript:alert(1)" />
<pubDate>Thu, 20 Aug 2026 03:00:00 GMT</pubDate>
</item>
</channel>
</rss>"""
    items = parse_feed(malicious_rss, "SampleMedia")
    assert len(items) == 1
    assert items[0]["url"] == "https://example.com/a"
    assert items[0]["image_url"] is None


def test_parse_feed_extracts_image_from_description_img_tag():
    # 一部の媒体の実データはmedia:thumbnail/media:content拡張要素を使わず、
    # descriptionの先頭に<img src="...">を埋め込み、その後ろに本文が続く形式で画像を提供する。
    rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Sample Feed</title>
<item>
<title>サンプル記事</title>
<link>https://example.com/item-with-image</link>
<description>&lt;img src="https://example.com/photo.jpg" /&gt; お笑いトリオの記事本文がここに続きます。</description>
<pubDate>Thu, 20 Aug 2026 03:00:00 GMT</pubDate>
</item>
</channel>
</rss>"""
    items = parse_feed(rss, "SampleMedia")
    assert len(items) == 1
    assert items[0]["image_url"] == "https://example.com/photo.jpg"


def test_parse_feed_unescapes_query_string_ampersands_in_description_image():
    # 別の媒体の実データはクエリ文字列付きの画像URLを持ち、XML上は`&amp;amp;`と
    # 二重エスケープされているため、feedparserが1段階デコードした後のsummaryには
    # `&amp;`が残る。html.unescape()でさらに1段階デコードして実URLに戻す必要がある。
    rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Sample Feed</title>
<item>
<title>サンプル記事2</title>
<link>https://example.com/item-with-query-image</link>
<description>&lt;img src="https://example.com/photo.jpg?w=800&amp;amp;q=90" /&gt; 本文です。</description>
<pubDate>Thu, 20 Aug 2026 03:00:00 GMT</pubDate>
</item>
</channel>
</rss>"""
    items = parse_feed(rss, "SampleMedia")
    assert items[0]["image_url"] == "https://example.com/photo.jpg?w=800&q=90"


def test_parse_feed_rejects_unsafe_scheme_in_description_image():
    rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Sample Feed</title>
<item>
<title>危険な画像リンク（description内）</title>
<link>https://example.com/item-unsafe-image</link>
<description>&lt;img src="javascript:alert(1)" /&gt; 本文です。</description>
<pubDate>Thu, 20 Aug 2026 03:00:00 GMT</pubDate>
</item>
</channel>
</rss>"""
    items = parse_feed(rss, "SampleMedia")
    assert items[0]["image_url"] is None


def test_parse_feed_still_prefers_media_thumbnail_when_present():
    # media:thumbnail/media:content経由の既存の抽出パスが、description内img
    # フォールバックの追加によって壊れていないことを確認する回帰テスト。
    rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
<channel>
<title>Sample Feed</title>
<item>
<title>media:thumbnail付き記事</title>
<link>https://example.com/item-media-thumbnail</link>
<description>&lt;img src="https://example.com/should-not-be-used.jpg" /&gt; 本文です。</description>
<media:thumbnail url="https://example.com/thumbnail.jpg" />
<pubDate>Thu, 20 Aug 2026 03:00:00 GMT</pubDate>
</item>
</channel>
</rss>"""
    items = parse_feed(rss, "SampleMedia")
    assert items[0]["image_url"] == "https://example.com/thumbnail.jpg"


def test_parse_feed_extracts_image_from_content_encoded_when_summary_has_none():
    # 別の媒体の実データは、前述の媒体と異なり画像はdescription(summary)には
    # 一切含まれず、content:encoded（entry.content[0].value）にのみ<img>タグとして
    # 埋め込まれている（実際のフィードをfeedparserで確認済み）。
    rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel>
<title>Sample Feed</title>
<item>
<title>真夏のブラック。ブラブラブラから軽やかなコットンウェアの新作コレクションが。</title>
<link>https://example.com/content-encoded-item</link>
<description>&lt;p&gt;こう暑いと服のことを考えるのもなんだか億劫になりますよね。&lt;/p&gt;
&lt;p&gt;The post &lt;a href="https://example.com/content-encoded-item"&gt;記事タイトル&lt;/a&gt; first appeared on &lt;a href="https://example.com"&gt;SampleMediaB（サンプルメディア）&lt;/a&gt;.&lt;/p&gt;</description>
<content:encoded><![CDATA[<div class="tate-img">
<img alt="" class="alignnone size-full wp-image-1162896 image" height="1000" src="https://example.com/wp-content/uploads/2026/08/BBB_CRSPBLK_01-1.jpg" width="800" />
</div>]]></content:encoded>
<pubDate>Thu, 20 Aug 2026 03:00:00 GMT</pubDate>
</item>
</channel>
</rss>"""
    items = parse_feed(rss, "SampleMedia")
    assert len(items) == 1
    assert items[0]["image_url"] == "https://example.com/wp-content/uploads/2026/08/BBB_CRSPBLK_01-1.jpg"


def test_parse_feed_prefers_summary_image_over_content_encoded_when_both_present():
    # summary内にimgがあればcontent:encodedより優先する（SampleMediaの既存挙動を
    # 変えないための優先順位）。
    rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel>
<title>Sample Feed</title>
<item>
<title>両方に画像がある記事</title>
<link>https://example.com/item-both-images</link>
<description>&lt;img src="https://example.com/summary-photo.jpg" /&gt; 本文の抜粋です。</description>
<content:encoded><![CDATA[<img src="https://example.com/content-photo.jpg" />]]></content:encoded>
<pubDate>Thu, 20 Aug 2026 03:00:00 GMT</pubDate>
</item>
</channel>
</rss>"""
    items = parse_feed(rss, "SampleMedia")
    assert items[0]["image_url"] == "https://example.com/summary-photo.jpg"


def test_parse_feed_no_image_in_summary_or_content_encoded_returns_none():
    # summary・content:encodedのいずれにも画像が無い場合はNoneを返し、クラッシュしない
    # （content:encoded自体が存在するフィードでの回帰確認）。
    rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel>
<title>Sample Feed</title>
<item>
<title>画像の無い記事（content:encodedあり）</title>
<link>https://example.com/item-no-image-with-content</link>
<description>画像を含まない普通の説明文です。</description>
<content:encoded><![CDATA[<p>本文にも画像はありません。</p>]]></content:encoded>
<pubDate>Thu, 20 Aug 2026 03:00:00 GMT</pubDate>
</item>
</channel>
</rss>"""
    items = parse_feed(rss, "SampleMedia")
    assert items[0]["image_url"] is None


def test_parse_feed_no_image_anywhere_returns_none_without_crashing():
    rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Sample Feed</title>
<item>
<title>画像の無い記事</title>
<link>https://example.com/item-no-image</link>
<description>画像を含まない普通の説明文です。</description>
<pubDate>Thu, 20 Aug 2026 03:00:00 GMT</pubDate>
</item>
</channel>
</rss>"""
    items = parse_feed(rss, "SampleMedia")
    assert items[0]["image_url"] is None


def test_merge_items_removes_duplicates_by_url():
    existing = [{"url": "https://example.com/a", "published": "2026-08-19T00:00:00+00:00"}]
    new_items = [
        {"url": "https://example.com/a", "published": "2026-08-19T00:00:00+00:00"},
        {"url": "https://example.com/b", "published": "2026-08-20T00:00:00+00:00"},
    ]
    merged = merge_items(existing, new_items)
    assert [item["url"] for item in merged] == [
        "https://example.com/b",
        "https://example.com/a",
    ]


def test_merge_items_ignores_missing_url_without_raising():
    existing = [{"url": "https://example.com/a", "published": "2026-08-19T00:00:00+00:00"}]
    new_items = [
        {"title": "urlが無いアイテム", "published": "2026-08-20T00:00:00+00:00"},
        {"url": "https://example.com/b", "published": "2026-08-18T00:00:00+00:00"},
    ]
    merged = merge_items(existing, new_items)
    # urlの無いアイテムも消えずに残る（重複判定の対象外として扱われる）
    assert len(merged) == 3
    urls = [item.get("url") for item in merged]
    assert "https://example.com/a" in urls
    assert "https://example.com/b" in urls


def test_merge_items_sorts_missing_published_last():
    existing = []
    new_items = [
        {"url": "https://example.com/no-date"},  # publishedキーが無い
        {"url": "https://example.com/a", "published": "2026-08-20T00:00:00+00:00"},
    ]
    merged = merge_items(existing, new_items)
    assert [item["url"] for item in merged] == [
        "https://example.com/a",
        "https://example.com/no-date",
    ]


def test_merge_items_existing_missing_url_does_not_raise():
    existing = [{"title": "既存だがurlが無い", "published": "2026-08-19T00:00:00+00:00"}]
    new_items = [{"url": "https://example.com/b", "published": "2026-08-20T00:00:00+00:00"}]
    merged = merge_items(existing, new_items)
    assert len(merged) == 2


def _mock_response(html_bytes: bytes) -> MagicMock:
    mock_response = MagicMock()
    mock_response.read.return_value = html_bytes
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = False
    return mock_response


def test_fetch_og_image_extracts_og_image_content():
    html = b'<html><head><meta property="og:image" content="https://example.com/photo.jpg"></head></html>'
    with patch("scripts.fetch_feeds.urllib.request.urlopen", return_value=_mock_response(html)):
        assert fetch_og_image("https://example.com/article") == "https://example.com/photo.jpg"


def test_fetch_og_image_supports_content_before_property_attribute_order():
    # サイトによってはmetaタグの属性順がcontent→propertyの場合もある
    html = b'<meta content="https://example.com/photo2.jpg" property="og:image">'
    with patch("scripts.fetch_feeds.urllib.request.urlopen", return_value=_mock_response(html)):
        assert fetch_og_image("https://example.com/article") == "https://example.com/photo2.jpg"


def test_fetch_og_image_returns_none_when_tag_missing():
    html = b"<html><head><title>no og image here</title></head></html>"
    with patch("scripts.fetch_feeds.urllib.request.urlopen", return_value=_mock_response(html)):
        assert fetch_og_image("https://example.com/article") is None


def test_fetch_og_image_returns_none_on_network_error():
    with patch("scripts.fetch_feeds.urllib.request.urlopen", side_effect=OSError("timeout")):
        assert fetch_og_image("https://example.com/article") is None


def test_fetch_og_image_rejects_unsafe_scheme():
    html = b'<meta property="og:image" content="javascript:alert(1)">'
    with patch("scripts.fetch_feeds.urllib.request.urlopen", return_value=_mock_response(html)):
        assert fetch_og_image("https://example.com/article") is None


def test_backfill_og_images_skips_existing_urls():
    new_items = [
        {"url": "https://example.com/existing", "image_url": None},
        {"url": "https://example.com/new", "image_url": None},
    ]
    existing_urls = {"https://example.com/existing"}
    with patch("scripts.fetch_feeds.fetch_og_image", return_value="https://example.com/photo.jpg") as mock_fetch:
        _backfill_og_images(new_items, existing_urls)
    mock_fetch.assert_called_once_with("https://example.com/new")
    assert new_items[0]["image_url"] is None
    assert new_items[1]["image_url"] == "https://example.com/photo.jpg"


def test_backfill_og_images_skips_items_that_already_have_image():
    new_items = [{"url": "https://example.com/new", "image_url": "https://example.com/existing.jpg"}]
    with patch("scripts.fetch_feeds.fetch_og_image") as mock_fetch:
        _backfill_og_images(new_items, set())
    mock_fetch.assert_not_called()


def test_load_existing_items_returns_empty_list_when_missing(tmp_path):
    missing_path = tmp_path / "items.json"
    assert load_existing_items(missing_path) == []


def test_save_and_load_round_trip(tmp_path):
    path = tmp_path / "items.json"
    items = [{"url": "https://example.com/a", "title": "テスト記事", "published": "2026-08-20T00:00:00+00:00"}]
    save_items(items, path)
    loaded = load_existing_items(path)
    assert loaded == items
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    assert raw == items


def test_fetch_source_returns_empty_list_on_parse_error():
    source = {"name": "BrokenMedia", "url": "https://example.com/broken.xml"}
    with patch("scripts.fetch_feeds.parse_feed", side_effect=ValueError("boom")):
        result = fetch_source(source)
    assert result == []


def test_fetch_source_returns_items_on_success():
    source = {"name": "SampleMedia", "url": "https://example.com/feed.xml"}
    fake_items = [{"url": "https://example.com/a", "title": "a", "published": "2026-08-20T00:00:00+00:00"}]
    with patch("scripts.fetch_feeds.parse_feed", return_value=fake_items):
        result = fetch_source(source)
    assert result == fake_items


from scripts.fetch_feeds import _is_included


def test_is_excluded_false_for_normal_houseplant_item():
    item = {
        "title": "モンステラの育て方｜葉焼けを防ぐコツ",
        "summary": "観葉植物として人気のモンステラの育て方を紹介します。",
    }
    assert _is_excluded(item) is False


def test_is_excluded_true_for_weed_control_garden_article():
    # 検索フィード経由で混入する庭づくり記事（design doc 3.4節の実例）
    item = {"title": "防草シート×多年草「クラピア」で雑草対策", "summary": ""}
    assert _is_excluded(item) is True


def test_is_excluded_true_for_prefecture_flower_quiz():
    item = {"title": "「都道府県の花」3択クイズ！ 群馬県の花は次のうちどれ？", "summary": ""}
    assert _is_excluded(item) is True


def test_is_included_true_for_houseplant_keyword_in_title():
    item = {"title": "6 Purple Houseplants That Add Instant Drama To Your Home", "summary": ""}
    assert _is_included(item) is True


def test_is_included_true_for_monstera_keyword_case_insensitive():
    item = {"title": "How to care for your Monstera", "summary": ""}
    assert _is_included(item) is True


def test_is_included_false_for_unrelated_gardening_item():
    item = {"title": "5 Self-Sowing Flowers That Bloom in Fall", "summary": ""}
    assert _is_included(item) is False


def test_fetch_source_search_mode_applies_only_exclude_filter():
    source = {"name": "LOVEGREEN", "url": "https://example.com/feed.xml", "mode": "search"}
    fake_items = [
        {"url": "https://example.com/a", "title": "モンステラの育て方", "summary": "", "published": "2026-09-01T00:00:00+00:00"},
        {"url": "https://example.com/b", "title": "雑草対策の決定版", "summary": "", "published": "2026-09-01T00:00:00+00:00"},
    ]
    with patch("scripts.fetch_feeds.parse_feed", return_value=fake_items):
        result = fetch_source(source)
    assert [item["url"] for item in result] == ["https://example.com/a"]


def test_fetch_source_filter_mode_applies_include_then_exclude_filter():
    source = {"name": "Gardenista", "url": "https://example.com/feed.xml", "mode": "filter"}
    fake_items = [
        {"url": "https://example.com/a", "title": "Monstera Care Guide", "summary": "", "published": "2026-09-01T00:00:00+00:00"},
        {"url": "https://example.com/b", "title": "Best Pizza Ovens for 2026", "summary": "", "published": "2026-09-01T00:00:00+00:00"},
    ]
    with patch("scripts.fetch_feeds.parse_feed", return_value=fake_items):
        result = fetch_source(source)
    assert [item["url"] for item in result] == ["https://example.com/a"]


def test_fetch_source_logs_warning_when_zero_items_kept(caplog):
    source = {"name": "EmptyMedia", "url": "https://example.com/feed.xml", "mode": "search"}
    with patch("scripts.fetch_feeds.parse_feed", return_value=[]):
        with caplog.at_level("WARNING"):
            result = fetch_source(source)
    assert result == []
    assert any("0" in record.message or "0件" in record.message for record in caplog.records)
